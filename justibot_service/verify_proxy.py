import asyncio
import httpx
import websockets
import json
import sys

# URL base de Justibot (interno en docker)
BASE_URL = "http://justibot:8001/api"
# URL WS de Justibot (interno en docker)
WS_URL_BASE = "ws://justibot:8001/api/ws/chat"

async def verify_proxy():
    print("🚀 Iniciando prueba de Proxy WebSocket...")

    async with httpx.AsyncClient() as client:
        # 1. Login Invitado
        print("\n1. Solicitando sesión de invitado...")
        resp = await client.post(f"{BASE_URL}/auth/guest")
        if resp.status_code != 200:
            print(f"❌ Error login invitado: {resp.text}")
            return
        
        data = resp.json()
        token = data.get("token")
        pubsub_token = data.get("pubsub_token")
        print(f"   ✅ Token Sesión: {token[:10]}...")
        print(f"   ✅ PubSub Token: {pubsub_token}")

        if not pubsub_token:
            print("❌ Error: No se recibió pubsub_token")
            return

        # 2. Conectar WS Proxy
        ws_url = f"{WS_URL_BASE}?token={token}"
        print(f"\n2. Conectando a WS Proxy: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as ws:
                print("   ✅ Conectado al Proxy.")
                
                # Suscribirse (Protocolo Chatwoot)
                sub_payload = {
                    "command": "subscribe",
                    "identifier": json.dumps({
                        "channel": "RoomChannel",
                        "pubsub_token": pubsub_token
                    })
                }
                await ws.send(json.dumps(sub_payload))
                print("   ✅ Suscripción enviada a través del Proxy.")

                # Esperar confirmación
                print("\n3. Esperando respuesta de Chatwoot...")
                resp_ws = await ws.recv()
                print(f"   📩 WS Recibido: {resp_ws}")
                
                # Verificar si es confirmación
                data_ws = json.loads(resp_ws)
                if data_ws.get("type") == "confirm_subscription":
                    print("   ✅✅ ÉXITO: Proxy funciona y Chatwoot confirmó suscripción!")
                elif data_ws.get("type") == "welcome":
                    print("   ℹ️ Recibido Welcome, esperando confirmación...")
                    resp_ws_2 = await ws.recv()
                    print(f"   📩 WS Recibido 2: {resp_ws_2}")
                    data_ws_2 = json.loads(resp_ws_2)
                    if data_ws_2.get("type") == "confirm_subscription":
                         print("   ✅✅ ÉXITO: Proxy funciona y Chatwoot confirmó suscripción!")
                
        except Exception as e:
            print(f"❌ Error WS Proxy: {e}")

if __name__ == "__main__":
    asyncio.run(verify_proxy())
