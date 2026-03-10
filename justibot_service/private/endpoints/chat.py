from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
from typing import List, Optional

from private.config_loader import settings
from private.deps import obtener_usuario_actual
from private.endpoints.auth import obtener_headers_chatwoot, sincronizar_contacto_chatwoot
from private.database import actualizar_cache_chatwoot

router = APIRouter(prefix="/api/messages", tags=["Chat"])

class MensajeInput(BaseModel):
    content: str
    tipo: str = "text" # text, image, etc.

class MensajeOutput(BaseModel):
    id: int
    contenido: str
    tipo: str
    creado_en: int
    es_mio: bool
    estado: Optional[str] = None

@router.get("", response_model=List[MensajeOutput])
async def obtener_historial(usuario: dict = Depends(obtener_usuario_actual)):
    """
    Obtiene el historial de mensajes de la conversación activa en Chatwoot.
    """
    conversation_id = usuario.get("chatwoot_conversation_id")
    if not conversation_id:
        return []
        
    url = f"{settings.chatwoot.base_url}/api/v1/accounts/{settings.chatwoot.account_id}/conversations/{conversation_id}/messages"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=obtener_headers_chatwoot())
            
        if resp.status_code != 200:
            print(f"Error Chatwoot GET messages: {resp.text}")
            return []
            
        mensajes_raw = resp.json().get("payload", [])
        mensajes_procesados = []
        
        for msg in mensajes_raw:
            # Filtrar mensajes internos o privados si es necesario
            if msg.get("private"):
                continue
                
            es_mio = str(msg.get("sender", {}).get("id")) == str(usuario.get("chatwoot_contact_id"))
            
            tipo_mensaje = msg.get("message_type") # incoming (0), outgoing (1)
            print(f"DEBUG Historial: ID={msg['id']}, Tipo={tipo_mensaje}, SenderID={msg.get('sender', {}).get('id')}")
            
            # Chatwoot API v1: 0=incoming (cliente), 1=outgoing (agente)
            # También soportamos strings por si acaso
            es_mio_logica = (tipo_mensaje == 0 or tipo_mensaje == "incoming")
            
            mensajes_procesados.append(MensajeOutput(
                id=msg["id"],
                contenido=msg.get("content") or "",
                tipo=msg.get("content_type") or "text",
                creado_en=msg["created_at"],
                es_mio=es_mio_logica,
                estado=msg.get("status")
            ))
            
        return mensajes_procesados
        
    except Exception as e:
        print(f"Excepción obteniendo mensajes: {e}")
        raise HTTPException(status_code=500, detail="Error de comunicación con servicio de chat")

@router.post("", response_model=MensajeOutput)
async def enviar_mensaje(
    input_msg: MensajeInput, 
    usuario: dict = Depends(obtener_usuario_actual)
):
    """
    Envía un mensaje a Chatwoot a nombre del usuario.
    """
    import time
    start_time = time.time()
    print(f"DEBUG: Inicio enviar_mensaje para {usuario.get('email')}")

    # 2. Verificar si tiene conversation_id
    conversation_id = usuario.get("chatwoot_conversation_id")
    print(f"DEBUG: Usuario {usuario.get('email')} - Conversation ID inicial: {conversation_id}")

    if not conversation_id:
        print("DEBUG: No hay conversation_id, intentando sincronizar...")
        t_sync_start = time.time()
        
        try:
            contact_id_new, conversation_id_new, pubsub_token_new = await sincronizar_contacto_chatwoot(
                nombre=usuario.get("nombre_alias"),
                email=usuario.get("email"),
                identificador=usuario.get("credencial_externa"),
                id_usuario=usuario.get("id_cliente")
            )
            
            print(f"DEBUG: Sincronización completada en {time.time() - t_sync_start:.2f}s. IDs: Contact={contact_id_new}, Conv={conversation_id_new}")
            
            if conversation_id_new:
                conversation_id = conversation_id_new
                # Actualizar DB
                await actualizar_cache_chatwoot(usuario.get("id_cliente"), contact_id_new, conversation_id_new, pubsub_token_new)
            else:
                print("DEBUG: Falló la obtención de conversation_id tras sincronización")
                raise HTTPException(status_code=400, detail="No se pudo iniciar una conversación con el agente.")
                
        except Exception as e:
             print(f"DEBUG: Error en sincronización: {e}")
             raise HTTPException(status_code=500, detail=f"Error interno sincronizando usuario: {str(e)}")

    # 3. Enviar mensaje a Chatwoot
    url = f"{settings.chatwoot.base_url}/api/v1/accounts/{settings.chatwoot.account_id}/conversations/{conversation_id}/messages"
    headers = obtener_headers_chatwoot()
    
    payload = {
        "content": input_msg.content,
        "message_type": "incoming",
        "private": False
    }
    
    print(f"DEBUG: Enviando a Chatwoot: {url} | Payload: {payload}")
    t_req_start = time.time()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
        print(f"DEBUG: Respuesta Chatwoot recibida en {time.time() - t_req_start:.2f}s: {response.status_code}")
    except Exception as e:
        print(f"DEBUG: Excepción requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Error enviando mensaje a Chatwoot: {response.text}")
            
    msg = response.json()
    print(f"DEBUG: Fin enviar_mensaje. Duración total: {time.time() - start_time:.2f}s")
    
    return MensajeOutput(
        id=msg["id"],
        contenido=msg["content"],
        tipo=msg.get("content_type", "text"),
        creado_en=msg["created_at"],
        es_mio=True,
        estado="sent"
    )
