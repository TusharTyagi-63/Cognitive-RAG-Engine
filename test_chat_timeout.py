import requests
import json
import uuid

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "Password123!"

try:
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "username": "testuser",
        "password": PASSWORD
    }, timeout=5)
    
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    }, timeout=5)
    token = res.json()["access_token"]
    
    res = requests.post(f"{BASE_URL}/chat/sessions", json={"title": "Test"}, headers={"Authorization": f"Bearer {token}"}, timeout=5)
    session_id = res.json()["data"]["id"]
    
    print(f"Streaming message to session {session_id}...")
    with requests.post(f"{BASE_URL}/chat/sessions/{session_id}/stream", json={"content": "hello"}, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=10) as r:
        print("Status code:", r.status_code)
        for line in r.iter_lines():
            if line:
                print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
