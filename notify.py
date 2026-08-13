import os
import requests

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

# -----------------------------
# 共通：価格取得（例外処理付き）
# -----------------------------
def get_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    try:
        data = requests.get(url).json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None

# -----------------------------
# 共通：取得結果を整形する
# -----------------------------
def status_line(label, value):
    if value is None:
        return f"{label}：取得失敗"
    else:
        return f"{label}：取得成功（{value}）"

# -----------------------------
# 寄り付き判定（08:00）
# -----------------------------
def check_opening():
    nikkei_fut = get_price("^NKX")
    topix_fut  = get_price("^TPX")
    usd_jpy    = get_price("JPY=X")

    status = [
        status_line("日経先物", nikkei_fut),
        status_line("TOPIX先物", topix_fut),
        status_line("USDJPY", usd_jpy)
    ]

    score = 0
    weight = 0

    # 先物（重み 0.6）
    if nikkei_fut is not None and topix_fut is not None:
        weight += 0.6
        score += 0.6 if (nikkei_fut > 0 and topix_fut > 0) else -0.6

    # 為替（重み 0.4）
    if usd_jpy is not None:
        weight += 0.4
        score += 0.4 if usd_jpy > 150 else -0.4

    if weight == 0:
        decision = "判定不能（全データ取得失敗）"
    else:
        decision = "ブル寄り" if score > 0 else "ベア寄り"

    send(
        "【08:00 寄り付き判定】\n"
        + "\n".join(status) + "\n"
        + f"総合判定：{decision}"
    )

# -----------------------------
# 後場判定（12:30）
# -----------------------------
def check_noon():
    morning_nikkei = float(os.getenv("MORNING_N225", "0"))
    morning_topix  = float(os.getenv("MORNING_TOPIX", "0"))

    noon_nikkei = get_price("^N225")
    noon_topix  = get_price("^TOPX")

    sector = {
        "電機": get_price("9984.T"),
        "自動車": get_price("7203.T"),
        "金融": get_price("8306.T")
    }

    top3 = {
        "ソフトバンクG": get_price("9984.T"),
        "東エレ": get_price("8035.T"),
        "キーエンス": get_price("6861.T")
    }

    growth = get_price("1305.T")
    value  = get_price("1306.T")
    large  = get_price("1343.T")
    small  = get_price("1312.T")

    status = [
        status_line("日経（後場）", noon_nikkei),
        status_line("TOPIX（後場）", noon_topix),
        status_line("グロースETF", growth),
        status_line("バリューETF", value),
        status_line("大型株ETF", large),
        status_line("小型株ETF", small)
    ] + [
        status_line(f"セクター：{k}", v) for k, v in sector.items()
    ] + [
        status_line(f"寄与度：{k}", v) for k, v in top3.items()
    ]

    score = 0
    weight = 0

    # 前場→後場の変化（重み 0.3）
    if noon_nikkei and morning_nikkei:
        weight += 0.3
        score += 0.3 if noon_nikkei > morning_nikkei else -0.3

    if noon_topix and morning_topix:
        weight += 0.3
        score += 0.3 if noon_topix > morning_topix else -0.3

    # セクター（重み 0.2）
    valid_sector = [v for v in sector.values() if v is not None]
    if valid_sector:
        weight += 0.2
        score += 0.2 if sum(valid_sector) > 0 else -0.2

    # 寄与度（重み 0.2）
    valid_top3 = [v for v in top3.values() if v is not None]
    if valid_top3:
        weight += 0.2
        score += 0.2 if sum(valid_top3) > 0 else -0.2

    # スタイル（重み 0.1）
    if growth and value:
        weight += 0.1
        score += 0.1 if growth > value else -0.1

    # 大型/小型（重み 0.1）
    if large and small:
        weight += 0.1
        score += 0.1 if large > small else -0.1

    if weight == 0:
        decision = "判定不能（全データ取得失敗）"
    else:
        decision = "ブル優勢" if score > 0 else "ベア優勢"

    send(
        "【12:30 後場判定】\n"
        + "\n".join(status) + "\n"
        + f"総合判定：{decision}"
    )

# -----------------------------
# 引け判定（15:00）
# -----------------------------
def check_close():
    nikkei = get_price("^N225")
    topix  = get_price("^TOPX")
    vix    = get_price("^VIX")

    top3 = {
        "ソフトバンクG": get_price("9984.T"),
        "東エレ": get_price("8035.T"),
        "キーエンス": get_price("6861.T")
    }

    sector = {
        "電機": get_price("9984.T"),
        "自動車": get_price("7203.T"),
        "金融": get_price("8306.T")
    }

    status = [
        status_line("日経", nikkei),
        status_line("TOPIX", topix),
        status_line("VIX", vix)
    ] + [
        status_line(f"寄与度：{k}", v) for k, v in top3.items()
    ] + [
        status_line(f"セクター：{k}", v) for k, v in sector.items()
    ]

    score = 0
    weight = 0

    if nikkei:
        weight += 0.3
        score += 0.3 if nikkei > 0 else -0.3

    if topix:
        weight += 0.3
        score += 0.3 if topix > 0 else -0.3

    valid_top3 = [v for v in top3.values() if v is not None]
    if valid_top3:
        weight += 0.2
        score += 0.2 if sum(valid_top3) > 0 else -0.2

    valid_sector = [v for v in sector.values() if v is not None]
    if valid_sector:
        weight += 0.2
        score += 0.2 if sum(valid_sector) > 0 else -0.2

    if vix:
        weight += 0.2
        score += -0.2 if vix > 20 else 0.2

    if weight == 0:
        decision = "判定不能（全データ取得失敗）"
    else:
        decision = "ブル引け" if score > 0 else "ベア引け"

    send(
        "【15:00 引け判定】\n"
        + "\n".join(status) + "\n"
        + f"総合判定：{decision}"
    )

# -----------------------------
# GitHub Actions 入口
# -----------------------------
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
