import requests

url = "https://cognitive-rag-engine.onrender.com/api/v1/documents/123"

# This endpoint doesn't exist, it should return 404, or if I pass something that causes 500...
# Let's hit the endpoint to see if 404 has CORS headers
res = requests.options(url, headers={
    "Origin": "https://cognitive-rag-engine-1.onrender.com",
    "Access-Control-Request-Method": "GET"
})
print("OPTIONS 404 headers:", res.headers)

res = requests.get(url, headers={
    "Origin": "https://cognitive-rag-engine-1.onrender.com"
})
print("GET 404 headers:", res.headers)
