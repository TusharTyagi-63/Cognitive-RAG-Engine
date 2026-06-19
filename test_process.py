import requests
import uuid

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "Password123!"

try:
    print("Registering...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "username": f"user_{uuid.uuid4().hex[:8]}",
        "password": PASSWORD
    }, timeout=10)
    print("Register:", res.status_code)
    if res.status_code != 200:
        with open("register_error.txt", "w", encoding="utf-8") as f:
            f.write(res.content.decode('utf-8'))
        print("Register Error written to register_error.txt")
    
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    }, timeout=10)
    token = res.json()["access_token"]
    
    print("Uploading dummy document...")
    files = {'file': ('dummy.txt', b'Hello world, this is a test document to process.')}
    res = requests.post(f"{BASE_URL}/documents/upload", headers={"Authorization": f"Bearer {token}"}, files=files, timeout=10)
    print("Upload Status:", res.status_code)
    doc_id = res.json()["data"]["id"]
    
    print(f"Processing document {doc_id}...")
    res = requests.post(f"{BASE_URL}/documents/{doc_id}/process", headers={"Authorization": f"Bearer {token}"})
    print("Process Status:", res.status_code)
    print("Process Body:", res.text)
except Exception as e:
    print(f"Error: {e}")
