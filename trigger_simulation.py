import asyncio
import httpx
import json

BASE_URL = "https://justibot.sci-vacasantana.org"

async def trigger():
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Login
        resp = await client.post(f"{BASE_URL}/api/auth/guest")
        if resp.status_code != 200:
            print("Login failed")
            return
        token = resp.json()["token"]
        
        # 2. Convert to Google/User (Opcional, pero guest basta)
        
        # 3. Send Message
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"content": "Simulacion para Captura JSON", "tipo": "text"}
        resp_msg = await client.post(f"{BASE_URL}/api/messages", json=payload, headers=headers)
        
        if resp_msg.status_code == 200:
            print("Message sent. Waiting for webhook...")
            await asyncio.sleep(5)
        else:
            print(f"Message failed: {resp_msg.text}")

if __name__ == "__main__":
    asyncio.run(trigger())
