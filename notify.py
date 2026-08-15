import yfinance as yf
import requests
import os

WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ============================
# データ取得
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
    "ewj": "EWJ"
}

def fetch_data():
    data = {}
    for name, t in TICKERS.items():
        df = yf.Ticker(t).history(period="5d")

        # 終値と前日終値
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

    # TOPIX
    if d["topix"]["pct_change"] > 0:
    bull += 1
    reason.append("TOPIX前日比プラス → 全体強い")
    else:
    bear += 1
    reason.append("TOPIX前日比マイナス → 全体弱い")

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

    # ★ 前日比（勢い）をスコアに反映
    if nikkei["pct_change"] > 0:
        bull += 2
        reason.append("日経前日比プラス → 勢いブル")
    elif nikkei["pct_change"] < 0:
        bear += 2
        reason.append("日経前日比マイナス → 勢いベア")

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

     # TOPIX
    if d["topix"]["ma15"] > d["topix"]["ma25"]:
        bull += 1
        reason.append("TOPIX上昇トレンド（全体補強）")
    else:
        bear += 1
        reason.append("TOPIX下降トレンド（全体弱化）")
    
    # セクター別
    for sector_key, sector_label in [("bank", "金融"), ("telecom", "通信"), ("electric", "電気")]:
        if d[sector_key]["close"] > d[sector_key]["ma5"]:
            bull += 2
            reason.append(f"{sector_label}強い → ブル")
        else:
            bear += 2
            reason.append(f"{sector_label}弱い → ベア")
    
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

    # ★ 前日比（流れ補強）をスコアに反映
    if nikkei["pct_change"] > 0:
        bull += 1
        reason.append("日経前日比プラス（流れ補強）")
    elif nikkei["pct_change"] < 0:
        bear += 1
        reason.append("日経前日比マイナス（流れ弱化）")

    direction = "ブル" if bull > bear else "ベア"
    return direction, reason, bull, bear

# ============================
# Embed 生成（Discord用）
# ============================

def build_embed(d, short_dir, short_reason, short_bull, short_bear,
                swing_dir, swing_reason, swing_bull, swing_bear):

    nikkei = d["nikkei"]
    ts = nikkei["timestamp"].strftime("%Y-%m-%d %H:%M")

    # カードの色：スイング方向で決める
    color = 3447003 if swing_dir == "ブル" else 15158332  # 青 / 赤

    embed = {
        "embeds": [
            {
                "title": "市場AI通知",
                "description": f"{ts}（日本時間）",
                "color": color,
                "fields": [
                    {
                        "name": "短期（1〜2日）",
                        "value": (
                            f"方向性：{short_dir}（ブル点 {short_bull} / ベア点 {short_bear}）\n"
                            f"理由：{', '.join(short_reason[:4])}"
                        )
                    },
                    {
                        "name": "スイング（3〜5日）",
                        "value": (
                            f"方向性：{swing_dir}（ブル点 {swing_bull} / ベア点 {swing_bear}）\n"
                            f"理由：{', '.join(swing_reason[:4])}"
                        )
                    },
                    {
                        "name": "主要指標（前日比付き）",
                        "value": (
                            f"日経：{nikkei['close']:.2f}（{color_pct(nikkei['pct_change'])}）\n"
                            f"為替：{d['usd_jpy']['close']:.2f}（{color_pct(d['usd_jpy']['pct_change'])}）\n"
                            f"SPY：{d['spy']['close']:.2f}（{color_pct(d['spy']['pct_change'])}）\n"
                            f"VIX：{d['vix']['close']:.2f}（{color_pct(d['vix']['pct_change'])}）\n"
                            f"EWJ：{d['ewj']['close']:.2f}（{color_pct(d['ewj']['pct_change'])}）"
                        )
                    },
                    {
                        "name": "セクター（前日比付き）",
                        "value": (
                            f"金融：{d['bank']['close']:.2f}（{color_pct(d['bank']['pct_change'])}）\n"
                            f"通信：{d['telecom']['close']:.2f}（{color_pct(d['telecom']['pct_change'])}）\n"
                            f"電気：{d['electric']['close']:.2f}（{color_pct(d['electric']['pct_change'])}）"
                        )
                    },
                    {
                        "name": "総合判定",
                        "value": (
                            f"短期：{short_dir}（ブル点 {short_bull} / ベア点 {short_bear}）\n"
                            f"スイング：{swing_dir}（ブル点 {swing_bull} / ベア点 {swing_bear}）"
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
