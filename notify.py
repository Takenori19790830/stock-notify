import yfinance as yf
import requests
import os
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ============================
# データ取得
# ============================

TICKERS = {
    "nikkei": "1321.T",
    "usd_jpy": "JPY=X",
    "spy": "SPY",
    "vix": "^VIX",
    "bank": "1615.T",
    "telecom": "1620.T",
    "electric": "1625.T",
    "ewj": "EWJ"
}

def fetch_data():
    data = {}
    for name, t in TICKERS.items():
        df = yf.Ticker(t).history(period="5d")

        # 終値
        close = df["Close"].iloc[-1]
        prev_close = df["Close"].iloc[-2]

        # 前日比（％）
        pct_change = (close - prev_close) / prev_close * 100

        # 移動平均
        ma5 = df["Close"].rolling(5).mean().iloc[-1]
        ma15 = df["Close"].rolling(15).mean().iloc[-1]
        ma25 = df["Close"].rolling(25).mean().iloc[-1]

        # 最終更新日時（日本時間）
        last_ts = df.index[-1].tz_convert("Asia/Tokyo")

        data[name] = {
            "close": close,
            "prev_close": prev_close,
            "pct_change": pct_change,
            "ma5": ma5,
            "ma15": ma15,
            "ma25": ma25,
            "kairi5": (close - ma5) / ma5 * 100,
            "kairi15": (close - ma15) / ma15 * 100,
            "timestamp": last_ts
        }
    return data

# ============================
# 色分け（＋青、−赤）
# ============================

def color_pct(pct):
    if pct > 0:
        return f"🔵 +{pct:.2f}%"
    elif pct < 0:
        return f"🔴 {pct:.2f}%"
    else:
        return f"{pct:.2f}%"



# ============================
# 短期スコアリング（勢い）
# ============================

def score_short(d):
    bull = 0
    bear = 0
    reason = []

    nikkei = d["nikkei"]

    if nikkei["close"] > nikkei["ma5"]:
        bull += 3
        reason.append("MA5上向き")
    else:
        bear += 3
        reason.append("MA5下向き")

    if nikkei["close"] > nikkei["ma5"]:
        bull += 2
        reason.append("現在値がMA5より上")
    else:
        bear += 2
        reason.append("現在値がMA5より下")

    if nikkei["kairi5"] > 2:
        bear += 1
        reason.append("短期過熱（ベア寄り）")
    if nikkei["kairi5"] < -2:
        bull += 1
        reason.append("短期売られすぎ（ブル寄り）")

    if d["usd_jpy"]["close"] > 150:
        bull += 1
        reason.append("円安 → ブル")
    else:
        bear += 1
        reason.append("円高 → ベア")

    if d["spy"]["close"] > d["spy"]["ma5"]:
        bull += 1
        reason.append("SPY上昇 → ブル")
    else:
        bear += 1
        reason.append("SPY下落 → ベア")

    if d["vix"]["close"] > 20:
        bear += 1
        reason.append("VIX高い → ベア")
    else:
        bull += 1
        reason.append("VIX低い → ブル")

    direction = "ブル" if bull > bear else "ベア"
    return direction, reason, bull, bear


# ============================
# スイングスコアリング（流れ）
# ============================

def score_swing(d):
    bull = 0
    bear = 0
    reason = []

    nikkei = d["nikkei"]

    if nikkei["ma15"] > nikkei["ma25"]:
        bull += 4
        reason.append("MA15 > MA25（上昇トレンド）")
    else:
        bear += 4
        reason.append("MA15 < MA25（下降トレンド）")

    if nikkei["close"] > nikkei["ma15"]:
        bull += 2
        reason.append("現在値がMA15より上（押し目）")
    else:
        bear += 2
        reason.append("現在値がMA15より下（戻り）")

    for sector in ["bank", "telecom", "electric"]:
        if d[sector]["close"] > d[sector]["ma5"]:
            bull += 2
            reason.append(f"{sector}強い → ブル")
        else:
            bear += 2
            reason.append(f"{sector}弱い → ベア")

    if d["ewj"]["close"] > d["ewj"]["ma5"]:
        bull += 1
        reason.append("海外勢買い → ブル")
    else:
        bear += 1
        reason.append("海外勢売り → ベア")

    if d["usd_jpy"]["close"] > 150:
        bull += 1
    else:
        bear += 1

    if d["spy"]["close"] > d["spy"]["ma5"]:
        bull += 1
    else:
        bear += 1

    if d["vix"]["close"] > 20:
        bear += 1
    else:
        bull += 1

    direction = "ブル" if bull > bear else "ベア"
    return direction, reason, bull, bear



# ============================
# 通知フォーマット（コンパクト版）
# ============================

def build_embed(d, short_dir, short_reason, short_bull, short_bear,
                swing_dir, swing_reason, swing_bull, swing_bear):

    nikkei = d["nikkei"]
    ts = nikkei["timestamp"].strftime("%Y-%m-%d %H:%M")

    # 色分け
    color = 3447003 if swing_dir == "ブル" else 15158332

    embed = {
        "embeds": [
            {
                "title": "市場AI通知",
                "description": f"{ts}（日本時間）",
                "color": color,
                "fields": [
                    {
                        "name": "短期（1〜2日）",
                        "value": f"方向性：{short_dir}（ブル点 {short_bull} / ベア点 {short_bear}）\n理由：{', '.join(short_reason[:4])}"
                    },
                    {
                        "name": "スイング（3〜5日）",
                        "value": f"方向性：{swing_dir}（ブル点 {swing_bull} / ベア点 {swing_bear}）\n理由：{', '.join(swing_reason[:4])}"
                    },
                    {
                        "name": "主要指標",
                        "value": (
                            f"日経：{nikkei['close']:.2f}（{color_pct(nikkei['pct_change'])}）\n"
                            f"為替：{d['usd_jpy']['close']:.2f}（{color_pct(d['usd_jpy']['pct_change'])}）\n"
                            f"SPY：{d['spy']['close']:.2f}（{color_pct(d['spy']['pct_change'])}）\n"
                            f"VIX：{d['vix']['close']:.2f}（{color_pct(d['vix']['pct_change'])}）\n"
                            f"EWJ：{d['ewj']['close']:.2f}（{color_pct(d['ewj']['pct_change'])}）"
                        )
                    },
                    {
                        "name": "セクター",
                        "value": (
                            f"金融：{d['bank']['close']:.2f}（{color_pct(d['bank']['pct_change'])}）\n"
                            f"通信：{d['telecom']['close']:.2f}（{color_pct(d['telecom']['pct_change'])}）\n"
                            f"電気：{d['electric']['close']:.2f}（{color_pct(d['electric']['pct_change'])}）"
                        )
                    }
                ]
            }
        ]
    }

    return embed


# ============================
# 通知送信
# ============================
def send(payload):
    requests.post(WEBHOOK_URL, json=payload)

#def send(msg):
#    requests.post(WEBHOOK_URL, json={"content": msg})  装飾前

# ============================
# 実行
# ============================

if __name__ == "__main__":
    d = fetch_data()

    short_dir, short_reason, short_bull, short_bear = score_short(d)
    swing_dir, swing_reason, swing_bull, swing_bear = score_swing(d)

    payload = build_embed(
        d,
        short_dir, short_reason, short_bull, short_bear,
        swing_dir, swing_reason, swing_bull, swing_bear
    )

    send(payload)
