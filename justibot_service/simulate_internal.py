
import asyncio
import httpx
import json

# URL interna (localhost porque se corre dentro del contenedor)
URL = "http://justibot:8001/api/ws/webhook"

async def simulate():
    # Payload de ejemplo simplificado de Chatwoot
    payload = {
        "event": "message_created",
        "data": {
            "content": "Hola desde simulacion interna Docker",
            "message_type": "outgoing",
            "conversation": {"id": 123},
            "contact": {"email": "test@example.com", "identifier": "user123"}
        }
    }
    
    print(f"Enviando webhook a {URL}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(URL, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error conectando: {e}")

if __name__ == "__main__":
    asyncio.run(simulate())
