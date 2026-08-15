import yfinance as yf
import requests

WEBHOOK_URL = "YOUR_WEBHOOK_URL"  # ← あなたのURLを入れてね

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
        df = yf.Ticker(t).history(period="60d")
        close = df["Close"].iloc[-1]

        ma5 = df["Close"].rolling(5).mean().iloc[-1]
        ma15 = df["Close"].rolling(15).mean().iloc[-1]
        ma25 = df["Close"].rolling(25).mean().iloc[-1]

        data[name] = {
            "close": close,
            "ma5": ma5,
            "ma15": ma15,
            "ma25": ma25,
            "kairi5": (close - ma5) / ma5 * 100,
            "kairi15": (close - ma15) / ma15 * 100
        }
    return data

# ============================
# 短期スコアリング（勢い）
# ============================

def score_short(d):
    bull = 0
    bear = 0
    reason = []

    nikkei = d["nikkei"]

    # MA5 の向き（最重要）
    if nikkei["close"] > nikkei["ma5"]:
        bull += 3
        reason.append("MA5上向き")
    else:
        bear += 3
        reason.append("MA5下向き")

    # 現在値 vs MA5
    if nikkei["close"] > nikkei["ma5"]:
        bull += 2
        reason.append("現在値がMA5より上")
    else:
        bear += 2
        reason.append("現在値がMA5より下")

    # 乖離率
    if nikkei["kairi5"] > 2:
        bear += 1
        reason.append("短期過熱（ベア寄り）")
    if nikkei["kairi5"] < -2:
        bull += 1
        reason.append("短期売られすぎ（ブル寄り）")

    # 為替
    if d["usd_jpy"]["close"] > 150:
        bull += 1
        reason.append("円安 → ブル")
    else:
        bear += 1
        reason.append("円高 → ベア")

    # SPY
    if d["spy"]["close"] > d["spy"]["ma5"]:
        bull += 1
        reason.append("SPY上昇 → ブル")
    else:
        bear += 1
        reason.append("SPY下落 → ベア")

    # VIX
    if d["vix"]["close"] > 20:
        bear += 1
        reason.append("VIX高い → ベア")
    else:
        bull += 1
        reason.append("VIX低い → ブル")

    direction = "ブル" if bull > bear else "ベア"
    return direction, reason

# ============================
# スイングスコアリング（流れ）
# ============================

def score_swing(d):
    bull = 0
    bear = 0
    reason = []

    nikkei = d["nikkei"]

    # MA15 vs MA25（最重要）
    if nikkei["ma15"] > nikkei["ma25"]:
        bull += 4
        reason.append("MA15 > MA25（上昇トレンド）")
    else:
        bear += 4
        reason.append("MA15 < MA25（下降トレンド）")

    # 現在値 vs MA15
    if nikkei["close"] > nikkei["ma15"]:
        bull += 2
        reason.append("現在値がMA15より上（押し目）")
    else:
        bear += 2
        reason.append("現在値がMA15より下（戻り）")

    # セクター別
    if d["bank"]["close"] > d["bank"]["ma5"]:
        bull += 2
        reason.append("金融強い → ブル")
    else:
        bear += 2
        reason.append("金融弱い → ベア")

    if d["telecom"]["close"] > d["telecom"]["ma5"]:
        bull += 2
        reason.append("通信強い → ブル")
    else:
        bear += 2
        reason.append("通信弱い → ベア")

    # EWJ（海外勢）
    if d["ewj"]["close"] > d["ewj"]["ma5"]:
        bull += 1
        reason.append("海外勢買い → ブル")
    else:
        bear += 1
        reason.append("海外勢売り → ベア")

    # 地合い（為替・SPY・VIX）
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
    return direction, reason

# ============================
# 通知フォーマット（コンパクト版）
# ============================

def build_message(d, short_dir, short_reason, swing_dir, swing_reason):
    nikkei = d["nikkei"]

    msg = f"""
【12:00 市場判定】

■短期（1〜2日）
方向性：{short_dir}
理由：{", ".join(short_reason[:4])}

■スイング（3〜5日）
方向性：{swing_dir}
理由：{", ".join(swing_reason[:4])}

━━━━━━━━━━━━━━
■主要指標（要点）
日経：{nikkei["close"]:.2f}
MA5：{nikkei["ma5"]:.2f}（{nikkei["kairi5"]:+.2f}%）
MA15：{nikkei["ma15"]:.2f}（{nikkei["kairi15"]:+.2f}%）
MA25：{nikkei["ma25"]:.2f}

為替：{d["usd_jpy"]["close"]:.2f}
SPY：{d["spy"]["close"]:.2f}
VIX：{d["vix"]["close"]:.2f}

セクター：
金融：{d["bank"]["close"]:.2f}
通信：{d["telecom"]["close"]:.2f}
電気：{d["electric"]["close"]:.2f}
EWJ：{d["ewj"]["close"]:.2f}
━━━━━━━━━━━━━━

■総合判定
短期：{short_dir}
スイング：{swing_dir}
"""

    return msg

# ============================
# 通知送信
# ============================

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

# ============================
# 実行
# ============================

if __name__ == "__main__":
    d = fetch_data()

    short_dir, short_reason = score_short(d)
    swing_dir, swing_reason = score_swing(d)

    msg = build_message(d, short_dir, short_reason, swing_dir, swing_reason)
    send(msg)
