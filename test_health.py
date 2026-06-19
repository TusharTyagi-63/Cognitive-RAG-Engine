import requests
import time

url = "https://cognitive-rag-engine.onrender.com/api/v1/health"

for _ in range(5):
    try:
        start = time.time()
        res = requests.get(url, timeout=10)
        print(f"[{time.time() - start:.2f}s] {res.status_code} {res.text}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)
