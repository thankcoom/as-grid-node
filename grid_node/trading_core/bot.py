import asyncio
import json
import logging
import time
import math
import hmac
import hashlib
import base64
import ssl
import certifi
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import ccxt.async_support as ccxt_async
import ccxt

from .models import GlobalConfig, SymbolConfig, SymbolState, GlobalState
from .strategy import (
    GridStrategy, FundingRateManager, GLFTController, DynamicGridManager,
    UCBBanditOptimizer, DGTBoundaryManager, LeadingIndicatorManager
)

logger = logging.getLogger(__name__)

class CustomExchange(ccxt.bitget):
    """Bitget 交易所擴展類"""
    def fetch(self, url, method='GET', headers=None, body=None):
        if headers is None:
            headers = {}
        return super().fetch(url, method, headers, body)

class MaxGridBot:
    """MAX 版本網格機器人 (Bitget) - 整合學術模型增強功能"""

    def __init__(self, config: GlobalConfig):
        self.config = config
        self.state = GlobalState()

        for symbol, sym_cfg in config.symbols.items():
            if sym_cfg.enabled:
                self.state.symbols[sym_cfg.ccxt_symbol] = SymbolState(symbol=sym_cfg.ccxt_symbol)

        self.exchange: Optional[CustomExchange] = None
        # Bitget 不需要 listenKey，使用 WebSocket 簽名認證
        self.tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self.precisions: Dict[str, dict] = {}
        self.last_sync_time = 0
        self.last_order_times: Dict[str, float] = {}

        # MAX 增強模組
        self.funding_manager: Optional[FundingRateManager] = None
        self.glft_controller = GLFTController()
        self.dynamic_grid_manager = DynamicGridManager()

        # 學習模組 (Bandit + DGT)
        self.bandit_optimizer = UCBBanditOptimizer(config.bandit)
        self.dgt_manager = DGTBoundaryManager(config.dgt)

        # 領先指標系統 (取代滯後 ATR)
        self.leading_indicator = LeadingIndicatorManager(config.leading_indicator)

        logger.info(f"[MAX Bitget] 初始化完成 - Bandit: {config.bandit.enabled}, Leading: {config.leading_indicator.enabled}")

    def _init_exchange(self):
        """初始化 Bitget 交易所連接"""
        self.exchange = CustomExchange({
            "apiKey": self.config.api_key,
            "secret": self.config.api_secret,
            "password": self.config.passphrase,  # Bitget 需要 passphrase
            "options": {
                "defaultType": "swap",  # Bitget 永續合約
                "adjustForTimeDifference": True,
            }
        })
        self.exchange.load_markets(reload=False)

        # 初始化 funding manager
        self.funding_manager = FundingRateManager(self.exchange)

        markets = self.exchange.fetch_markets()
        for sym_config in self.config.symbols.values():
            if not sym_config.enabled:
                continue

            try:
                symbol_info = next(m for m in markets if m["symbol"] == sym_config.ccxt_symbol)
                price_prec = symbol_info["precision"]["price"]
                self.precisions[sym_config.ccxt_symbol] = {
                    "price": int(abs(math.log10(price_prec))) if isinstance(price_prec, float) else price_prec,
                    "amount": int(abs(math.log10(symbol_info["precision"]["amount"]))) if isinstance(symbol_info["precision"]["amount"], float) else symbol_info["precision"]["amount"],
                    "min_amount": symbol_info["limits"]["amount"]["min"]
                }
            except Exception as e:
                logger.error(f"獲取 {sym_config.ccxt_symbol} 精度失敗: {e}")

    def _check_hedge_mode(self):
        """檢查並設置雙向持倉模式 (Bitget)"""
        for sym_config in self.config.symbols.values():
            if sym_config.enabled:
                try:
                    # Bitget: 使用 CCXT 統一接口設置持倉模式
                    self.exchange.set_position_mode(hedged=True, symbol=sym_config.ccxt_symbol)
                    logger.info(f"[Bitget] 已設置 {sym_config.ccxt_symbol} 為雙向持倉模式")
                    break
                except Exception as e:
                    # 可能已經是雙向持倉模式
                    logger.debug(f"設置持倉模式: {e}")
                    pass

    def _generate_ws_signature(self) -> dict:
        """生成 Bitget WebSocket 認證簽名"""
        timestamp = str(int(time.time()))
        message = f"{timestamp}GET/user/verify"
        signature = base64.b64encode(
            hmac.new(
                self.config.api_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        return {
            "apiKey": self.config.api_key,
            "passphrase": self.config.passphrase,
            "timestamp": timestamp,
            "sign": signature
        }

    def sync_all(self):
        self._sync_positions()
        self._sync_orders()
        self._sync_account()
        self._sync_funding_rates()

    def _sync_funding_rates(self):
        """同步所有交易對的 funding rate"""
        if not self.funding_manager:
            return

        for sym_config in self.config.symbols.values():
            if sym_config.enabled:
                rate = self.funding_manager.update_funding_rate(sym_config.ccxt_symbol)
                sym_state = self.state.symbols.get(sym_config.ccxt_symbol)
                if sym_state:
                    sym_state.current_funding_rate = rate

    def _sync_positions(self):
        try:
            positions = self.exchange.fetch_positions(params={'type': 'future'})

            for sym_state in self.state.symbols.values():
                sym_state.long_position = 0
                sym_state.short_position = 0
                sym_state.unrealized_pnl = 0

            for pos in positions:
                symbol = pos['symbol']
                if symbol in self.state.symbols:
                    contracts = pos.get('contracts', 0)
                    side = pos.get('side')
                    pnl = float(pos.get('unrealizedPnl', 0) or 0)

                    if side == 'long':
                        self.state.symbols[symbol].long_position = contracts
                    elif side == 'short':
                        self.state.symbols[symbol].short_position = abs(contracts)

                    self.state.symbols[symbol].unrealized_pnl += pnl

        except Exception as e:
            logger.error(f"同步持倉失敗: {e}")

    def _sync_orders(self):
        for sym_config in self.config.symbols.values():
            if not sym_config.enabled:
                continue
            symbol = sym_config.ccxt_symbol

            try:
                orders = self.exchange.fetch_open_orders(symbol=symbol)
                state = self.state.symbols.get(symbol)
                if not state:
                    continue

                state.buy_long_orders = 0
                state.sell_long_orders = 0
                state.buy_short_orders = 0
                state.sell_short_orders = 0

                for order in orders:
                    qty = abs(float(order.get('amount', 0) or order.get('info', {}).get('size', 0)))
                    side = order.get('side')
                    pos_side = order.get('info', {}).get('holdSide', '').lower()

                    if side == 'buy' and pos_side == 'long':
                        state.buy_long_orders += qty
                    elif side == 'sell' and pos_side == 'long':
                        state.sell_long_orders += qty
                    elif side == 'buy' and pos_side == 'short':
                        state.buy_short_orders += qty
                    elif side == 'sell' and pos_side == 'short':
                        state.sell_short_orders += qty
            except Exception as e:
                logger.error(f"同步 {symbol} 掛單失敗: {e}")

    def _sync_account(self):
        try:
            balance = self.exchange.fetch_balance({'type': 'future'})

            for currency in ['USDC', 'USDT']:
                total = float(balance.get('total', {}).get(currency, 0) or 0)
                free = float(balance.get('free', {}).get(currency, 0) or 0)

                acc = self.state.get_account(currency)
                acc.wallet_balance = total
                acc.available_balance = free
                acc.margin_used = total - free if total > free else 0

                unrealized = 0
                for sym_state in self.state.symbols.values():
                    if currency in sym_state.symbol:
                        unrealized += sym_state.unrealized_pnl
                acc.unrealized_pnl = unrealized

            self.state.update_totals()
            self._check_trailing_stop()
        except Exception as e:
            logger.error(f"同步帳戶失敗: {e}")

    def _check_trailing_stop(self):
        risk = self.config.risk
        if not risk.enabled:
            return

        if self.state.margin_usage < risk.margin_threshold:
            self.state.trailing_active.clear()
            self.state.peak_pnl.clear()
            return

        for sym_config in self.config.symbols.values():
            if not sym_config.enabled:
                continue

            ccxt_symbol = sym_config.ccxt_symbol
            sym_state = self.state.symbols.get(ccxt_symbol)
            if not sym_state:
                continue

            current_pnl = sym_state.unrealized_pnl

            if self.state.trailing_active.get(ccxt_symbol, False):
                peak = self.state.peak_pnl.get(ccxt_symbol, 0)
                if current_pnl > peak:
                    self.state.peak_pnl[ccxt_symbol] = current_pnl
                    logger.info(f"[追蹤止盈] {sym_config.symbol} 新高: {current_pnl:.2f}U")

                peak = self.state.peak_pnl.get(ccxt_symbol, 0)
                drawdown = peak - current_pnl
                trigger = max(risk.trailing_min_drawdown, peak * risk.trailing_drawdown_pct)

                if drawdown >= trigger and peak > 0:
                    logger.info(f"[追蹤止盈] {sym_config.symbol} 觸發! 最高:{peak:.2f}, 當前:{current_pnl:.2f}, 回撤:{drawdown:.2f}")
                    self._close_symbol_positions(ccxt_symbol, sym_config)
                    self.state.trailing_active[ccxt_symbol] = False
                    self.state.peak_pnl[ccxt_symbol] = 0

            else:
                if current_pnl >= risk.trailing_start_profit:
                    self.state.trailing_active[ccxt_symbol] = True
                    self.state.peak_pnl[ccxt_symbol] = current_pnl
                    logger.info(f"[追蹤止盈] {sym_config.symbol} 開始追蹤! 浮盈: {current_pnl:.2f}U")

    def _close_symbol_positions(self, ccxt_symbol: str, sym_config: SymbolConfig):
        try:
            sym_state = self.state.symbols.get(ccxt_symbol)
            if not sym_state:
                return

            self.cancel_orders_for_side(ccxt_symbol, 'long')
            self.cancel_orders_for_side(ccxt_symbol, 'short')

            if sym_state.long_position > 0:
                self.place_order(
                    ccxt_symbol, 'sell', 0, sym_state.long_position,
                    reduce_only=True, position_side='long', order_type='market'
                )
                logger.info(f"[追蹤止盈] {sym_config.symbol} 市價平多 {sym_state.long_position}")

            if sym_state.short_position > 0:
                self.place_order(
                    ccxt_symbol, 'buy', 0, sym_state.short_position,
                    reduce_only=True, position_side='short', order_type='market'
                )
                logger.info(f"[追蹤止盈] {sym_config.symbol} 市價平空 {sym_state.short_position}")

        except Exception as e:
            logger.error(f"[追蹤止盈] {sym_config.symbol} 平倉失敗: {e}")

    def place_order(self, symbol: str, side: str, price: float, quantity: float,
                    reduce_only: bool = False, position_side: str = None,
                    order_type: str = 'limit'):
        try:
            prec = self.precisions.get(symbol, {"price": 4, "amount": 0, "min_amount": 1})
            price = round(price, prec["price"])
            quantity = round(quantity, prec["amount"])
            quantity = max(quantity, prec["min_amount"])

            params = {'reduceOnly': reduce_only}
            if position_side:
                params['holdSide'] = position_side.lower()
                params['hedged'] = True

            display_symbol = symbol.replace('/USDT:USDT', '').replace('/', '')

            if order_type == 'market':
                result = self.exchange.create_order(symbol, 'market', side, quantity, None, params)
                side_cn = "買入" if side == 'buy' else "賣出"
                pos_cn = "做多" if position_side == 'long' else "做空" if position_side == 'short' else ""
                action = "平倉" if reduce_only else "開倉"
                logger.info(f"📤 [掛單成功] {display_symbol} {pos_cn}{action}: 市價{side_cn} {quantity}張")
                return result
            else:
                result = self.exchange.create_order(symbol, 'limit', side, quantity, price, params)
                side_cn = "買入" if side == 'buy' else "賣出"
                pos_cn = "做多" if position_side == 'long' else "做空" if position_side == 'short' else ""
                action = "止盈" if reduce_only else "補倉"
                logger.info(f"📤 [掛單成功] {display_symbol} {pos_cn}{action}: {side_cn}@{price:.4f} x {quantity}張")
                return result
        except Exception as e:
            logger.error(f"❌ [掛單失敗] {symbol}: {e}")
            return None

    def cancel_orders_for_side(self, symbol: str, position_side: str):
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            cancelled_count = 0
            display_symbol = symbol.replace('/USDT:USDT', '').replace('/', '')

            logger.debug(f"[撤單檢查] {display_symbol} {position_side}: 找到 {len(orders)} 個掛單")

            for order in orders:
                order_id = order.get('id')
                order_side = order.get('side')
                
                order_info = order.get('info', {})
                order_pos_side = (
                    order_info.get('holdSide', '') or
                    order_info.get('posSide', '') or
                    order_info.get('positionSide', '') or
                    order.get('positionSide', '')
                ).lower()

                if not order_pos_side:
                    trade_side = order_info.get('tradeSide', '')
                    if trade_side == 'open':
                        order_pos_side = 'long' if order_side == 'buy' else 'short'
                    elif trade_side == 'close':
                        order_pos_side = 'long' if order_side == 'sell' else 'short'

                should_cancel = (order_pos_side == position_side)

                if should_cancel:
                    try:
                        self.exchange.cancel_order(order_id, symbol)
                        cancelled_count += 1
                        logger.debug(f"  ✓ 已取消訂單 {order_id}")
                    except Exception as cancel_err:
                        logger.warning(f"  ✗ 取消訂單 {order_id} 失敗: {cancel_err}")

            pos_cn = "做多" if position_side == 'long' else "做空"
            if cancelled_count > 0:
                logger.info(f"🗑️ [撤單成功] {display_symbol} {pos_cn}: 取消 {cancelled_count} 筆掛單")

        except Exception as e:
            logger.error(f"❌ [撤單失敗] {symbol}: {e}")

    def _get_dynamic_spacing(self, sym_config: SymbolConfig, sym_state: SymbolState) -> Tuple[float, float]:
        max_cfg = self.config.max_enhancement
        ccxt_symbol = sym_config.ccxt_symbol

        base_take_profit = sym_config.take_profit_spacing
        base_grid_spacing = sym_config.grid_spacing

        leading_reason = ""
        leading_signals = []
        leading_values = {}

        if self.config.leading_indicator.enabled:
            leading_signals, leading_values = self.leading_indicator.get_signals(ccxt_symbol)
            sym_state.leading_ofi = leading_values.get('ofi', 0)
            sym_state.leading_volume_ratio = leading_values.get('volume_ratio', 1.0)
            sym_state.leading_spread_ratio = leading_values.get('spread_ratio', 1.0)
            sym_state.leading_signals = leading_signals

            should_pause, pause_reason = self.leading_indicator.should_pause_trading(ccxt_symbol)
            if should_pause:
                logger.warning(f"[LeadingIndicator] {sym_config.symbol} 暫停交易: {pause_reason}")
                base_take_profit *= 2.0
                base_grid_spacing *= 2.0
                leading_reason = f"暫停:{pause_reason}"
            elif leading_signals:
                adjusted_spacing, leading_reason = self.leading_indicator.get_spacing_adjustment(
                    ccxt_symbol, base_grid_spacing
                )
                if adjusted_spacing != base_grid_spacing:
                    ratio = adjusted_spacing / base_grid_spacing
                    base_grid_spacing = adjusted_spacing
                    base_take_profit *= ratio

        if not leading_reason or leading_reason == "正常":
            take_profit, grid_spacing = self.dynamic_grid_manager.get_dynamic_spacing(
                ccxt_symbol,
                base_take_profit,
                base_grid_spacing,
                max_cfg
            )
        else:
            take_profit = base_take_profit
            grid_spacing = base_grid_spacing

        bid_skew, ask_skew = self.glft_controller.calculate_spread_skew(
            sym_state.long_position,
            sym_state.short_position,
            grid_spacing,
            max_cfg
        )

        sym_state.dynamic_take_profit = take_profit
        sym_state.dynamic_grid_spacing = grid_spacing
        sym_state.inventory_ratio = self.glft_controller.calculate_inventory_ratio(
            sym_state.long_position, sym_state.short_position
        )

        if leading_reason and leading_reason != "正常":
            logger.debug(f"[LeadingIndicator] {sym_config.symbol} 間距調整: {leading_reason}")

        return take_profit, grid_spacing

    def _get_adjusted_quantity(
        self,
        sym_config: SymbolConfig,
        sym_state: SymbolState,
        side: str,
        is_take_profit: bool
    ) -> float:
        max_cfg = self.config.max_enhancement
        base_qty = sym_config.initial_quantity

        if is_take_profit:
            if side == 'long':
                if sym_state.long_position > sym_config.position_limit:
                    base_qty *= 2
                elif sym_state.short_position >= sym_config.position_threshold:
                    base_qty *= 2
            else:
                if sym_state.short_position > sym_config.position_limit:
                    base_qty *= 2
                elif sym_state.long_position >= sym_config.position_threshold:
                    base_qty *= 2

        if not is_take_profit:
            base_qty = self.glft_controller.adjust_order_quantity(
                base_qty, side,
                sym_state.long_position, sym_state.short_position,
                max_cfg
            )

        if self.funding_manager:
            long_bias, short_bias = self.funding_manager.get_position_bias(
                sym_config.ccxt_symbol, max_cfg
            )
            if side == 'long':
                base_qty *= long_bias
            else:
                base_qty *= short_bias

        return max(sym_config.initial_quantity * 0.5, base_qty)

    def _check_and_reduce_positions(self, sym_config: SymbolConfig, sym_state: SymbolState):
        REDUCE_COOLDOWN = 60
        ccxt_symbol = sym_config.ccxt_symbol
        local_threshold = sym_config.position_threshold * 0.8
        reduce_qty = sym_config.position_threshold * 0.1

        last_reduce = self.state.last_reduce_time.get(ccxt_symbol, 0)
        if time.time() - last_reduce < REDUCE_COOLDOWN:
            return

        if sym_state.long_position >= local_threshold and sym_state.short_position >= local_threshold:
            logger.info(f"[風控] {sym_config.symbol} 多空持倉均超過 {local_threshold}，開始雙向減倉")
            if sym_state.long_position > 0:
                self.place_order(ccxt_symbol, 'sell', 0, reduce_qty, True, 'long', 'market')
            if sym_state.short_position > 0:
                self.place_order(ccxt_symbol, 'buy', 0, reduce_qty, True, 'short', 'market')
            self.state.last_reduce_time[ccxt_symbol] = time.time()

    def _should_adjust_grid(self, sym_config: SymbolConfig, sym_state: SymbolState, side: str) -> bool:
        price = sym_state.latest_price
        deviation_threshold = sym_config.grid_spacing * 0.5

        if side == 'long':
            if sym_state.buy_long_orders <= 0 or sym_state.sell_long_orders <= 0:
                return True
            if sym_state.last_grid_price_long > 0:
                deviation = abs(price - sym_state.last_grid_price_long) / sym_state.last_grid_price_long
                return deviation >= deviation_threshold
            return True
        else:
            if sym_state.buy_short_orders <= 0 or sym_state.sell_short_orders <= 0:
                return True
            if sym_state.last_grid_price_short > 0:
                deviation = abs(price - sym_state.last_grid_price_short) / sym_state.last_grid_price_short
                return deviation >= deviation_threshold
            return True

    async def adjust_grid(self, ccxt_symbol: str):
        sym_config = None
        for cfg in self.config.symbols.values():
            if cfg.ccxt_symbol == ccxt_symbol and cfg.enabled:
                sym_config = cfg
                break

        if not sym_config:
            return

        sym_state = self.state.symbols.get(ccxt_symbol)
        if not sym_state:
            return

        price = sym_state.latest_price
        if price <= 0:
            return

        if self.config.dgt.enabled:
            if ccxt_symbol not in self.dgt_manager.boundaries:
                self.dgt_manager.initialize_boundary(
                    ccxt_symbol, price, sym_config.grid_spacing, num_grids=10
                )
            accumulated = self.dgt_manager.accumulated_profits.get(ccxt_symbol, 0)
            reset, reset_info = self.dgt_manager.check_and_reset(ccxt_symbol, price, accumulated)
            if reset and reset_info:
                logger.info(f"[DGT] {sym_config.symbol} 邊界重置 #{reset_info['reset_count']}: "
                           f"{reset_info['direction']}破, 中心價 {reset_info['old_center']:.4f} → {reset_info['new_center']:.4f}")

        if self.config.bandit.enabled:
            bandit_params = self.bandit_optimizer.get_current_params()
            sym_config.grid_spacing = bandit_params.grid_spacing
            sym_config.take_profit_spacing = bandit_params.take_profit_spacing
            if self.config.max_enhancement.all_enhancements_enabled:
                self.config.max_enhancement.gamma = bandit_params.gamma

        self.dynamic_grid_manager.update_price(ccxt_symbol, price)
        self._check_and_reduce_positions(sym_config, sym_state)

        if sym_state.long_position == 0:
            if time.time() - self.last_order_times.get(f"{ccxt_symbol}_long", 0) > 10:
                if sym_state.best_bid > 0:
                    self.cancel_orders_for_side(ccxt_symbol, 'long')
                    qty = self._get_adjusted_quantity(sym_config, sym_state, 'long', False)
                    self.place_order(ccxt_symbol, 'buy', sym_state.best_bid, qty, False, 'long')
                    self.last_order_times[f"{ccxt_symbol}_long"] = time.time()
                    sym_state.last_grid_price_long = price
        else:
            if time.time() - self.last_order_times.get(f"{ccxt_symbol}_long_grid", 0) > 10:
                if self._should_adjust_grid(sym_config, sym_state, 'long'):
                    await self._place_grid(ccxt_symbol, sym_config, 'long')
                    self.last_order_times[f"{ccxt_symbol}_long_grid"] = time.time()
                    sym_state.last_grid_price_long = price

        if sym_state.short_position == 0:
            if time.time() - self.last_order_times.get(f"{ccxt_symbol}_short", 0) > 10:
                if sym_state.best_ask > 0:
                    self.cancel_orders_for_side(ccxt_symbol, 'short')
                    qty = self._get_adjusted_quantity(sym_config, sym_state, 'short', False)
                    self.place_order(ccxt_symbol, 'sell', sym_state.best_ask, qty, False, 'short')
                    self.last_order_times[f"{ccxt_symbol}_short"] = time.time()
                    sym_state.last_grid_price_short = price
        else:
            if time.time() - self.last_order_times.get(f"{ccxt_symbol}_short_grid", 0) > 10:
                if self._should_adjust_grid(sym_config, sym_state, 'short'):
                    await self._place_grid(ccxt_symbol, sym_config, 'short')
                    self.last_order_times[f"{ccxt_symbol}_short_grid"] = time.time()
                    sym_state.last_grid_price_short = price

    async def _place_grid(self, ccxt_symbol: str, sym_config: SymbolConfig, side: str):
        sym_state = self.state.symbols[ccxt_symbol]
        price = sym_state.latest_price

        take_profit_spacing, grid_spacing = self._get_dynamic_spacing(sym_config, sym_state)
        tp_qty = self._get_adjusted_quantity(sym_config, sym_state, side, True)
        base_qty = self._get_adjusted_quantity(sym_config, sym_state, side, False)

        if side == 'long':
            my_position = sym_state.long_position
            opposite_position = sym_state.short_position
            dead_mode_flag = sym_state.long_dead_mode
        else:
            my_position = sym_state.short_position
            opposite_position = sym_state.long_position
            dead_mode_flag = sym_state.short_dead_mode

        is_dead = GridStrategy.is_dead_mode(my_position, sym_config.position_threshold)

        if is_dead:
            if not dead_mode_flag:
                if side == 'long':
                    sym_state.long_dead_mode = True
                else:
                    sym_state.short_dead_mode = True
                logger.info(f"[MAX] {sym_config.symbol} {side}頭進入裝死模式 (持倉:{my_position})")

            self.cancel_orders_for_side(ccxt_symbol, side)
            special_price = GridStrategy.calculate_dead_mode_price(
                price, my_position, opposite_position, side
            )

            if side == 'long':
                self.place_order(ccxt_symbol, 'sell', special_price, tp_qty, True, 'long')
                sym_state.sell_long_orders = tp_qty
            else:
                self.place_order(ccxt_symbol, 'buy', special_price, tp_qty, True, 'short')
                sym_state.buy_short_orders = tp_qty
            logger.info(f"[MAX] {sym_config.symbol} {side}頭裝死止盈@{special_price:.4f}")
        else:
            if dead_mode_flag:
                if side == 'long':
                    sym_state.long_dead_mode = False
                else:
                    sym_state.short_dead_mode = False
                logger.info(f"[MAX] {sym_config.symbol} {side}頭離開裝死模式")

            self.cancel_orders_for_side(ccxt_symbol, side)
            tp_price, entry_price = GridStrategy.calculate_grid_prices(
                price, take_profit_spacing, grid_spacing, side
            )

            if side == 'long':
                if sym_state.long_position > 0:
                    self.place_order(ccxt_symbol, 'sell', tp_price, tp_qty, True, 'long')
                    sym_state.sell_long_orders = tp_qty
                self.place_order(ccxt_symbol, 'buy', entry_price, base_qty, False, 'long')
                sym_state.buy_long_orders = base_qty
            else:
                if sym_state.short_position > 0:
                    self.place_order(ccxt_symbol, 'buy', tp_price, tp_qty, True, 'short')
                    sym_state.buy_short_orders = tp_qty
                self.place_order(ccxt_symbol, 'sell', entry_price, base_qty, False, 'short')
                sym_state.sell_short_orders = base_qty

            logger.info(f"[MAX] {sym_config.symbol} {side}頭 止盈@{tp_price:.4f}({tp_qty:.1f}) "
                       f"補倉@{entry_price:.4f}({base_qty:.1f}) [TP:{take_profit_spacing*100:.2f}%/GS:{grid_spacing*100:.2f}%]")

    async def _handle_ticker(self, data: dict):
        # Implementation assumed from existing code (will be injected via WS loop)
        pass 

    # WebSocket handling methods need to be included as they are part of the bot logic
    async def _websocket_loop(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        while not self._stop_event.is_set():
            try:
                async with ccxt_async.websockets.connect(self.config.websocket_url, ssl=ssl_context) as ws:
                    self.state.connected = True
                    logger.info("[Bitget WS] 公共 WebSocket 已連接")
                    
                    subscribe_args = []
                    for cfg in self.config.symbols.values():
                        if cfg.enabled:
                            subscribe_args.append({
                                "instType": "USDT-FUTURES",
                                "channel": "ticker",
                                "instId": cfg.symbol
                            })

                    if subscribe_args:
                        await ws.send(json.dumps({
                            "op": "subscribe",
                            "args": subscribe_args
                        }))
                        logger.info(f"[Bitget WS] 已訂閱 {len(subscribe_args)} 個交易對")

                    while not self._stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            if "data" in data:
                                await self._handle_bitget_ticker(data)
                        except asyncio.TimeoutError:
                            await ws.ping()
            except Exception as e:
                self.state.connected = False
                if not self._stop_event.is_set():
                    logger.error(f"[Bitget WS] 公共 WebSocket 錯誤: {e}")
                    await asyncio.sleep(5)

    async def _private_websocket_loop(self):
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        while not self._stop_event.is_set():
            try:
                async with ccxt_async.websockets.connect(self.config.private_ws_url, ssl=ssl_context) as ws:
                    logger.info("[Bitget WS] 私有 WebSocket 已連接")
                    auth_args = self._generate_ws_signature()
                    await ws.send(json.dumps({"op": "login", "args": [auth_args]}))
                    
                    login_response = await asyncio.wait_for(ws.recv(), timeout=10)
                    login_data = json.loads(login_response)
                    if login_data.get("code") == 0 or login_data.get("code") == "0":
                         logger.info("[Bitget WS] 私有 WebSocket 登錄成功")
                    else:
                        logger.error(f"[Bitget WS] 登錄失敗: {login_data}")
                        await asyncio.sleep(5)
                        continue

                    await ws.send(json.dumps({
                        "op": "subscribe",
                        "args": [
                            {"instType": "USDT-FUTURES", "channel": "orders", "instId": "default"},
                            {"instType": "USDT-FUTURES", "channel": "positions", "instId": "default"},
                            {"instType": "USDT-FUTURES", "channel": "account", "coin": "default"}
                        ]
                    }))

                    while not self._stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)
                            if "data" in data:
                                channel = data.get("arg", {}).get("channel", "")
                                if channel == "orders":
                                    await self._handle_bitget_order_update(data)
                                elif channel == "positions":
                                    await self._handle_bitget_position_update(data)
                                elif channel == "account":
                                    await self._handle_bitget_account_update(data)
                        except asyncio.TimeoutError:
                            await ws.ping()
            except Exception as e:
                if not self._stop_event.is_set():
                    logger.error(f"[Bitget WS] 私有 WebSocket 錯誤: {e}")
                    await asyncio.sleep(5)

    async def _handle_bitget_ticker(self, data: dict):
        try:
            ticker_data = data.get("data", [{}])[0]
            inst_id = ticker_data.get("instId", "")
            bid = float(ticker_data.get("bidPr", 0))
            ask = float(ticker_data.get("askPr", 0))

            if not bid or not ask:
                return

            for sym_config in self.config.symbols.values():
                if sym_config.enabled and sym_config.symbol == inst_id:
                    ccxt_symbol = sym_config.ccxt_symbol
                    state = self.state.symbols.get(ccxt_symbol)
                    if state:
                        state.best_bid = bid
                        state.best_ask = ask
                        state.latest_price = (bid + ask) / 2
                        self.leading_indicator.update_spread(ccxt_symbol, bid, ask)
                        await self.adjust_grid(ccxt_symbol)
                    break
            
            if time.time() - self.last_sync_time > self.config.sync_interval:
                self.sync_all()
                self.last_sync_time = time.time()
        except Exception as e:
            logger.error(f"[Bitget] 處理 ticker 失敗: {e}")

    async def _handle_bitget_order_update(self, data: dict):
        try:
            for order in data.get("data", []):
                inst_id = order.get("instId", "")
                order_status = order.get("status", "")
                side = order.get("side", "")
                pos_side = order.get("posSide", "").lower()
                realized_pnl = float(order.get("pnl", 0) or 0)

                ccxt_symbol = None
                for cfg in self.config.symbols.values():
                    if cfg.symbol == inst_id:
                        ccxt_symbol = cfg.ccxt_symbol
                        break
                
                if not ccxt_symbol or ccxt_symbol not in self.state.symbols:
                    continue
                
                sym_state = self.state.symbols[ccxt_symbol]

                if order_status == "filled":
                    sym_state.total_trades += 1
                    self.state.total_trades += 1
                    if realized_pnl != 0:
                        sym_state.total_profit += realized_pnl
                        self.state.total_profit += realized_pnl
                        trade_side = 'long' if pos_side == 'long' else 'short'
                        self.bandit_optimizer.record_trade(realized_pnl, trade_side)
                        self.dgt_manager.accumulated_profits[ccxt_symbol] = \
                            self.dgt_manager.accumulated_profits.get(ccxt_symbol, 0) + realized_pnl
                        
                        # Record trade for leading indicator (using avg price if available)
                        exec_price = float(order.get('priceAvg', 0) or order.get('price', 0) or 0)
                        exec_qty = float(order.get('size', 0) or 0) # API spec usually 'size'
                        if exec_price > 0 and exec_qty > 0:
                             self.leading_indicator.record_trade(ccxt_symbol, exec_price, exec_qty, 'buy' if side == 'buy' else 'sell')

                    if pos_side == 'long':
                        if side == 'buy': sym_state.buy_long_orders = 0
                        else: sym_state.sell_long_orders = 0
                    elif pos_side == 'short':
                        if side == 'sell': sym_state.sell_short_orders = 0
                        else: sym_state.buy_short_orders = 0
                    
                    await self.adjust_grid(ccxt_symbol)

                elif order_status == "cancelled":
                    if pos_side == 'long':
                        if side == 'buy': sym_state.buy_long_orders = 0
                        else: sym_state.sell_long_orders = 0
                    elif pos_side == 'short':
                        if side == 'sell': sym_state.sell_short_orders = 0
                        else: sym_state.buy_short_orders = 0
        except Exception as e:
            logger.error(f"[Bitget] 處理訂單更新失敗: {e}")

    async def _handle_bitget_position_update(self, data: dict):
        try:
            for pos in data.get("data", []):
                inst_id = pos.get("instId", "")
                hold_side = pos.get("holdSide", "")
                total = float(pos.get("total", 0))
                unrealized_pnl = float(pos.get("upl", 0))

                ccxt_symbol = None
                for cfg in self.config.symbols.values():
                    if cfg.symbol == inst_id:
                        ccxt_symbol = cfg.ccxt_symbol
                        break
                
                if ccxt_symbol and ccxt_symbol in self.state.symbols:
                    sym_state = self.state.symbols[ccxt_symbol]
                    if hold_side == "long":
                        sym_state.long_position = total
                    elif hold_side == "short":
                        sym_state.short_position = total
                    sym_state.unrealized_pnl = unrealized_pnl
        except Exception as e:
            logger.error(f"[Bitget] 處理持倉更新失敗: {e}")

    async def _handle_bitget_account_update(self, data: dict):
        try:
            for account in data.get("data", []):
                coin = account.get("marginCoin", "")
                equity_value = float(account.get("equity", 0))
                available = float(account.get("available", 0))
                upl = float(account.get("upl", 0))

                if coin in ["USDT", "USDC"]:
                    acc = self.state.get_account(coin)
                    acc.wallet_balance = equity_value - upl
                    acc.unrealized_pnl = upl
                    acc.available_balance = available
            self.state.update_totals()
        except Exception as e:
             logger.error(f"[Bitget] 處理帳戶更新失敗: {e}")

    async def _keep_alive_loop(self):
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(25)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def run(self):
        try:
            self._init_exchange()
            self._check_hedge_mode()
            self.state.running = True
            self.state.start_time = datetime.now()
            self.sync_all()
            
            logger.info("=" * 60)
            logger.info("🚀 [交易啟動] AS Grid Trading (Bitget MAX)")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ [MAX Bitget] 初始化失敗: {e}")
            self.state.running = False
            return

        self.tasks = [
            asyncio.create_task(self._websocket_loop()),
            asyncio.create_task(self._private_websocket_loop()),
            asyncio.create_task(self._keep_alive_loop())
        ]

        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(0.5)
        finally:
            await self.stop()

    async def stop(self):
        self._stop_event.set()
        self.state.running = False
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
