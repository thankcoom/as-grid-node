from binance_historical_data import BinanceDataDumper
from datetime import date

def fetch_xrp_data():
    # 初始化 dumper - 下載 XRP/USDC 合約數據
    dumper = BinanceDataDumper(
        path_dir_where_to_dump="./data",   # 数据保存路径
        asset_class="um",                  # um = USDT-M Futures 合约
        data_type="klines",                # K线
        data_frequency="1m"                # 1 分钟级别
    )

    # 下載最近 30 天的數據用於回測
    dumper.dump_data(
        tickers=["XRPUSDC"],  # XRP/USDC 合約
        date_start=date(2025, 10, 26),
        date_end=date(2025, 11, 25)
    )

    print("✅ XRP/USDC 数据下载完成！文件在 ./data 目录下")

if __name__ == "__main__":
    fetch_xrp_data()
