import requests

# This script simulates the exact preflight and GET request sent by the browser
url = "https://cognitive-rag-engine.onrender.com/api/v1/documents"

try:
    print("Testing GET /documents...")
    res = requests.get(url, headers={
        "Origin": "https://cognitive-rag-engine-1.onrender.com",
        "Accept": "*/*"
    }, timeout=10)
    print("Status:", res.status_code)
    print("Headers:", res.headers)
except Exception as e:
    print(f"Error: {e}")
