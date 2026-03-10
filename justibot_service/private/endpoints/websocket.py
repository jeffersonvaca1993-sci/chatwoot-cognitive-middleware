from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Request, HTTPException
import json
from typing import Dict, List
import asyncio

from ..database import obtener_usuario_por_token, obtener_usuario_por_email, obtener_usuario_por_credencial
import traceback

router = APIRouter(prefix="/api/ws", tags=["WebSocket"])

# --- CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Mapea user_id (int) -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"WS: Usuario {user_id} conectado.")

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"WS: Usuario {user_id} desconectado.")

    async def send_personal_message(self, message: dict, user_id: int):
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(message)
                print(f"WS: Mensaje enviado a usuario {user_id}", flush=True)
            except Exception as e:
                print(f"WS: Error enviando a usuario {user_id}: {e}", flush=True)
                self.disconnect(user_id)
        else:
            print(f"WS: Usuario {user_id} no conectado. Mensaje ignorado.", flush=True)
            print(f"WS DEBUG: Active Conections Registry: {list(self.active_connections.keys())}", flush=True)

manager = ConnectionManager()

# --- WEBSOCKET ENDPOINT (Cliente -> Servidor) ---
@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    Mantiene la conexión abierta con el cliente para recibir notificaciones en tiempo real.
    """
    if not token:
        print("WS DEBUG: Rejected connection (No token)")
        await websocket.close(code=4003)
        return

    usuario = await obtener_usuario_por_token(token)
    if not usuario:
        print("WS DEBUG: Rejected connection (Invalid token)")
        await websocket.close(code=4003)
        return

    # Convertir a dict por si acaso (fix record)
    if not isinstance(usuario, dict):
        usuario = dict(usuario)

    user_id = usuario["id_cliente"]
    print(f"WS DEBUG: Accepting connection for User ID {user_id}")
    
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # Mantener vivo el socket. El cliente puede mandar "ping"
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        print(f"WS DEBUG: Client {user_id} disconnected")
        manager.disconnect(user_id)
    except Exception as e:
        print(f"WS DEBUG: Error with client {user_id}: {e}")
        manager.disconnect(user_id)

# --- WEBHOOK ENDPOINT (Chatwoot -> Servidor) ---
@router.post("/webhook")
async def chatwoot_webhook(request: Request):
    """
    Recibe eventos de Chatwoot y los reenvía al usuario correspondiente via WebSocket.
    """
    try:
        payload = await request.json()
        print(f"WEBHOOK DEBUG: Payload received")
        
        # --- CAPTURE TO FILE ---
        with open("test.txt", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        print("WEBHOOK DEBUG: Payload saved to captured_webhook.json")
        # -----------------------

    except Exception as e:
        print(f"WEBHOOK ERROR: Invalid JSON - {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        event_type = payload.get("event")
        print(f"WEBHOOK DEBUG: Event '{event_type}'")

        if event_type == "message_created":
            await procesar_nuevo_mensaje(payload)
        else:
            print(f"WEBHOOK DEBUG: Ignoring event {event_type}")

    except Exception as e:
        print(f"WEBHOOK CRITICAL ERROR: {e}")
        traceback.print_exc()
        # Return 200 to avoid retries from Chatwoot if it's a code bug
        return {"status": "error", "message": str(e)}
    
    return {"status": "ok"}

async def procesar_nuevo_mensaje(payload: dict):
    """
    Extrae info del mensaje y lo envía al usuario si es saliente (del agente).
    """
    data = payload.get("data", {})
    message_type = data.get("message_type")
    content = data.get("content")
    
    print(f"WEBHOOK MSG DEBUG: Type={message_type}, Content={content[:20]}...")

    # message_type: 0 (incoming/user), 1 (outgoing/agent)
    if message_type == "outgoing" or message_type == 1:
        
        # Buscar contacto
        contact_payload = data.get("contact", {}) # Puede estar dentro de data directo?
        
        # A veces en 'message_created', 'data' tiene 'conversation', 'sender', etc.
        # Chatwoot payload structure varies.
        # Fallback: check conversation -> contact_inbox
        
        contact_email = None
        contact_identifier = None
        
        if contact_payload:
            contact_email = contact_payload.get("email")
            contact_identifier = contact_payload.get("identifier")
        
        # Si no esta en data.contact, buscar en conversation.meta.sender? No, eso es el sender.
        
        print(f"WEBHOOK LOOKUP: Email={contact_email}, Identifier={contact_identifier}")
        
        target_user = None
        if contact_email:
            target_user = await obtener_usuario_por_email(contact_email)
            print(f"WEBHOOK LOOKUP: By Email -> {'Found' if target_user else 'Not Found'}")
        
        if not target_user and contact_identifier:
            target_user = await obtener_usuario_por_credencial(contact_identifier)
            print(f"WEBHOOK LOOKUP: By Credential -> {'Found' if target_user else 'Not Found'}")

        if target_user:
            if not isinstance(target_user, dict):
                target_user = dict(target_user)
                
            uid = target_user["id_cliente"]
            print(f"WEBHOOK: Target User found: {uid}. Sending WS message...")
            
            simple_msg = {
                "type": "new_message",
                "content": content,
                "sender": "agent"
            }
            
            await manager.send_personal_message(simple_msg, uid)
        else:
            print(f"WEBHOOK ERROR: Could not find user for this message.")
    else:
        print("WEBHOOK DEBUG: Ignoring incoming message (not outgoing)")
