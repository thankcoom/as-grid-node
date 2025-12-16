import math
import time
import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import numpy as np
from .models import (
    BanditConfig, MarketContext, ParameterArm,
    MaxEnhancement, DGTConfig, LeadingIndicatorConfig
)

logger = logging.getLogger(__name__)

class GridStrategy:
    """
    網格策略核心邏輯 - 統一回測與實盤

    此類提取所有策略計算邏輯，確保回測與實盤行為一致。
    不包含任何 I/O 操作（下單、日誌等），只負責純計算。
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # 常量定義 - 集中管理魔術數字
    # ═══════════════════════════════════════════════════════════════════════════
    DEAD_MODE_FALLBACK_LONG = 1.05    # 多頭裝死模式無對手倉時的止盈比例
    DEAD_MODE_FALLBACK_SHORT = 0.95   # 空頭裝死模式無對手倉時的止盈比例
    DEAD_MODE_DIVISOR = 100           # 裝死模式計算除數 (持倉比/100)

    @staticmethod
    def is_dead_mode(position: float, threshold: float) -> bool:
        """
        判斷是否進入裝死模式
        """
        return position > threshold

    @staticmethod
    def calculate_dead_mode_price(
        base_price: float,
        my_position: float,
        opposite_position: float,
        side: str
    ) -> float:
        """
        計算裝死模式的特殊止盈價格
        """
        if opposite_position > 0:
            r = (my_position / opposite_position) / GridStrategy.DEAD_MODE_DIVISOR + 1
            if side == 'long':
                return base_price * r
            else:  # short
                return base_price / r
        else:
            # 無對手倉，使用固定比例
            if side == 'long':
                return base_price * GridStrategy.DEAD_MODE_FALLBACK_LONG
            else:  # short
                return base_price * GridStrategy.DEAD_MODE_FALLBACK_SHORT

    @staticmethod
    def calculate_tp_quantity(
        base_qty: float,
        my_position: float,
        opposite_position: float,
        position_limit: float,
        position_threshold: float
    ) -> float:
        """
        計算止盈數量
        """
        if my_position > position_limit or opposite_position >= position_threshold:
            return base_qty * 2
        return base_qty

    @staticmethod
    def calculate_grid_prices(
        base_price: float,
        take_profit_spacing: float,
        grid_spacing: float,
        side: str
    ) -> Tuple[float, float]:
        """
        計算正常模式的網格價格
        """
        if side == 'long':
            tp_price = base_price * (1 + take_profit_spacing)
            entry_price = base_price * (1 - grid_spacing)
        else:  # short
            tp_price = base_price * (1 - take_profit_spacing)
            entry_price = base_price * (1 + grid_spacing)

        return tp_price, entry_price

    @staticmethod
    def get_grid_decision(
        price: float,
        my_position: float,
        opposite_position: float,
        position_threshold: float,
        position_limit: float,
        base_qty: float,
        take_profit_spacing: float,
        grid_spacing: float,
        side: str
    ) -> dict:
        """
        獲取完整的網格決策 (主要入口方法)
        """
        dead_mode = GridStrategy.is_dead_mode(my_position, position_threshold)

        tp_qty = GridStrategy.calculate_tp_quantity(
            base_qty, my_position, opposite_position,
            position_limit, position_threshold
        )

        if dead_mode:
            tp_price = GridStrategy.calculate_dead_mode_price(
                price, my_position, opposite_position, side
            )
            return {
                'dead_mode': True,
                'tp_price': tp_price,
                'entry_price': None,
                'tp_qty': tp_qty,
                'entry_qty': 0,
            }
        else:
            tp_price, entry_price = GridStrategy.calculate_grid_prices(
                price, take_profit_spacing, grid_spacing, side
            )
            return {
                'dead_mode': False,
                'tp_price': tp_price,
                'entry_price': entry_price,
                'tp_qty': tp_qty,
                'entry_qty': base_qty,
            }


class UCBBanditOptimizer:
    """
    UCB Bandit 參數優化器 (增強版)
    """

    # AS 網格專用參數組合空間
    DEFAULT_ARMS = [
        # 緊密型 (高頻交易，手續費敏感) - 適合震盪市
        ParameterArm(gamma=0.05, grid_spacing=0.003, take_profit_spacing=0.003),
        ParameterArm(gamma=0.05, grid_spacing=0.004, take_profit_spacing=0.004),
        # 非對稱型 (止盈小於補倉，適合震盪)
        ParameterArm(gamma=0.08, grid_spacing=0.005, take_profit_spacing=0.003),
        ParameterArm(gamma=0.08, grid_spacing=0.006, take_profit_spacing=0.004),
        # 平衡型 - 適合趨勢市
        ParameterArm(gamma=0.10, grid_spacing=0.006, take_profit_spacing=0.004),
        ParameterArm(gamma=0.10, grid_spacing=0.008, take_profit_spacing=0.005),
        # 寬鬆型 (低頻交易) - 適合高波動
        ParameterArm(gamma=0.12, grid_spacing=0.008, take_profit_spacing=0.006),
        ParameterArm(gamma=0.12, grid_spacing=0.010, take_profit_spacing=0.006),
        # 高波動適應型
        ParameterArm(gamma=0.15, grid_spacing=0.010, take_profit_spacing=0.008),
        ParameterArm(gamma=0.15, grid_spacing=0.012, take_profit_spacing=0.008),
    ]

    def __init__(self, config: BanditConfig = None):
        self.config = config or BanditConfig()
        self.arms = self.DEFAULT_ARMS.copy()

        # 每個 arm 的獎勵歷史 (滑動窗口)
        self.rewards: Dict[int, deque] = {
            i: deque(maxlen=self.config.window_size)
            for i in range(len(self.arms))
        }

        # 追蹤狀態
        self.current_arm_idx: int = 0
        self.total_pulls: int = 0
        self.pull_counts: Dict[int, int] = {i: 0 for i in range(len(self.arms))}

        # 交易追蹤 (用於計算 reward)
        self.pending_trades: List[Dict] = []
        self.trade_count_since_update: int = 0

        # 統計
        self.best_arm_history: List[int] = []
        self.cumulative_reward: float = 0

        # === 新增: Contextual Bandit 狀態 ===
        self.current_context: str = MarketContext.RANGING
        self.price_history: deque = deque(maxlen=100)  # 價格歷史 (用於計算市場狀態)

        # 每個 context 的獨立統計
        self.context_rewards: Dict[str, Dict[int, deque]] = {
            ctx: {i: deque(maxlen=self.config.window_size) for i in range(len(self.arms))}
            for ctx in [MarketContext.RANGING, MarketContext.TRENDING_UP,
                       MarketContext.TRENDING_DOWN, MarketContext.HIGH_VOLATILITY]
        }
        self.context_pulls: Dict[str, Dict[int, int]] = {
            ctx: {i: 0 for i in range(len(self.arms))}
            for ctx in [MarketContext.RANGING, MarketContext.TRENDING_UP,
                       MarketContext.TRENDING_DOWN, MarketContext.HIGH_VOLATILITY]
        }

        # === 新增: Thompson Sampling 狀態 ===
        # Beta 分布參數 (alpha, beta) 用於每個 arm
        self.thompson_alpha: Dict[int, float] = {
            i: self.config.thompson_prior_alpha for i in range(len(self.arms))
        }
        self.thompson_beta: Dict[int, float] = {
            i: self.config.thompson_prior_beta for i in range(len(self.arms))
        }

        # === 新增: 動態生成的 arm (Thompson Sampling 探索) ===
        self.dynamic_arm: Optional[ParameterArm] = None
        self.dynamic_arm_reward: float = 0

        # === 冷啟動初始化 ===
        if self.config.cold_start_enabled:
            self._cold_start_init()

        logger.info(f"[Bandit] 增強版初始化完成，共 {len(self.arms)} 個參數組合")

    def _cold_start_init(self):
        # 設定初始 arm 為歷史最佳
        self.current_arm_idx = self.config.cold_start_arm_idx

        # 為推薦 arm 預載一些虛擬正向獎勵 (給予信任)
        recommended_arms = [4, 5]  # 平衡型
        for arm_idx in recommended_arms:
            self.rewards[arm_idx].append(0.5)  # 預設正向獎勵
            self.pull_counts[arm_idx] = 1
            self.total_pulls += 1

        logger.info(f"[Bandit] 冷啟動: 初始 arm={self.current_arm_idx}")

    def update_price(self, price: float):
        self.price_history.append(price)

    def detect_market_context(self) -> str:
        if not self.config.contextual_enabled:
            return MarketContext.RANGING

        if len(self.price_history) < self.config.volatility_lookback:
            return self.current_context  # 數據不足，保持當前狀態

        prices = list(self.price_history)

        # 計算波動率
        recent_prices = prices[-self.config.volatility_lookback:]
        volatility = np.std(recent_prices) / np.mean(recent_prices)

        # 檢查高波動
        if volatility > self.config.high_volatility_threshold:
            self.current_context = MarketContext.HIGH_VOLATILITY
            return self.current_context

        # 計算趨勢 (簡單線性回歸)
        if len(prices) >= self.config.trend_lookback:
            trend_prices = prices[-self.config.trend_lookback:]
            x = np.arange(len(trend_prices))
            slope = np.polyfit(x, trend_prices, 1)[0]
            trend_pct = slope / np.mean(trend_prices)

            if trend_pct > self.config.trend_threshold:
                self.current_context = MarketContext.TRENDING_UP
            elif trend_pct < -self.config.trend_threshold:
                self.current_context = MarketContext.TRENDING_DOWN
            else:
                self.current_context = MarketContext.RANGING
        else:
            self.current_context = MarketContext.RANGING

        return self.current_context

    def _thompson_sample(self) -> int:
        samples = []
        for i in range(len(self.arms)):
            sample = np.random.beta(self.thompson_alpha[i], self.thompson_beta[i])
            samples.append(sample)
        return int(np.argmax(samples))

    def _generate_dynamic_arm(self) -> Optional[ParameterArm]:
        if not self.config.thompson_enabled:
            return None

        # 找到最佳 arm
        best_idx = self._get_best_arm()
        best_arm = self.arms[best_idx]

        # 參數擾動
        perturbation = self.config.param_perturbation

        # 隨機擾動方向
        gamma_delta = np.random.uniform(-perturbation, perturbation) * best_arm.gamma
        gs_delta = np.random.uniform(-perturbation, perturbation) * best_arm.grid_spacing
        tp_delta = np.random.uniform(-perturbation, perturbation) * best_arm.take_profit_spacing

        # 生成新參數 (確保在合理範圍內)
        new_gamma = max(0.01, min(0.3, best_arm.gamma + gamma_delta))
        new_gs = max(0.002, min(0.02, best_arm.grid_spacing + gs_delta))
        new_tp = max(0.002, min(0.015, best_arm.take_profit_spacing + tp_delta))

        # 確保 tp < gs
        if new_tp >= new_gs:
            new_tp = new_gs * 0.7

        return ParameterArm(gamma=new_gamma, grid_spacing=new_gs, take_profit_spacing=new_tp)

    def _calculate_reward(self, pnls: List[float]) -> float:
        if not pnls:
            return 0

        # 1. Sharpe-like reward
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls) if np.std(pnls) > 0 else 0.001
        sharpe = mean_pnl / std_pnl

        # 2. Max Drawdown 計算
        cumsum = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumsum)
        drawdowns = running_max - cumsum
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0

        # 正規化 MDD (相對於總收益)
        total_pnl = sum(pnls)
        mdd_ratio = max_drawdown / abs(total_pnl) if total_pnl != 0 else 0
        mdd_penalty = self.config.mdd_penalty_weight * mdd_ratio

        # 3. 勝率獎勵
        win_rate = len([p for p in pnls if p > 0]) / len(pnls) if pnls else 0
        win_bonus = self.config.win_rate_bonus * (win_rate - 0.5)  # 50% 為基準

        # 綜合 reward
        reward = sharpe - mdd_penalty + win_bonus
        return reward

    def _update_thompson(self, reward: float):
        arm_idx = self.current_arm_idx
        prob_success = 1 / (1 + np.exp(-reward))
        self.thompson_alpha[arm_idx] += prob_success
        self.thompson_beta[arm_idx] += (1 - prob_success)

    def get_current_params(self) -> ParameterArm:
        if self.dynamic_arm and self.dynamic_arm_reward > 0:
            return self.dynamic_arm
        return self.arms[self.current_arm_idx]

    def select_arm(self) -> int:
        for i in range(len(self.arms)):
            if self.pull_counts[i] < self.config.min_pulls_per_arm:
                return i

        if self.config.contextual_enabled:
            context = self.detect_market_context()
            recommended = MarketContext.RECOMMENDED_ARMS.get(context, list(range(len(self.arms))))
        else:
            recommended = list(range(len(self.arms)))

        if self.config.thompson_enabled and np.random.random() < 0.3:
            thompson_choice = self._thompson_sample()
            if thompson_choice in recommended:
                return thompson_choice

        ucb_values = []
        for i in range(len(self.arms)):
            if i not in recommended:
                ucb_values.append(float('-inf'))
                continue

            rewards = list(self.rewards[i])
            if not rewards:
                ucb_values.append(float('inf'))
                continue

            mean_reward = np.mean(rewards)
            confidence = self.config.exploration_factor * np.sqrt(
                2 * np.log(self.total_pulls + 1) / len(rewards)
            )
            ucb_values.append(mean_reward + confidence)

        return int(np.argmax(ucb_values))

    def record_trade(self, pnl: float, side: str):
        if not self.config.enabled:
            return

        self.pending_trades.append({
            'pnl': pnl,
            'side': side,
            'arm_idx': self.current_arm_idx,
            'context': self.current_context,
            'timestamp': time.time()
        })
        self.trade_count_since_update += 1

        if self.trade_count_since_update >= self.config.update_interval:
            self._update_and_select()

    def _update_and_select(self):
        if not self.pending_trades:
            return

        pnls = [t['pnl'] for t in self.pending_trades]
        reward = self._calculate_reward(pnls)

        arm_idx = self.current_arm_idx
        self.rewards[arm_idx].append(reward)
        self.pull_counts[arm_idx] += 1
        self.total_pulls += 1
        self.cumulative_reward += sum(pnls)

        if self.config.contextual_enabled:
            context = self.pending_trades[0].get('context', MarketContext.RANGING)
            self.context_rewards[context][arm_idx].append(reward)
            self.context_pulls[context][arm_idx] += 1

        if self.config.thompson_enabled:
            self._update_thompson(reward)

        new_arm_idx = self.select_arm()
        if new_arm_idx != self.current_arm_idx:
            old_params = self.arms[self.current_arm_idx]
            new_params = self.arms[new_arm_idx]
            logger.info(f"[Bandit] 切換參數: {old_params} → {new_params} "
                       f"(context={self.current_context})")
            self.current_arm_idx = new_arm_idx

        if self.config.thompson_enabled and np.random.random() < 0.1:
            self.dynamic_arm = self._generate_dynamic_arm()
            if self.dynamic_arm:
                logger.info(f"[Bandit] 動態探索: {self.dynamic_arm}")

        self.best_arm_history.append(self._get_best_arm())
        self.pending_trades = []
        self.trade_count_since_update = 0

    def _get_best_arm(self) -> int:
        best_idx = 0
        best_mean = float('-inf')

        for i in range(len(self.arms)):
            rewards = list(self.rewards[i])
            if rewards:
                mean = np.mean(rewards)
                if mean > best_mean:
                    best_mean = mean
                    best_idx = i
        return best_idx


class DGTBoundaryManager:
    """
    DGT 動態邊界管理器
    """

    def __init__(self, config: DGTConfig = None):
        self.config = config or DGTConfig()
        self.boundaries: Dict[str, Dict] = {}
        self.accumulated_profits: Dict[str, float] = {}
        self.reset_counts: Dict[str, int] = {}

    def initialize_boundary(self, symbol: str, center_price: float, grid_spacing: float, num_grids: int = 10):
        half_grids = num_grids // 2
        upper = center_price * ((1 + grid_spacing) ** half_grids)
        lower = center_price * ((1 - grid_spacing) ** half_grids)

        self.boundaries[symbol] = {
            'center': center_price,
            'upper': upper,
            'lower': lower,
            'grid_spacing': grid_spacing,
            'num_grids': num_grids,
            'initialized_at': time.time(),
            'last_reset': time.time()
        }

        self.accumulated_profits[symbol] = 0
        self.reset_counts[symbol] = 0
        logger.info(f"[DGT] {symbol} 邊界初始化: {lower:.4f} ~ {upper:.4f} (中心: {center_price:.4f})")

    def check_and_reset(self, symbol: str, current_price: float, realized_pnl: float = 0) -> Tuple[bool, Optional[Dict]]:
        if not self.config.enabled:
            return False, None

        if symbol not in self.boundaries:
            return False, None

        boundary = self.boundaries[symbol]
        upper = boundary['upper']
        lower = boundary['lower']

        breach_upper = current_price >= upper * (1 - self.config.boundary_buffer)
        breach_lower = current_price <= lower * (1 + self.config.boundary_buffer)

        if not (breach_upper or breach_lower):
            return False, None

        self.accumulated_profits[symbol] += realized_pnl
        old_center = boundary['center']
        new_center = current_price

        if breach_upper:
            reinvest = self.accumulated_profits[symbol] * self.config.profit_reinvest_ratio
            logger.info(f"[DGT] {symbol} 上破重置: {old_center:.4f} → {new_center:.4f}, 再投資: {reinvest:.2f}")
        else:
            reinvest = self.accumulated_profits[symbol]
            logger.info(f"[DGT] {symbol} 下破重置: {old_center:.4f} → {new_center:.4f}, 累積利潤: {reinvest:.2f}")

        self.initialize_boundary(
            symbol,
            new_center,
            boundary['grid_spacing'],
            boundary['num_grids']
        )

        self.reset_counts[symbol] += 1
        self.accumulated_profits[symbol] = 0

        return True, {
            'old_center': old_center,
            'new_center': new_center,
            'direction': 'upper' if breach_upper else 'lower',
            'reinvest_amount': reinvest,
            'reset_count': self.reset_counts[symbol]
        }


class FundingRateManager:
    """
    Funding Rate 管理器
    """

    def __init__(self, exchange):
        self.exchange = exchange
        self.funding_rates: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        self.update_interval = 60  # 每 60 秒更新一次

    def update_funding_rate(self, symbol: str) -> float:
        now = time.time()
        if symbol in self.last_update:
            if now - self.last_update[symbol] < self.update_interval:
                return self.funding_rates.get(symbol, 0)

        try:
            funding_info = self.exchange.fetch_funding_rate(symbol)
            rate = float(funding_info.get('fundingRate', 0) or 0)
            self.funding_rates[symbol] = rate
            self.last_update[symbol] = now
            logger.info(f"[Funding] {symbol} funding rate: {rate*100:.4f}%")
            return rate
        except Exception as e:
            logger.error(f"[Funding] 獲取 {symbol} funding rate 失敗: {e}")
            return self.funding_rates.get(symbol, 0)

    def get_position_bias(self, symbol: str, config: MaxEnhancement) -> Tuple[float, float]:
        if not config.is_feature_enabled('funding_rate'):
            return 1.0, 1.0

        rate = self.funding_rates.get(symbol, 0)
        if abs(rate) < config.funding_rate_threshold:
            return 1.0, 1.0

        bias = config.funding_rate_position_bias
        if rate > 0:
            # 多付空收 → 減少多頭，增加空頭
            long_bias = 1.0 - bias
            short_bias = 1.0 + bias
        else:
            # 空付多收 → 增加多頭，減少空頭
            long_bias = 1.0 + bias
            short_bias = 1.0 - bias
        return long_bias, short_bias


class GLFTController:
    """
    GLFT (Guéant-Lehalle-Fernandez-Tapia) 庫存控制器
    """

    def calculate_inventory_ratio(self, long_pos: float, short_pos: float) -> float:
        total = long_pos + short_pos
        if total <= 0:
            return 0.0
        return (long_pos - short_pos) / total

    def calculate_spread_skew(
        self,
        long_pos: float,
        short_pos: float,
        base_spread: float,
        config: MaxEnhancement
    ) -> Tuple[float, float]:
        if not config.is_feature_enabled('glft'):
            return 0.0, 0.0

        inventory_ratio = self.calculate_inventory_ratio(long_pos, short_pos)
        skew = inventory_ratio * base_spread * config.gamma
        bid_skew = -skew
        ask_skew = skew
        return bid_skew, ask_skew

    def adjust_order_quantity(
        self,
        base_qty: float,
        side: str,
        long_pos: float,
        short_pos: float,
        config: MaxEnhancement
    ) -> float:
        if not config.is_feature_enabled('glft'):
            return base_qty

        inventory_ratio = self.calculate_inventory_ratio(long_pos, short_pos)
        if side == 'long':
            adjust = 1.0 - inventory_ratio * config.gamma
        else:
            adjust = 1.0 + inventory_ratio * config.gamma

        adjust = max(0.5, min(1.5, adjust))
        return base_qty * adjust


class DynamicGridManager:
    """
    動態網格管理器
    """

    def __init__(self):
        self.price_history: Dict[str, deque] = {}
        self.atr_cache: Dict[str, float] = {}
        self.last_calc_time: Dict[str, float] = {}
        self.calc_interval = 60  # 每 60 秒重算一次

    def update_price(self, symbol: str, price: float):
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=1000)
        self.price_history[symbol].append({
            'price': price,
            'time': time.time()
        })

    def calculate_atr(self, symbol: str, config: MaxEnhancement) -> float:
        now = time.time()
        if symbol in self.last_calc_time:
            if now - self.last_calc_time[symbol] < self.calc_interval:
                return self.atr_cache.get(symbol, 0.005)

        history = self.price_history.get(symbol, deque())
        if len(history) < config.volatility_lookback:
            return 0.005

        recent_prices = [h['price'] for h in list(history)[-config.volatility_lookback:]]
        returns = []
        for i in range(1, len(recent_prices)):
            if recent_prices[i-1] > 0:
                ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                returns.append(ret)

        if not returns:
            return 0.005

        volatility = np.std(returns) * config.atr_multiplier
        volatility = max(config.min_spacing, min(config.max_spacing, volatility))

        self.atr_cache[symbol] = volatility
        self.last_calc_time[symbol] = now
        return volatility

    def get_dynamic_spacing(
        self,
        symbol: str,
        base_take_profit: float,
        base_grid_spacing: float,
        config: MaxEnhancement
    ) -> Tuple[float, float]:
        if not config.is_feature_enabled('dynamic_grid'):
            return base_take_profit, base_grid_spacing

        atr = self.calculate_atr(symbol, config)
        dynamic_tp = atr * 0.5
        dynamic_tp = max(config.min_spacing, min(config.max_spacing * 0.6, dynamic_tp))
        dynamic_gs = atr
        dynamic_gs = max(config.min_spacing * 1.5, min(config.max_spacing, dynamic_gs))

        if dynamic_tp >= dynamic_gs:
            dynamic_tp = dynamic_gs * 0.6

        return dynamic_tp, dynamic_gs


class LeadingIndicatorManager:
    """
    領先指標管理器
    """

    def __init__(self, config: LeadingIndicatorConfig = None):
        self.config = config or LeadingIndicatorConfig()
        self.trade_history: Dict[str, deque] = {}
        self.spread_history: Dict[str, deque] = {}
        self.ofi_history: Dict[str, deque] = {}
        self.current_ofi: Dict[str, float] = {}
        self.current_volume_ratio: Dict[str, float] = {}
        self.current_spread_ratio: Dict[str, float] = {}
        self.active_signals: Dict[str, List[str]] = {}
        logger.info("[LeadingIndicator] 領先指標管理器初始化完成")

    def _ensure_symbol_data(self, symbol: str):
        if symbol not in self.trade_history:
            self.trade_history[symbol] = deque(maxlen=500)
        if symbol not in self.spread_history:
            self.spread_history[symbol] = deque(maxlen=200)
        if symbol not in self.ofi_history:
            self.ofi_history[symbol] = deque(maxlen=100)

    def record_trade(self, symbol: str, price: float, quantity: float, side: str):
        if not self.config.enabled:
            return
        self._ensure_symbol_data(symbol)
        self.trade_history[symbol].append({
            'time': time.time(),
            'price': price,
            'quantity': quantity,
            'side': side,
            'value': price * quantity
        })

    def update_spread(self, symbol: str, bid: float, ask: float):
        if not self.config.enabled or bid <= 0 or ask <= 0:
            return
        self._ensure_symbol_data(symbol)
        mid_price = (bid + ask) / 2
        spread_bps = (ask - bid) / mid_price * 10000
        self.spread_history[symbol].append({
            'time': time.time(),
            'bid': bid,
            'ask': ask,
            'spread_bps': spread_bps
        })

    def calculate_ofi(self, symbol: str) -> float:
        if symbol not in self.trade_history:
            return 0.0

        trades = list(self.trade_history[symbol])
        if len(trades) < self.config.ofi_lookback:
            return 0.0

        recent = trades[-self.config.ofi_lookback:]
        buy_volume = sum(t['value'] for t in recent if t['side'] == 'buy')
        sell_volume = sum(t['value'] for t in recent if t['side'] == 'sell')
        total = buy_volume + sell_volume
        if total <= 0:
            return 0.0

        ofi = (buy_volume - sell_volume) / total
        self.current_ofi[symbol] = ofi
        self.ofi_history[symbol].append({
            'time': time.time(),
            'ofi': ofi,
            'buy_vol': buy_volume,
            'sell_vol': sell_volume
        })
        return ofi

    def calculate_volume_ratio(self, symbol: str) -> float:
        if symbol not in self.trade_history:
            return 1.0

        trades = list(self.trade_history[symbol])
        if len(trades) < self.config.volume_lookback:
            return 1.0

        now = time.time()
        recent_minute = [t['value'] for t in trades if now - t['time'] < 60]
        historical = trades[-self.config.volume_lookback:]
        current_volume = sum(recent_minute)
        avg_volume_per_trade = np.mean([t['value'] for t in historical])
        expected_volume = avg_volume_per_trade * max(1, len(recent_minute))

        if expected_volume <= 0:
            return 1.0

        ratio = current_volume / expected_volume
        self.current_volume_ratio[symbol] = ratio
        return ratio

    def calculate_spread_ratio(self, symbol: str) -> float:
        if symbol not in self.spread_history:
            return 1.0

        spreads = list(self.spread_history[symbol])
        if len(spreads) < self.config.spread_lookback:
            return 1.0

        current_spread = spreads[-1]['spread_bps']
        avg_spread = np.mean([s['spread_bps'] for s in spreads[-self.config.spread_lookback:]])
        if avg_spread <= 0:
            return 1.0

        ratio = current_spread / avg_spread
        self.current_spread_ratio[symbol] = ratio
        return ratio

    def get_signals(self, symbol: str) -> Tuple[List[str], Dict[str, float]]:
        if not self.config.enabled:
            return [], {}

        signals = []
        ofi = self.calculate_ofi(symbol)
        volume_ratio = self.calculate_volume_ratio(symbol)
        spread_ratio = self.calculate_spread_ratio(symbol)

        values = {
            'ofi': ofi,
            'volume_ratio': volume_ratio,
            'spread_ratio': spread_ratio
        }

        if self.config.ofi_enabled:
            if ofi > self.config.ofi_threshold:
                signals.append('OFI_BUY_PRESSURE')
            elif ofi < -self.config.ofi_threshold:
                signals.append('OFI_SELL_PRESSURE')

        if self.config.volume_enabled:
            if volume_ratio > self.config.volume_surge_threshold:
                signals.append('VOLUME_SURGE')

        if self.config.spread_enabled:
            if spread_ratio > self.config.spread_surge_threshold:
                signals.append('SPREAD_EXPANSION')

        self.active_signals[symbol] = signals
        return signals, values

    def get_spacing_adjustment(self, symbol: str, base_spacing: float) -> Tuple[float, str]:
        if not self.config.enabled:
            return base_spacing, "領先指標關閉"

        signals, values = self.get_signals(symbol)
        if not signals:
            return base_spacing, "正常"

        adjustment = 1.0
        reasons = []

        if 'VOLUME_SURGE' in signals:
            vol_ratio = values.get('volume_ratio', 1.0)
            vol_adj = min(1.5, 1.0 + (vol_ratio - 2.0) * 0.1)
            adjustment = max(adjustment, vol_adj)
            reasons.append(f"放量×{vol_ratio:.1f}")

        if 'SPREAD_EXPANSION' in signals:
            spread_ratio = values.get('spread_ratio', 1.0)
            spread_adj = min(1.4, 1.0 + (spread_ratio - 1.5) * 0.2)
            adjustment = max(adjustment, spread_adj)
            reasons.append(f"價差擴{spread_ratio:.1f}x")

        if 'OFI_BUY_PRESSURE' in signals or 'OFI_SELL_PRESSURE' in signals:
            ofi = abs(values.get('ofi', 0))
            ofi_adj = 1.0 + ofi * 0.2
            adjustment = max(adjustment, ofi_adj)
            direction = "買" if values.get('ofi', 0) > 0 else "賣"
            reasons.append(f"{direction}壓OFI={ofi:.2f}")

        adjustment = min(adjustment, 1.8)
        adjusted_spacing = base_spacing * adjustment
        reason = " + ".join(reasons) if reasons else "正常"
        return adjusted_spacing, reason

    def should_pause_trading(self, symbol: str) -> Tuple[bool, str]:
        if not self.config.enabled:
            return False, ""

        signals, values = self.get_signals(symbol)
        volume_ratio = values.get('volume_ratio', 1.0)
        spread_ratio = values.get('spread_ratio', 1.0)

        if volume_ratio > 4.0 and spread_ratio > 2.0:
            return True, f"極端波動 (Vol={volume_ratio:.1f}x, Spread={spread_ratio:.1f}x)"
        if volume_ratio > 6.0:
            return True, f"異常放量 (Vol={volume_ratio:.1f}x)"
        if spread_ratio > 3.0:
            return True, f"流動性枯竭 (Spread={spread_ratio:.1f}x)"
        return False, ""
