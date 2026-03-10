import requests
import json
import time

URL = "https://justibot.sci-vacasantana.org/api/ws/webhook"
PAYLOAD = {
    "event": "message_created",
    "test_simulation": True,
    "data": {
        "content": "Simulacion Externa",
        "message_type": "outgoing",
        "contact": {
            "email": "jeffersonvaca1993@hotmail.com",
            "identifier": "manual_test"
        }
    }
}

try:
    print(f"📡 Sending mock webhook to {URL}...")
    start = time.time()
    resp = requests.post(URL, json=PAYLOAD, timeout=10)
    duration = time.time() - start
    
    print(f"✅ Status Code: {resp.status_code}")
    print(f"⏱️ Duration: {duration:.2f}s")
    print(f"📄 Response: {resp.text}")

except Exception as e:
    print(f"❌ Error: {e}")
