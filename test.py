import os
import requests
from datetime import datetime, timezone, timedelta

url = os.getenv("WEBHOOK_URL")

# JST（UTC+9）
jst = timezone(timedelta(hours=9))
now = datetime.now(jst).strftime("%Y-%m-%d %H:%M")

msg = f"【テスト通知】JST {now} に自動実行されました。"

requests.post(url, json={"content": msg})
