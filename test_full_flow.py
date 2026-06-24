import requests
import uuid
import time

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "Password123!"

def test_flow():
    print("1. Registering...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "username": f"user_{uuid.uuid4().hex[:5]}",
        "password": PASSWORD
    }, timeout=30)
    print("Register:", res.status_code)
    
    print("2. Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    }, timeout=10)
    token = res.json().get("access_token")
    if not token:
        print("Login failed!", res.text)
        return
        
    print("3. Uploading document...")
    files = {"file": ("test.txt", b"This is a test document about Paris being the capital of France.", "text/plain")}
    res = requests.post(f"{BASE_URL}/documents/upload", headers={"Authorization": f"Bearer {token}"}, files=files, timeout=10)
    print("Upload Status:", res.status_code)
    doc_id = res.json()["data"]["id"]
    
    print("4. Processing document...")
    res = requests.post(f"{BASE_URL}/documents/{doc_id}/process", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print("Process Status:", res.status_code)
    
    print("5. Waiting for background task to finish...")
    time.sleep(5)
    
    print("6. Opening Document (GET /content)...")
    content_res = requests.get(
        f"{BASE_URL}/documents/{doc_id}/content", 
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print("Content Response:", content_res.status_code)
    if content_res.status_code != 200:
        print("Content Error:", content_res.text)

    print("7. Deleting Document (DELETE)...")
    delete_res = requests.delete(
        f"{BASE_URL}/documents/{doc_id}", 
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )
    print("Delete Response:", delete_res.status_code)
    if delete_res.status_code != 200:
        print("Delete Error:", delete_res.text)

if __name__ == "__main__":
    test_flow()
