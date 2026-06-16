import urllib.request
import urllib.parse
import json

data = urllib.parse.urlencode({
    "username": "Tushar",
    "password": "SecurePass123!"
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8000/api/v1/auth/login',
    data=data,
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)

try:
    response = urllib.request.urlopen(req)
    print("Login successful:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print(f"Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
