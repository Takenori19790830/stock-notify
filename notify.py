import os
import requests

url = os.getenv("WEBHOOK_URL")

def notify(msg):
    requests.post(url, json={"content": msg})

notify("GitHub Actions からのテスト通知だよ、トトス")
