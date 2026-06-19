import requests

url = "https://cognitive-rag-engine.onrender.com/api/v1/documents"
headers = {
    "Origin": "https://cognitive-rag-engine-1.onrender.com"
}

print("Testing GET without following redirects...")
res = requests.get(url, headers=headers, allow_redirects=False)
print("Status:", res.status_code)
print("Headers:", res.headers)
