import urllib.request
import json

data = json.dumps({
    "email": "tushar@example.com",
    "username": "Tushar",
    "password": "SecurePass123!"
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/register',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    response = urllib.request.urlopen(req)
    print("User created successfully!")
except Exception as e:
    print(f"Error: {e}")
