from fastapi import APIRouter, Request, HTTPException, Header
from private.database import database
# from private.endpoints.websocket import manager
import hmac
import hashlib
import os

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

# Consulta auxiliar para buscar usuario por conversation_id
QUERY_USER_BY_CONV_ID = """
    SELECT id_cliente 
    FROM clientes_activos 
    WHERE chatwoot_conversation_id = :conv_id
"""

def validar_firma(raw_body: bytes, signature: str):
    secret = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    if not secret:
        # Si no hay secreto configurado, permitimos todo (modo desarrollo inseguro)
        # O bloqueamos. Por seguridad, mejor loguear advertencia.
        print("ADVERTENCIA: CHATWOOT_WEBHOOK_SECRET no configurado. Saltando validación.")
        return True
        
    computed_sha = hmac.new(
        key=secret.encode(),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_sha, signature)

@router.post("/chatwoot")
async def chatwoot_webhook(
    request: Request,
    x_chatwoot_signature: str = Header(None)
):
    """
    Recibe eventos de Chatwoot y notifica al usuario vía WebSocket.
    """
    print("DEBUG: Recibida petición en /api/webhooks/chatwoot", flush=True)
    try:
        raw_body = await request.body()
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="JSON inválido")
        
    # Validación de Seguridad
    if x_chatwoot_signature:
        if not validar_firma(raw_body, x_chatwoot_signature):
            print(f"Firma inválida. Recibida: {x_chatwoot_signature}")
            raise HTTPException(status_code=401, detail="Firma inválida")
    else:
        # Si Chatwoot envía firma y nosotros no la recibimos, es sospechoso.
        # Pero si no está configurado en Chatwoot, no la enviará.
        # Verificamos si tenemos secreto local.
        if os.getenv("CHATWOOT_WEBHOOK_SECRET"):
            print("Falta firma X-Chatwoot-Signature")
            raise HTTPException(status_code=401, detail="Firma requerida")
        
    evento = payload.get("event")
    
    # Solo nos interesan mensajes creados
    if evento not in ["message_created"]:
        return {"status": "ignorado"}
        
    data = payload.get("data", {})
    mensaje = data.get("content")
    tipo_mensaje = data.get("message_type") # incoming, outgoing
    conversation_id = data.get("conversation", {}).get("id")
    
    print(f"DEBUG Webhook: Evento={evento}, Tipo={tipo_mensaje}, ConvID={conversation_id}")

    
    # Solo notificar mensajes SALIENTES (del agente al usuario)
    # Chatwoot webhooks: "outgoing" o 1
    if tipo_mensaje not in ["outgoing", 1]:
        return {"status": f"ignorado_no_outgoing_tipo_{tipo_mensaje}"}
        
    if not conversation_id:
        return {"status": "sin_conversation_id"}
        
    # Buscar a qué usuario pertenece esta conversación
    usuario = await database.fetch_one(query=QUERY_USER_BY_CONV_ID, values={"conv_id": conversation_id})
    
    if not usuario:
        print(f"Webhook recibido para conversación {conversation_id} pero no encontrada en DB local.")
        return {"status": "usuario_no_encontrado"}
        
    id_usuario = usuario["id_cliente"]
    
    # Construir payload para el cliente
    # Asegurar coincidencia con lo que espera el frontend (index.html)
    mensaje_cliente = {
        "tipo": "nuevo_mensaje",
        "datos": { # Frontend espera "datos", no "data"
            "id": data.get("id"),
            "contenido": mensaje,
            "tipo": data.get("content_type", "text"),
            "creado_en": data.get("created_at"),
            "es_mio": False, # Es del agente
            "estado": "sent"
        }
    }
    
    # Enviar por WebSocket
    # await manager.enviar_mensaje_personal(mensaje_cliente, id_usuario)
    print(f"DEBUG: Webhook procesado. Mensaje saliente ignorado (usando Proxy WebSocket).")
    
    return {"status": "procesado"}
