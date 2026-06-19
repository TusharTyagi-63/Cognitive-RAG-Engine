import requests

url = "https://cognitive-rag-engine.onrender.com/api/v1/chat/sessions"
headers = {
    "Origin": "https://cognitive-rag-engine-1.onrender.com",
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "authorization, content-type"
}

res = requests.options(url, headers=headers)
print("OPTIONS Response Code:", res.status_code)
print("OPTIONS Headers:", res.headers)

res_get = requests.get(url, headers={"Origin": "https://cognitive-rag-engine-1.onrender.com"})
print("GET Response Code:", res_get.status_code)
print("GET Headers:", res_get.headers)
