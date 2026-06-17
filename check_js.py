import urllib.request
import re

url = "https://cognitive-rag-engine-1.onrender.com/assets/index-oNQnCVVl.js"
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    js_code = response.read().decode('utf-8')

# Search for the definition of 'qo'
matches = re.findall(r'[^;]*qo[^;]*', js_code)
# Let's be more specific, find where qo is assigned
assignments = re.findall(r'(?:let|var|const)\s+qo\s*=[^;]*;', js_code)
print(f"qo assignment: {assignments}")
