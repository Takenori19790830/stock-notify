import os
import requests

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

# Yahoo Finance から価格取得
def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    data = requests.get(url).json()
    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]

# ============================
# 前場の終値保存（08:00）
# ============================
def check_morning():
    nikkei = get_price("^N225")
    topix = get_price("^TOPX")
    send(f"【08:00 地合いチェック】\n日経:{nikkei}\nTOPIX:{topix}")

# ============================
# 後場寄り付き判定（12:30）
# ============================
def get_sector_strength():
    sectors = {
        "電機": "9984.T",
        "自動車": "7203.T",
        "金融": "8306.T",
    }
    score = 0
    for name, code in sectors.items():
        price = get_price(code)
        score += 1 if price > 0 else -1
    return score

def get_top3_strength():
    top3 = ["9984.T", "8035.T", "6861.T"]
    score = 0
    for code in top3:
        price = get_price(code)
        score += 1 if price > 0 else -1
    return score

def check_noon():
    nikkei = get_price("^N225")
    sector_score = get_sector_strength()
    top3_score = get_top3_strength()

    total = (sector_score * 0.2) + (top3_score * 0.3)

    if total > 0.3:
        decision = "ブル優勢"
    elif total < -0.3:
        decision = "ベア優勢"
        decision = "見送り"

    send(
        f"【12:30 後場寄り付き判定】\n"
        f"日経:{nikkei}\n"
        f"主要セクター強弱:{sector_score}\n"
        f"影響度TOP3:{top3_score}\n"
        f"総合スコア:{total:.2f}\n"
        f"判定:{decision}"
    )

# ============================
# GitHub Actions から呼ばれる入口
# ============================
if __name__ == "__main__":
    mode = os.getenv("MODE")

    if mode == "morning":
        check_morning()
    elif mode == "noon":
        check_noon()
    else:
        send("MODE が指定されていません")
