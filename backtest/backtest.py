import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import os

# ============================
# 取得対象（notify.py と完全一致）
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

# 外国指標（前日終値しか使えない）
FOREIGN = ["spy", "vix", "ewj"]

# ============================
# 3年分のデータ取得
# ============================

def fetch_3years():
    end = datetime.today()
    start = end - timedelta(days=365*3)

    frames = []

    for name, ticker in TICKERS.items():
        df = yf.Ticker(ticker).history(start=start, end=end)

        if df.empty:
            print(f"⚠ {name} ({ticker}) のデータが取得できませんでした")
            continue

        df = df[["Close"]].rename(columns={"Close": f"{name}_close"})
        df[f"{name}_pct"] = df[f"{name}_close"].pct_change(fill_method=None) * 100
        df[f"{name}_ma5"] = df[f"{name}_close"].rolling(5).mean()
        df[f"{name}_ma15"] = df[f"{name}_close"].rolling(15).mean()
        df[f"{name}_ma25"] = df[f"{name}_close"].rolling(25).mean()
        df[f"{name}_kairi5"] = (df[f"{name}_close"] - df[f"{name}_ma5"]) / df[f"{name
