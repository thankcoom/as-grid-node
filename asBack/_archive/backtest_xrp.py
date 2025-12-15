# XRP/USDC 網格策略回測 - 參數優化
import pandas as pd
from datetime import datetime, timedelta
import os

class GridOrderBacktester:
    def __init__(self, df, config):
        self.df = df.reset_index(drop=True)
        self.config = config

        self.long_settings = config["long_settings"]
        self.short_settings = config["short_settings"]

        self.balance = config["initial_balance"]
        self.max_drawdown = config["max_drawdown"]
        self.fee = config["fee_pct"]
        self.direction = config.get("direction", "both")
        self.leverage = config["leverage"]

        self.long_positions = []
        self.short_positions = []
        self.trade_history = []
        self.equity_curve = []
        self.max_equity = self.balance

        self.orders = {"long": [], "short": []}
        self.last_refresh_time = None
        self.last_long_price = None
        self.last_short_price = None

        self._init_orders(self.df['close'].iloc[0])

    def _init_orders(self, price):
        if self.direction in ["long", "both"]:
            self._place_long_orders(price)
        if self.direction in ["short", "both"]:
            self._place_short_orders(price)

    def _place_long_orders(self, current_price):
        """多头网格：上方止盈，下方补仓"""
        self.orders["long"] = [
            (current_price * (1 - self.long_settings["down_spacing"]), "BUY"),
            (current_price * (1 + self.long_settings["up_spacing"]), "SELL")
        ]
        self.last_long_price = current_price

    def _place_short_orders(self, current_price):
        """空头网格：上方补仓，下方止盈"""
        self.orders["short"] = [
            (current_price * (1 + self.short_settings["up_spacing"]), "SELL_SHORT"),
            (current_price * (1 - self.short_settings["down_spacing"]), "COVER_SHORT")
        ]
        self.last_short_price = current_price

    def _update_orders_after_trade(self, side, fill_price):
        if side == "long":
            self._place_long_orders(fill_price)
        elif side == "short":
            self._place_short_orders(fill_price)

    def _refresh_orders_if_needed(self, price, current_time):
        if self.last_refresh_time is None or (current_time - self.last_refresh_time) >= timedelta(
                minutes=self.config["grid_refresh_interval"]):
            if self.direction in ["long", "both"]:
                self._place_long_orders(price)
            if self.direction in ["short", "both"]:
                self._place_short_orders(price)
            self.last_refresh_time = current_time

    def _calculate_unrealized_pnl(self, price):
        long_pnl = sum((price - entry_price) * qty for entry_price, qty, _ in self.long_positions)
        short_pnl = sum((entry_price - price) * qty for entry_price, qty, _ in self.short_positions)
        return long_pnl + short_pnl

    def run(self):
        for _, row in self.df.iterrows():
            if len(self.short_positions) + len(self.long_positions) >= self.config["max_positions"]:
                break

            price = row['close']
            timestamp = row['open_time']
            effective_order_value = self.config["order_value"] * self.leverage

            self._refresh_orders_if_needed(price, timestamp)

            used_margin = sum(pos[2] for pos in self.long_positions + self.short_positions)
            available_margin = self.balance - used_margin

            # LONG SIDE
            if self.direction in ["long", "both"]:
                for order_price, action in self.orders["long"]:
                    if action == "BUY" and price <= order_price:
                        qty = effective_order_value / price
                        notional_value = qty * price
                        margin_required = notional_value / self.leverage
                        fee_cost = qty * price * (self.fee / 2)

                        if (margin_required + fee_cost) > available_margin:
                            continue

                        self.balance -= (margin_required + fee_cost)
                        self.long_positions.append((price, qty, margin_required))

                        unrealized_pnl = self._calculate_unrealized_pnl(price)
                        total_equity = self.balance + unrealized_pnl
                        self.trade_history.append((
                            timestamp, "BUY", price, qty, "LONG",
                            0.0, fee_cost, 0.0, unrealized_pnl, total_equity
                        ))

                        self._update_orders_after_trade("long", price)
                        break

                    elif action == "SELL" and self.long_positions and price >= order_price:
                        entry_price, qty, margin_required = self.long_positions.pop(0)
                        fee_cost = qty * price * (self.fee / 2)
                        gross_pnl = (price - entry_price) * qty
                        net_pnl = gross_pnl - fee_cost

                        self.balance += margin_required + net_pnl

                        unrealized_pnl = self._calculate_unrealized_pnl(price)
                        total_equity = self.balance + unrealized_pnl
                        self.trade_history.append((
                            timestamp, "SELL", price, qty, "LONG",
                            net_pnl, fee_cost, gross_pnl, unrealized_pnl, total_equity
                        ))

                        self._update_orders_after_trade("long", price)
                        break

            # SHORT SIDE
            if self.direction in ["short", "both"]:
                for order_price, action in self.orders["short"]:
                    if action == "SELL_SHORT" and price >= order_price:
                        qty = effective_order_value / price
                        notional_value = qty * price
                        margin_required = notional_value / self.leverage
                        fee_cost = qty * price * (self.fee / 2)

                        if (margin_required + fee_cost) > available_margin:
                            continue

                        self.balance -= (margin_required + fee_cost)
                        self.short_positions.append((price, qty, margin_required))

                        unrealized_pnl = self._calculate_unrealized_pnl(price)
                        total_equity = self.balance + unrealized_pnl
                        self.trade_history.append((
                            timestamp, "SELL_SHORT", price, qty, "SHORT",
                            0.0, fee_cost, 0.0, unrealized_pnl, total_equity
                        ))

                        self._update_orders_after_trade("short", price)
                        break

                    elif action == "COVER_SHORT" and self.short_positions and price <= order_price:
                        entry_price, qty, margin_required = self.short_positions.pop(0)
                        fee_cost = qty * price * (self.fee / 2)
                        gross_pnl = (entry_price - price) * qty
                        net_pnl = gross_pnl - fee_cost

                        self.balance += margin_required + net_pnl

                        unrealized_pnl = self._calculate_unrealized_pnl(price)
                        total_equity = self.balance + unrealized_pnl
                        self.trade_history.append((
                            timestamp, "COVER_SHORT", price, qty, "SHORT",
                            net_pnl, fee_cost, gross_pnl, unrealized_pnl, total_equity
                        ))

                        self._update_orders_after_trade("short", price)
                        break

            # 計算當前盈虧和淨值
            long_pnl = sum((price - entry_price) * qty for entry_price, qty, _ in self.long_positions)
            short_pnl = sum((entry_price - price) * qty for entry_price, qty, _ in self.short_positions)
            unrealized_pnl = long_pnl + short_pnl
            equity = self.balance + unrealized_pnl

            self.max_equity = max(self.max_equity, equity)
            drawdown = 1 - (equity / self.max_equity) if self.max_equity > 0 else 0

            realized_pnl_so_far = sum(trade[5] for trade in self.trade_history)

            self.equity_curve.append((
                timestamp, price, equity,
                realized_pnl_so_far, unrealized_pnl
            ))

            if drawdown >= self.max_drawdown:
                break

        return self.summary(price)

    def summary(self, final_price):
        long_pnl = sum((final_price - entry_price) * qty for entry_price, qty, _ in self.long_positions)
        short_pnl = sum((entry_price - final_price) * qty for entry_price, qty, _ in self.short_positions)
        unrealized_pnl = long_pnl + short_pnl
        realized_pnl = sum(row[5] for row in self.trade_history if row[5] != 0.0)
        final_equity = self.balance + unrealized_pnl

        return {
            "final_equity": final_equity,
            "return_pct": (final_equity - self.config["initial_balance"]) / self.config["initial_balance"],
            "max_drawdown": 1 - final_equity / self.max_equity if self.max_equity > 0 else 0,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": realized_pnl + unrealized_pnl,
            "trades": len(self.trade_history),
            "direction": self.direction
        }


def load_data_for_date(date_str, symbol="XRPUSDC"):
    try:
        path = f"data/futures/um/daily/klines/{symbol}/1m/{symbol}-1m-{date_str}.csv"
        df = pd.read_csv(path)
        if df.empty:
            return None
        df["open_time"] = pd.to_datetime(df["open_time"], unit='ms')
        return df
    except Exception as e:
        return None


def grid_search_backtest():
    """網格搜尋 - 測試多組參數"""

    # 參數組合
    param_sets = []

    # 測試不同的網格間距組合
    spacings = [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.008, 0.01]

    for spacing in spacings:
        # 對稱間距
        param_sets.append({
            "name": f"對稱_{spacing*100:.1f}%",
            "long_settings": {"up_spacing": spacing, "down_spacing": spacing},
            "short_settings": {"up_spacing": spacing, "down_spacing": spacing}
        })

    # 非對稱間距 - 止盈小，補倉大
    for up in [0.002, 0.003, 0.004]:
        for down in [0.004, 0.006, 0.008]:
            if up < down:
                param_sets.append({
                    "name": f"非對稱_止盈{up*100:.1f}%_補倉{down*100:.1f}%",
                    "long_settings": {"up_spacing": up, "down_spacing": down},
                    "short_settings": {"up_spacing": down, "down_spacing": up}
                })

    # 基礎配置
    base_config = {
        "initial_balance": 1000,
        "order_value": 10,
        "max_drawdown": 0.5,
        "max_positions": 50,
        "fee_pct": 0.0004,  # 合約手續費 0.04%
        "direction": "both",
        "leverage": 20,
        "grid_refresh_interval": 5
    }

    # 時間範圍
    start_date = datetime(2025, 10, 27)
    end_date = datetime(2025, 11, 25)

    results = []
    best_result = None
    best_bt = None

    print("=" * 80)
    print("XRP/USDC 網格策略回測 - 參數優化")
    print("=" * 80)
    print(f"時間範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    print(f"初始資金: ${base_config['initial_balance']}")
    print(f"每單金額: ${base_config['order_value']}")
    print(f"槓桿: {base_config['leverage']}x")
    print(f"測試參數組數: {len(param_sets)}")
    print("=" * 80)

    # 載入所有數據
    all_data = []
    current = start_date
    while current <= end_date:
        df = load_data_for_date(current.strftime("%Y-%m-%d"))
        if df is not None:
            all_data.append(df)
        current += timedelta(days=1)

    if not all_data:
        print("❌ 沒有找到數據")
        return None

    full_df = pd.concat(all_data, ignore_index=True)
    print(f"載入數據: {len(full_df)} 條 K 線記錄")
    print("=" * 80)

    for i, params in enumerate(param_sets):
        print(f"\n[{i+1}/{len(param_sets)}] 回測策略: {params['name']}")

        config = base_config.copy()
        config["long_settings"] = params["long_settings"]
        config["short_settings"] = params["short_settings"]

        bt = GridOrderBacktester(full_df.copy(), config)
        result = bt.run()

        result.update({
            "strategy_name": params["name"],
            "long_up": params["long_settings"]["up_spacing"],
            "long_down": params["long_settings"]["down_spacing"],
            "short_up": params["short_settings"]["up_spacing"],
            "short_down": params["short_settings"]["down_spacing"]
        })
        results.append(result)

        print(f"  收益率: {result['return_pct']*100:.2f}% | "
              f"交易次數: {result['trades']} | "
              f"最大回撤: {result['max_drawdown']*100:.2f}%")

        if best_result is None or result["return_pct"] > best_result["return_pct"]:
            best_result = result
            best_bt = bt

    # 輸出結果
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("return_pct", ascending=False)
    df_results.to_csv("xrp_grid_search_results.csv", index=False)

    print("\n" + "=" * 80)
    print("🏆 回測結果排名 (按收益率)")
    print("=" * 80)
    print(df_results[["strategy_name", "return_pct", "trades", "max_drawdown", "realized_pnl", "unrealized_pnl"]].head(10).to_string())

    if best_result:
        print("\n" + "=" * 80)
        print("✅ 最優策略")
        print("=" * 80)
        print(f"策略名稱: {best_result['strategy_name']}")
        print(f"收益率: {best_result['return_pct']*100:.2f}%")
        print(f"最終淨值: ${best_result['final_equity']:.2f}")
        print(f"已實現盈虧: ${best_result['realized_pnl']:.2f}")
        print(f"未實現盈虧: ${best_result['unrealized_pnl']:.2f}")
        print(f"交易次數: {best_result['trades']}")
        print(f"最大回撤: {best_result['max_drawdown']*100:.2f}%")
        print(f"\n最佳參數:")
        print(f"  多頭止盈間距: {best_result['long_up']*100:.2f}%")
        print(f"  多頭補倉間距: {best_result['long_down']*100:.2f}%")
        print(f"  空頭補倉間距: {best_result['short_up']*100:.2f}%")
        print(f"  空頭止盈間距: {best_result['short_down']*100:.2f}%")

    return df_results, best_result


if __name__ == "__main__":
    results, best = grid_search_backtest()
