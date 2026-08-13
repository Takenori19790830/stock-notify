import os
import csv
from datetime import datetime
import requests

# 価格取得（notify.py と同じ）
def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        data = requests.get(url).json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None

# CSV の保存先
CSV_PATH = "data/results.csv"

# 今日の判定（notify.py が出した MODE を読む）
def read_signal():
    # GitHub Actions の環境変数 MODE を読む
    return os.getenv("MODE_SIGNAL", "neutral")

# 仮想売買モデル（最小構成）
def simple_model(signal):
    """
    signal: bull / bear / neutral
    戻り値: (entry_price, exit_price, pnl)
    """

    # 日経平均を使う（指数連動ブルベアの代替）
    price = get_price("^N225")
    if price is None:
        return (None, None, None)

    # entry（仮想）
    entry = price

    # exit（仮想）→ 1%動いたと仮定（最小構成）
    if signal == "bull":
        exit = entry * 1.01
    elif signal == "bear":
        exit = entry * 0.99
    else:
        exit = entry

    pnl = exit - entry
    return (entry, exit, pnl)

# CSV に追記
def append_csv(date, model, signal, entry, exit, pnl):
    header = ["date", "model", "signal", "entry_price", "exit_price", "pnl"]

    # ファイルがなければヘッダーを書く
    try:
        with open(CSV_PATH, "x", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
    except FileExistsError:
        pass

    # 追記
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([date, model, signal, entry, exit, pnl])

# メイン処理
if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")

    signal = read_signal()  # notify.py が出した判定
    entry, exit, pnl = simple_model(signal)

    append_csv(today, "model1", signal, entry, exit, pnl)
