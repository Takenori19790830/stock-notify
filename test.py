import os
import requests

url = os.getenv("WEBHOOK_URL")
msg = "【テスト通知】JST 14:10 に自動実行されました。"
requests.post(url, json={"content": msg})
