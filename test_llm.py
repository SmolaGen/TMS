import urllib.request
import json
import os

api_key = os.getenv("VIBEPROXY_API_KEY", "sk-vibeproxy-placeholder")
url = "http://127.0.0.1:8317/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "gemini-2.5-flash",
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ]
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(url, data=data, headers=headers)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode())
