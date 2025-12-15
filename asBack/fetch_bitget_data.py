"""
Bitget 歷史數據下載器
使用 ccxt 從 Bitget 交易所下載 K 線數據用於回測

使用方法:
    python fetch_bitget_data.py                    # 下載所有支援的交易對
    python fetch_bitget_data.py BTCUSDT ETHUSDT   # 下載指定交易對
    python fetch_bitget_data.py --days 60         # 下載最近 60 天數據
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import argparse
import sys

# 預設支援的交易對
DEFAULT_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "SOLUSDT",
    "DOGEUSDT",
    "BNBUSDT",
    "ADAUSDT",
]


def get_data_dir() -> Path:
    """取得數據目錄"""
    # 從腳本位置往上找到 asBack
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data" / "futures" / "um" / "daily" / "klines"
    return data_dir


def download_symbol_data(
    exchange: ccxt.bitget,
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    interval: str = "1m",
    data_dir: Path = None
) -> int:
    """
    下載單個交易對的數據

    Args:
        exchange: ccxt 交易所實例
        symbol: 交易對符號 (如 BTCUSDT)
        start_date: 開始日期
        end_date: 結束日期
        interval: K 線間隔
        data_dir: 數據目錄

    Returns:
        下載的 K 線數量
    """
    if data_dir is None:
        data_dir = get_data_dir()

    # Bitget 使用的格式
    ccxt_symbol = f"{symbol[:-4]}/{symbol[-4:]}"  # BTCUSDT -> BTC/USDT

    print(f"\n📥 下載 {symbol} 數據...")
    print(f"   時間範圍: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

    current = start_date
    total_bars = 0
    skipped_days = 0

    # 建立符號目錄
    symbol_dir = data_dir / symbol / interval
    symbol_dir.mkdir(parents=True, exist_ok=True)

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        output_path = symbol_dir / f"{symbol}-{interval}-{date_str}.csv"

        # 如果文件已存在且不是今天，跳過
        if output_path.exists() and current.date() < datetime.now().date():
            skipped_days += 1
            current += timedelta(days=1)
            continue

        # 計算時間戳
        since = int(datetime(current.year, current.month, current.day).timestamp() * 1000)
        until = since + 24 * 60 * 60 * 1000  # 24小時

        try:
            # 從 Bitget 獲取數據
            all_ohlcv = []
            fetch_since = since

            # 可能需要多次請求才能獲取完整一天的數據（1440 根 1 分鐘 K 線）
            while fetch_since < until:
                ohlcv = exchange.fetch_ohlcv(
                    ccxt_symbol,
                    interval,
                    since=fetch_since,
                    limit=1000  # Bitget 限制
                )

                if not ohlcv:
                    break

                # 只保留當天數據
                day_ohlcv = [bar for bar in ohlcv if since <= bar[0] < until]
                all_ohlcv.extend(day_ohlcv)

                # 下一批的起始時間
                if ohlcv:
                    fetch_since = ohlcv[-1][0] + 60000  # +1 分鐘
                else:
                    break

                # 如果已經獲取到當天結束，停止
                if ohlcv[-1][0] >= until:
                    break

                # 避免 rate limit
                time.sleep(0.1)

            if all_ohlcv:
                # 去重並排序
                seen = set()
                unique_ohlcv = []
                for bar in all_ohlcv:
                    if bar[0] not in seen:
                        seen.add(bar[0])
                        unique_ohlcv.append(bar)
                unique_ohlcv.sort(key=lambda x: x[0])

                df = pd.DataFrame(unique_ohlcv, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume'
                ])
                df.to_csv(output_path, index=False)
                total_bars += len(df)
                print(f"   ✅ {date_str}: {len(df)} 條")
            else:
                print(f"   ⚠️ {date_str}: 無數據")

        except ccxt.NetworkError as e:
            print(f"   ❌ {date_str}: 網絡錯誤 - {e}")
            time.sleep(1)
        except ccxt.ExchangeError as e:
            print(f"   ❌ {date_str}: 交易所錯誤 - {e}")
        except Exception as e:
            print(f"   ❌ {date_str}: {e}")

        current += timedelta(days=1)
        time.sleep(0.2)  # 避免 rate limit

    if skipped_days > 0:
        print(f"   ℹ️ 跳過 {skipped_days} 天（已存在）")

    return total_bars


def main():
    parser = argparse.ArgumentParser(description="下載 Bitget 歷史 K 線數據")
    parser.add_argument(
        "symbols",
        nargs="*",
        default=DEFAULT_SYMBOLS,
        help="要下載的交易對列表（預設：全部）"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="下載最近幾天的數據（預設：30）"
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1m",
        choices=["1m", "5m", "15m", "1h", "4h", "1d"],
        help="K 線間隔（預設：1m）"
    )
    parser.add_argument(
        "--start",
        type=str,
        help="開始日期 (YYYY-MM-DD)，覆蓋 --days"
    )
    parser.add_argument(
        "--end",
        type=str,
        help="結束日期 (YYYY-MM-DD)，預設：今天"
    )

    args = parser.parse_args()

    # 計算日期範圍
    if args.end:
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    else:
        end_date = datetime.now()

    if args.start:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=args.days)

    # 初始化 Bitget 交易所
    print("🔗 連接 Bitget 交易所...")
    exchange = ccxt.bitget({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'swap',  # 永續合約
        }
    })

    # 載入市場資訊
    try:
        exchange.load_markets()
        print("✅ 已連接 Bitget")
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        sys.exit(1)

    # 下載數據
    print(f"\n📊 下載設定:")
    print(f"   交易對: {', '.join(args.symbols)}")
    print(f"   時間範圍: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    print(f"   K 線間隔: {args.interval}")

    data_dir = get_data_dir()
    print(f"   數據目錄: {data_dir}")

    total_all = 0
    for symbol in args.symbols:
        try:
            count = download_symbol_data(
                exchange=exchange,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=args.interval,
                data_dir=data_dir
            )
            total_all += count
        except Exception as e:
            print(f"❌ {symbol} 下載失敗: {e}")

    print(f"\n✅ 下載完成！共 {total_all:,} 條 K 線數據")
    print(f"   數據已保存至: {data_dir}")


if __name__ == "__main__":
    main()
