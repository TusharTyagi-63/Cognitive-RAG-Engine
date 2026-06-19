import requests

url = "https://cognitive-rag-engine.onrender.com/api/v1/auth/login"

try:
    print("Testing GET /auth/login...")
    res_get = requests.get(url, headers={"Origin": "https://cognitive-rag-engine-1.onrender.com"})
    print("GET Status:", res_get.status_code)
    
    print("Testing POST /auth/login...")
    res_post = requests.post(url, headers={"Origin": "https://cognitive-rag-engine-1.onrender.com"}, data={"username": "a", "password": "b"})
    print("POST Status:", res_post.status_code)
    print("POST Headers:", res_post.headers)
    print("POST Body:", res_post.text)
except Exception as e:
    print(f"Error: {e}")
