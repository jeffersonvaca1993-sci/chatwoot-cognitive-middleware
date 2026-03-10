from fastapi import APIRouter, HTTPException, Header, Depends, Request
from pydantic import BaseModel
import secrets
import httpx
import os
from typing import Optional
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from private.config_loader import settings
from private.database import (
    crear_usuario_invitado, registrar_usuario, obtener_usuario_por_email, 
    obtener_usuario_por_token, actualizar_token_sesion, verify_password,
    promover_usuario_google, actualizar_cache_chatwoot, obtener_usuario_por_id
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

# --- MODELOS ---
class RegistroRequest(BaseModel):
    nombre: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    id_token: str

# --- UTILIDADES ---
def obtener_headers_chatwoot():
    return {
        "api_access_token": settings.chatwoot.api_token,
        "Content-Type": "application/json"
    }

async def sincronizar_contacto_chatwoot(nombre: str, email: str, identificador: str, id_usuario: int, es_nuevo: bool = False):
    """
    Crea o actualiza un contacto en Chatwoot usando la API Pública (Client API)
    y guarda los IDs y pubsub_token en caché local.
    """
    # Usar el Token del Inbox (identificador del canal API)
    inbox_token = settings.chatwoot.inbox_id
    base_url = f"{settings.chatwoot.base_url}/public/api/v1/inboxes/{inbox_token}"
    
    async with httpx.AsyncClient() as client:
        # 1. Crear/Actualizar Contacto (Client API)
        # La API de Cliente usa 'identifier' como clave única para upsert.
        payload = {
            "identifier": identificador,
            "name": nombre,
            "email": email
        }
        
        # Si tenemos ID interno, lo pasamos como custom attribute?
        # La API pública acepta custom_attributes
        payload["custom_attributes"] = {"id_cliente_interno": str(id_usuario)}

        print(f"DEBUG: Sincronizando contacto en {base_url}/contacts")
        try:
            resp = await client.post(f"{base_url}/contacts", json=payload)
        except Exception as e:
            print(f"DEBUG: Error conexión Chatwoot: {e}")
            return None, None, None

        if resp.status_code != 200:
            print(f"DEBUG: Error Chatwoot API: {resp.status_code} - {resp.text}")
            return None, None, None

        data = resp.json()
        pubsub_token = data.get("pubsub_token")
        source_id = data.get("source_id")
        contact_data = data.get("contact", {})
        contact_id = contact_data.get("id")
        
        print(f"DEBUG: Contacto sincronizado. SourceID: {source_id}, PubSub: {bool(pubsub_token)}")

        # 2. Obtener/Crear Conversación
        # Para enviar mensajes, necesitamos un conversation_id.
        # La API de Cliente permite listar conversaciones del contacto.
        conversation_id = None
        
        # Listar conversaciones activas
        try:
            conv_resp = await client.get(f"{base_url}/contacts/{source_id}/conversations")
            if conv_resp.status_code == 200:
                conversations = conv_resp.json().get("payload", [])
                if conversations:
                    # Tomar la última activa
                    conversation_id = conversations[0]["id"]
                    print(f"DEBUG: Conversación existente encontrada: {conversation_id}")
        except Exception as e:
            print(f"DEBUG: Error listando conversaciones: {e}")

        # Si no hay conversación, crear una
        if not conversation_id:
            try:
                print("DEBUG: Creando nueva conversación...")
                create_resp = await client.post(f"{base_url}/contacts/{source_id}/conversations")
                if create_resp.status_code == 200:
                    conversation_id = create_resp.json().get("id")
                    print(f"DEBUG: Nueva conversación creada: {conversation_id}")
                else:
                    print(f"DEBUG: Error creando conversación: {create_resp.text}")
            except Exception as e:
                print(f"DEBUG: Error creando conversación: {e}")

        return contact_id, conversation_id, pubsub_token

# --- ENDPOINTS ---

@router.post("/guest")
async def login_invitado():
    """
    Inicio de sesión anónimo.
    Genera un usuario temporal y un token de sesión.
    """
    # 1. Generar credenciales
    uuid_invitado = secrets.token_hex(8)
    credencial = f"guest_{uuid_invitado}"
    token_sesion = secrets.token_urlsafe(32)
    
    # 2. Crear en DB
    id_usuario = await crear_usuario_invitado(credencial, token_sesion)
    
    if not id_usuario:
        raise HTTPException(status_code=500, detail="Error creando usuario invitado")
    
    # 3. Sincronizar con Chatwoot (Crear contacto)
    contact_id, conversation_id, pubsub_token = await sincronizar_contacto_chatwoot(
        nombre=f"Visitante {uuid_invitado[:6]}",
        email=None,
        identificador=credencial,
        id_usuario=id_usuario,
        es_nuevo=True
    )
    
    if contact_id:
        await actualizar_cache_chatwoot(id_usuario, contact_id, conversation_id, pubsub_token)
    
    return {
        "token": token_sesion,
        "rol": "guest",
        "nombre": f"Visitante {uuid_invitado[:6]}",
        "pubsub_token": pubsub_token
    }

@router.get("/config")
async def get_config():
    """
    Retorna configuración pública para el frontend.
    """
    return {
        "chatwoot_ws_url": "/api/ws/chat"
    }

@router.post("/google")
async def login_google(
    request: GoogleLoginRequest, 
    authorization: Optional[str] = Header(None)
):
    """
    Login o Registro con Google.
    Si el email no existe, promueve al usuario invitado actual (si existe token).
    """
    # 1. Validar Token de Google
    try:
        id_info = id_token.verify_oauth2_token(
            request.id_token, 
            google_requests.Request(), 
            audience=os.getenv("GOOGLE_CLIENT_ID") 
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido")
    
    email = id_info.get("email")
    sub_google = id_info.get("sub")
    nombre = id_info.get("name")
    avatar = id_info.get("picture")
    
    # 2. Verificar si el usuario ya existe
    usuario_existente = await obtener_usuario_por_email(email)
    
    if usuario_existente:
        # LOGIN: Usuario ya registrado
        nuevo_token = secrets.token_urlsafe(32)
        await actualizar_token_sesion(usuario_existente["id_cliente"], nuevo_token)
        
        return {
            "token": nuevo_token,
            "rol": "registered",
            "nombre": usuario_existente["nombre_alias"],
            "avatar": avatar,
            "pubsub_token": usuario_existente["chatwoot_pubsub_token"]
        }
    else:
        # REGISTRO / FUSIÓN
        token_invitado = None
        if authorization and authorization.startswith("Bearer "):
            token_invitado = authorization.split(" ")[1]
        
        usuario_invitado = None
        if token_invitado:
            usuario_invitado = await obtener_usuario_por_token(token_invitado)
        
        if usuario_invitado:
            # Promover invitado a registrado
            id_usuario = usuario_invitado["id_cliente"]
            await promover_usuario_google(id_usuario, email, nombre, avatar, sub_google)
        else:
            # Crear nuevo usuario directamente
            uuid_temp = secrets.token_hex(8)
            token_temp = secrets.token_urlsafe(32)
            id_usuario = await crear_usuario_invitado(f"google_{sub_google}", token_temp)
            await promover_usuario_google(id_usuario, email, nombre, avatar, sub_google)
            
        # Sincronizar Chatwoot con datos reales
        contact_id, conversation_id, pubsub_token = await sincronizar_contacto_chatwoot(
            nombre=nombre,
            email=email,
            identificador=f"google_{sub_google}",
            id_usuario=id_usuario
        )
        if contact_id:
            await actualizar_cache_chatwoot(id_usuario, contact_id, conversation_id, pubsub_token)
            
        token_final = token_invitado if usuario_invitado else token_temp
        
        return {
            "token": token_final,
            "rol": "registered",
            "nombre": nombre,
            "avatar": avatar,
            "pubsub_token": pubsub_token
        }

@router.post("/register")
async def registro_manual(
    request: RegistroRequest, 
    guest_jwt: Optional[str] = Header(None, alias="guest_jwt") 
):
    """
    Registro manual con email y contraseña.
    Promueve al usuario invitado.
    """
    if not guest_jwt:
        raise HTTPException(status_code=401, detail="Token de invitado requerido para registro")
        
    usuario_invitado = await obtener_usuario_por_token(guest_jwt)
    if not usuario_invitado:
        raise HTTPException(status_code=401, detail="Sesión de invitado inválida")
        
    # Verificar email
    if await obtener_usuario_por_email(request.email):
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
        
    # Actualizar DB
    try:
        await registrar_usuario(
            usuario_invitado["id_cliente"], 
            request.email, 
            request.password, 
            request.nombre
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"DEBUG: Error en registrar_usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno al registrar usuario")
    
    # Sincronizar Chatwoot
    contact_id, conversation_id, pubsub_token = await sincronizar_contacto_chatwoot(
        nombre=request.nombre,
        email=request.email,
        identificador=usuario_invitado["credencial_externa"], 
        id_usuario=usuario_invitado["id_cliente"]
    )
    
    if contact_id:
        await actualizar_cache_chatwoot(usuario_invitado["id_cliente"], contact_id, conversation_id, pubsub_token)
        
    return {
        "status": "ok",
        "token": guest_jwt, 
        "nombre": request.nombre,
        "rol": "registered",
        "pubsub_token": pubsub_token
    }

@router.post("/login")
async def login_manual(request: LoginRequest):
    """
    Login manual con email y contraseña.
    """
    usuario = await obtener_usuario_por_email(request.email)
    if not usuario or not usuario["password_hash"]:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
    if not verify_password(request.password, usuario["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        
    # Generar nuevo token
    nuevo_token = secrets.token_urlsafe(32)
    await actualizar_token_sesion(usuario["id_cliente"], nuevo_token)
    
    return {
        "token": nuevo_token,
        "nombre": usuario["nombre_alias"],
        "rol": "registered",
        "pubsub_token": usuario["chatwoot_pubsub_token"]
    }
