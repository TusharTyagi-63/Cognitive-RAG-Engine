import requests
import json
import uuid

BASE_URL = "https://cognitive-rag-engine.onrender.com/api/v1"
EMAIL = f"test_{uuid.uuid4()}@example.com"
PASSWORD = "Password123!"

# 1. Register
print("Registering...")
res = requests.post(f"{BASE_URL}/auth/register", json={
    "email": EMAIL,
    "username": "testuser",
    "password": PASSWORD
})
print("Register:", res.status_code, res.text)

# 2. Login
print("Logging in...")
res = requests.post(f"{BASE_URL}/auth/login", data={
    "username": EMAIL,
    "password": PASSWORD
})
print("Login:", res.status_code, res.text)
if res.status_code != 200:
    exit(1)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 3. Create Session
print("Creating session...")
res = requests.post(f"{BASE_URL}/chat/sessions", json={"title": "Test"}, headers=headers)
print("Create Session:", res.status_code, res.text)
session_id = res.json()["data"]["id"]

# 4. Stream Message
print(f"Streaming message to session {session_id}...")
with requests.post(f"{BASE_URL}/chat/sessions/{session_id}/stream", json={"content": "hello"}, headers=headers, stream=True) as r:
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
