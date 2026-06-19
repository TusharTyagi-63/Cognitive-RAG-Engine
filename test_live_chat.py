import requests
import json
import uuid

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "Password123!"

try:
    print("Registering...")
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "username": "testuser",
        "password": PASSWORD
    }, timeout=10)
    print("Register:", res.status_code)
    
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": EMAIL,
        "password": PASSWORD
    }, timeout=10)
    print("Login:", res.status_code)
    token = res.json()["access_token"]
    
    print("Creating Chat Session...")
    res = requests.post(f"{BASE_URL}/chat/sessions", json={"title": "Test"}, headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print("Session:", res.status_code)
    session_id = res.json()["data"]["id"]
    
    print(f"Streaming message to session {session_id}...")
    with requests.post(f"{BASE_URL}/chat/sessions/{session_id}/stream", json={"content": "hello"}, headers={"Authorization": f"Bearer {token}"}, stream=True, timeout=10) as r:
        print("Stream Status:", r.status_code)
        for line in r.iter_lines():
            if line:
                print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
