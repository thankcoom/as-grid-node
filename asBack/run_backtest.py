#!/usr/bin/env python3
"""
網格交易回測系統 - 主程式入口
==============================

使用方式:
    # 單次回測
    python3 run_backtest.py --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25

    # 參數優化
    python3 run_backtest.py --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25 --optimize

    # 下載數據
    python3 run_backtest.py --download --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

# 確保可以導入 backtest_system
sys.path.insert(0, str(Path(__file__).parent))

from backtest_system import Config, DataLoader, GridBacktester, GridOptimizer


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(
        description="網格交易回測系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 基本回測
  python3 run_backtest.py --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25

  # 使用自定義參數
  python3 run_backtest.py --symbol BTCUSDT --start 2025-01-01 --end 2025-01-31 \\
      --take-profit 0.003 --grid-spacing 0.005 --leverage 15

  # 參數優化
  python3 run_backtest.py --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25 --optimize

  # 下載數據
  python3 run_backtest.py --download --symbol XRPUSDC --start 2025-10-27 --end 2025-11-25
        """
    )

    # 基本參數
    parser.add_argument("--symbol", "-s", type=str, default="XRPUSDC",
                        help="交易對符號 (預設: XRPUSDC)")
    parser.add_argument("--start", type=str, required=True,
                        help="開始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True,
                        help="結束日期 (YYYY-MM-DD)")

    # 策略參數
    parser.add_argument("--take-profit", "-tp", type=float, default=0.004,
                        help="止盈間距 (預設: 0.004 = 0.4%%)")
    parser.add_argument("--grid-spacing", "-gs", type=float, default=0.006,
                        help="補倉間距 (預設: 0.006 = 0.6%%)")
    parser.add_argument("--leverage", "-l", type=int, default=20,
                        help="槓桿倍數 (預設: 20)")
    parser.add_argument("--initial-balance", "-b", type=float, default=1000,
                        help="初始資金 (預設: 1000)")
    parser.add_argument("--order-value", "-o", type=float, default=10,
                        help="每單金額 (預設: 10)")
    parser.add_argument("--direction", "-d", type=str, default="both",
                        choices=["long", "short", "both"],
                        help="交易方向 (預設: both)")

    # 運行模式
    parser.add_argument("--optimize", action="store_true",
                        help="執行參數優化")
    parser.add_argument("--download", action="store_true",
                        help="下載歷史數據")
    parser.add_argument("--compare-directions", action="store_true",
                        help="比較不同方向策略")

    # 輸出選項
    parser.add_argument("--output", type=str,
                        help="輸出結果到 CSV 文件")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="詳細輸出")

    return parser.parse_args()


def download_data(args):
    """下載數據"""
    loader = DataLoader()
    success = loader.download(
        symbol=args.symbol,
        start_date=args.start,
        end_date=args.end
    )
    return success


def run_single_backtest(args):
    """執行單次回測"""
    print("="*60)
    print("🚀 網格交易回測系統")
    print("="*60)

    # 建立配置
    config = Config(
        symbol=args.symbol,
        initial_balance=args.initial_balance,
        order_value=args.order_value,
        leverage=args.leverage,
        take_profit_spacing=args.take_profit,
        grid_spacing=args.grid_spacing,
        direction=args.direction
    )

    print(f"\n📊 配置:")
    print(config)

    # 載入數據
    loader = DataLoader()
    try:
        df = loader.load(args.symbol, args.start, args.end)
    except ValueError as e:
        print(f"\n❌ 錯誤: {e}")
        print(f"💡 提示: 使用 --download 先下載數據")
        return None

    # 執行回測
    print(f"\n⏳ 執行回測...")
    bt = GridBacktester(df, config)
    result = bt.run()

    # 輸出結果
    print(f"\n{result}")

    # 保存結果
    if args.output:
        trade_df = bt.get_trade_df()
        trade_df.to_csv(args.output, index=False)
        print(f"\n📁 交易記錄已保存至: {args.output}")

    return result


def run_optimization(args):
    """執行參數優化"""
    print("="*60)
    print("🔍 網格參數優化")
    print("="*60)

    # 載入數據
    loader = DataLoader()
    try:
        df = loader.load(args.symbol, args.start, args.end)
    except ValueError as e:
        print(f"\n❌ 錯誤: {e}")
        return None

    # 建立基礎配置
    base_config = Config(
        symbol=args.symbol,
        initial_balance=args.initial_balance,
        order_value=args.order_value,
        leverage=args.leverage,
        direction=args.direction
    )

    # 執行優化
    optimizer = GridOptimizer(df, base_config)

    print("\n📈 非對稱間距搜尋:")
    print("-"*40)
    asymmetric_results = optimizer.run_asymmetric_search()

    print("\n📊 對稱間距搜尋:")
    print("-"*40)
    symmetric_results = optimizer.run_symmetric_search()

    # 輸出最佳結果
    print("\n" + "="*60)
    print("🏆 最佳結果 (非對稱)")
    print("="*60)
    best = asymmetric_results.iloc[0]
    print(f"止盈間距: {best['tp_pct']}")
    print(f"補倉間距: {best['gs_pct']}")
    print(f"收益率: {best['return_pct']*100:.2f}%")
    print(f"最大回撤: {best['max_drawdown']*100:.2f}%")
    print(f"交易次數: {best['trades']}")
    print(f"勝率: {best['win_rate']*100:.1f}%")

    # 保存結果
    if args.output:
        asymmetric_results.to_csv(args.output, index=False)
        print(f"\n📁 優化結果已保存至: {args.output}")

    return asymmetric_results


def compare_directions(args):
    """比較不同方向策略"""
    print("="*60)
    print("🔄 方向策略比較")
    print("="*60)

    # 載入數據
    loader = DataLoader()
    try:
        df = loader.load(args.symbol, args.start, args.end)
    except ValueError as e:
        print(f"\n❌ 錯誤: {e}")
        return None

    # 建立基礎配置
    base_config = Config(
        symbol=args.symbol,
        initial_balance=args.initial_balance,
        order_value=args.order_value,
        leverage=args.leverage,
        take_profit_spacing=args.take_profit,
        grid_spacing=args.grid_spacing
    )

    # 比較方向
    optimizer = GridOptimizer(df, base_config)
    results = optimizer.compare_directions()

    print("\n" + "="*60)
    print("📊 比較結果")
    print("="*60)
    print(results.to_string(index=False))

    return results


def main():
    """主函數"""
    args = parse_args()

    if args.download:
        # 下載數據模式
        download_data(args)
    elif args.optimize:
        # 參數優化模式
        run_optimization(args)
    elif args.compare_directions:
        # 方向比較模式
        compare_directions(args)
    else:
        # 單次回測模式
        run_single_backtest(args)


if __name__ == "__main__":
    main()
