import ccxt
import pandas as pd
from datetime import datetime, timedelta
import os
import time

def fetch_xrp_data():
    """使用 ccxt 下載 XRP/USDC 1分鐘 K線數據"""

    # 初始化 Binance
    exchange = ccxt.binance({
        'options': {'defaultType': 'future'}
    })

    symbol = 'XRP/USDC:USDC'
    timeframe = '1m'

    # 創建數據目錄
    data_dir = './data/futures/um/daily/klines/XRPUSDC/1m'
    os.makedirs(data_dir, exist_ok=True)

    # 下載最近 30 天數據
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    print(f"開始下載 {symbol} 數據...")
    print(f"時間範圍: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")

    current_date = start_date
    while current_date < end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        file_path = f"{data_dir}/XRPUSDC-1m-{date_str}.csv"

        # 如果文件已存在則跳過
        if os.path.exists(file_path):
            print(f"跳過 {date_str} (已存在)")
            current_date += timedelta(days=1)
            continue

        # 計算時間戳
        since = int(current_date.timestamp() * 1000)
        end_of_day = int((current_date + timedelta(days=1)).timestamp() * 1000)

        all_ohlcv = []

        while since < end_of_day:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                if not ohlcv:
                    break

                # 只保留當天的數據
                day_data = [x for x in ohlcv if x[0] < end_of_day]
                all_ohlcv.extend(day_data)

                if len(ohlcv) < 1000:
                    break

                since = ohlcv[-1][0] + 60000  # 下一分鐘
                time.sleep(0.1)  # 避免請求過快

            except Exception as e:
                print(f"下載 {date_str} 時出錯: {e}")
                break

        if all_ohlcv:
            # 轉換為 DataFrame
            df = pd.DataFrame(all_ohlcv, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume'
            ])
            df.to_csv(file_path, index=False)
            print(f"✅ 已保存 {date_str} ({len(df)} 條記錄)")
        else:
            print(f"⚠️ {date_str} 無數據")

        current_date += timedelta(days=1)
        time.sleep(0.5)  # 避免請求過快

    print("\n✅ 數據下載完成！")

if __name__ == "__main__":
    fetch_xrp_data()
