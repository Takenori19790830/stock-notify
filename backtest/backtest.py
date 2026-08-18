import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ============================
# 取得対象
# ============================

TICKERS = {
    "nikkei": "1321.T",
    "topix": "1306.T",
    "usd_jpy": "JPY=X",
    "spy": "SPY",
    "vix": "^VIX",
    "bank": "1615.T",
    "telecom": "1620.T",
    "electric": "1625.T",
    "auto": "1622.T",
    "trading": "1629.T",
    "machine": "1624.T",
    "ewj": "EWJ"
}

# ============================
# 3年分のデータ取得
# ============================

def fetch_3years():
    end = datetime.today()
    start = end - timedelta(days=365*3)

    frames = []

    for name, ticker in TICKERS.items():
        df = yf.Ticker(ticker).history(start=start, end=end)

        df = df[["Close"]].rename(columns={"Close": f"{name}_close"})
        df[f"{name}_pct"] = df[f"{name}_close"].pct_change() * 100
        df[f"{name}_ma5"] = df[f"{name}_close"].rolling(5).mean()
        df[f"{name}_ma15"] = df[f"{name}_close"].rolling(15).mean()
        df[f"{name}_ma25"] = df[f"{name}_close"].rolling(25).mean()
        df[f"{name}_kairi5"] = (df[f"{name}_close"] - df[f"{name}_ma5"]) / df[f"{name}_ma5"] * 100
        df[f"{name}_kairi15"] = (df[f"{name}_close"] - df[f"{name}_ma15"]) / df[f"{name}_ma15"] * 100

        frames.append(df)

    # ============================
    # 日付で結合
    # ============================

    base = frames[0]
    for f in frames[1:]:
        base = base.join(f, how="outer")

    base = base.dropna()

    return base

# ============================
# CSV 出力
# ============================

def save_csv(df):
    df.to_csv("backtest/data/3years.csv", index=True)
    print("CSV 出力完了：backtest/data/3years.csv")

# ============================
# 実行
# ============================

if __name__ == "__main__":
    df = fetch_3years()
    save_csv(df)
