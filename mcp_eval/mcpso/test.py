import requests

proxies = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

try:
    r = requests.get("https://duckduckgo.com", proxies=proxies, timeout=10)
    print("Status:", r.status_code)
except Exception as e:
    print("Error:", e)