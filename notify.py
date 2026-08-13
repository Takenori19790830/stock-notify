import os
import requests

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

# ============================
# Yahoo Finance 価格取得（例外処理付き）
# ============================
def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        data = requests.get(url).json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None


# ============================
# 寄り付き判定（08:00）
# ============================
def check_opening():
    nikkei_fut = get_price("^NKX")     # 日経先物（安定版）
    topix_fut  = get_price("^TPX")     # TOPIX先物（安定版）
    usd_jpy    = get_price("JPY=X")

    if nikkei_fut is None or topix_fut is None or usd_jpy is None:
        send("【08:00 寄り付き判定】データ取得失敗のため見送り")
        return

    base = 0

    if nikkei_fut > 0 and topix_fut > 0:
        base += 1
    else:
        base -= 1

    if usd_jpy > 150:
        base += 0.3
    else:
        base -= 0.3

    decision = "ブル" if base > 0 else "ベア"

    send(
        f"【08:00 寄り付き判定（強化版）】\n"
        f"日経先物:{nikkei_fut}\n"
        f"TOPIX先物:{topix_fut}\n"
        f"USDJPY:{usd_jpy}\n"
        f"判定:{decision}"
    )


# ============================
# セクター強弱
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
        score += 1 if price and price > 0 else -1
    return score


# ============================
# 寄与度TOP3
# ============================
def get_top3_strength():
    top3 = ["9984.T", "8035.T", "6861.T"]
    score = 0
    for code in top3:
        price = get_price(code)
        score += 1 if price and price > 0 else -1
    return score


# ============================
# 後場寄り付き判定（12:30）
# ============================
def check_noon():
    morning_nikkei = float(os.getenv("MORNING_N225", "0"))
    morning_topix  = float(os.getenv("MORNING_TOPIX", "0"))

    noon_nikkei = get_price("^N225")
    noon_topix  = get_price("^TOPX")

    if noon_nikkei is None or noon_topix is None:
        send("【12:30 後場判定】データ取得失敗のため見送り")
        return

    nikkei_change = (noon_nikkei - morning_nikkei) / morning_nikkei if morning_nikkei else 0
    topix_change  = (noon_topix  - morning_topix)  / morning_topix  if morning_topix else 0

    base = 0
    if nikkei_change > 0.003 and topix_change > 0.003:
        base += 1
    elif nikkei_change < -0.003 and topix_change < -0.003:
        base -= 1

    sector_score = get_sector_strength()
    top3_score = get_top3_strength()

    growth = get_price("1305.T")
    value  = get_price("1306.T")
    style_score = 1 if growth and value and growth > value else -1

    large = get_price("1343.T")
    small = get_price("1312.T")
    size_score = 1 if large and small and large > small else -1

    total = (
        base +
        sector_score * 
