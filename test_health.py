import requests
import time

url = "https://cognitive-rag-engine.onrender.com/api/v1/health"

for _ in range(15):
    try:
        res = requests.get(url, timeout=10)
        print(f"Status: {res.status_code}")
        print(res.json())
        if res.json()["data"]["database"].startswith("unreachable:"):
            break
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(5)
