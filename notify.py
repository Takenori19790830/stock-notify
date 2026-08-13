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

# ============================
# 寄り付き判定（08:00）
# ============================
def check_opening():
    # 取得
    nikkei_fut = get_price("^NKX")
    topix_fut  = get_price("^TPX")
    usd_jpy    = get_price("JPY=X")

    # 取得結果一覧
    status = []
    status.append(f"日経先物：{'取得成功（' + str(nikkei_fut) + ')' if nikkei_fut else '取得失敗'}")
    status.append(f"TOPIX先物：{'取得成功（' + str(topix_fut) + ')' if topix_fut else '取得失敗'}")
    status.append(f"USDJPY：{'取得成功（' + str(usd_jpy) + ')' if usd_jpy else '取得失敗'}")

    # 判定ロジック（柔軟）
    score = 0
    weight_total = 0

    # 先物（重み 0.6）
    if nikkei_fut is not None and topix_fut is not None:
        weight_total += 0.6
        score += 0.6 if (nikkei_fut > 0 and topix_fut > 0) else -0.6

    # 為替（重み 0.4）
    if usd_jpy is not None:
        weight_total += 0.4
        score += 0.4 if usd_jpy > 150 else -0.4

    # 判定
    if weight_total == 0:
        decision = "判定不能（全データ取得失敗）"
    else:
        if score > 0:
            decision = "ブル寄り"
        elif score < 0:
            decision = "ベア寄り"
        else:
            decision = "中立"

    # 通知
    send(
        "【08:00 寄り付き判定（柔軟版）】\n"
        + "\n".join(status) + "\n"
        + f"総合判定：{decision}"
    )
