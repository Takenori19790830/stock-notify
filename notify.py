import os
import requests

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        data = requests.get(url).json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None

def check_opening():
    nikkei_fut = get_price("^NKX")
    topix_fut  = get_price("^TPX")
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

def get_top3_strength():
    top3 = ["9984.T", "8035.T", "6861.T"]
    score = 0
    for code in top3:
        price = get_price(code)
        score += 1 if price and price > 0 else -1
    return score

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
        sector_score * 0.2 +
        top3_score * 0.3 +
        style_score * 0.2 +
        size_score * 0.2
    )

    if total > 0.5:
        decision = "ブル優勢"
    elif total < -0.5:
        decision = "ベア優勢"
    else:
        decision = "見送り"

    send(
        f"【12:30 後場寄り付き判定（強化版）】\n"
        f"日経:{noon_nikkei}（前場比 {nikkei_change*100:.2f}%）\n"
        f"TOPIX:{noon_topix}（前場比 {topix_change*100:.2f}%）\n"
        f"主要セクター強弱:{sector_score}\n"
        f"寄与度TOP3:{top3_score}\n"
        f"グロース/バリュー:{style_score}\n"
        f"大型/小型:{size_score}\n"
        f"総合スコア:{total:.2f}\n"
        f"判定:{decision}"
    )

def check_close():
    nikkei = get_price("^N225")
    topix  = get_price("^TOPX")
    vix    = get_price("^VIX")

    if nikkei is None or topix is None or vix is None:
        send("【15:00 引け判定】データ取得失敗のため見送り")
        return

    top3_score = get_top3_strength()
    sector_score = get_sector_strength()

    risk = -1 if vix > 20 else 1

    total = (
        top3_score * 0.3 +
        sector_score * 0.2 +
        risk * 0.3
    )

    decision = "ブル" if total > 0 else "ベア"

    send(
        f"【15:00 引け判定（強化版）】\n"
        f"日経:{nikkei}\n"
        f"TOPIX:{topix}\n"
        f"VIX:{vix}\n"
        f"寄与度TOP3:{top3_score}\n"
        f"セクター強弱:{sector_score}\n"
        f"総合:{total:.2f}\n"
        f"判定:{decision}"
    )

if __name__ == "__main__":
    mode = os.getenv("MODE")

    if mode == "opening":
        check_opening()
    elif mode == "noon":
        check_noon()
    elif mode == "close":
        check_close()
    else:
        send("MODE が指定されていません")
