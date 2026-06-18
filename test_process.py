import requests
import json
import uuid

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "Password123!"

# 1. Register & Login
requests.post(f"{BASE_URL}/auth/register", json={"email": EMAIL, "username": "testuser", "password": PASSWORD})
res = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Upload Document
with open("test.txt", "w") as f:
    f.write("This is a test document for processing.")

with open("test.txt", "rb") as f:
    res = requests.post(f"{BASE_URL}/documents/upload", headers=headers, files={"file": ("test.txt", f, "text/plain")})

print("Upload:", res.status_code, res.text)
if res.status_code == 200:
    doc_id = res.json()["data"]["id"]
    print("Document ID:", doc_id)
    
    # 3. Process Document
    res = requests.post(f"{BASE_URL}/documents/{doc_id}/process", headers=headers)
    print("Process:", res.status_code, res.text)
