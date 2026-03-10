import os
import databases
from passlib.context import CryptContext

# Configuración
DATABASE_URL = os.getenv("DATABASE_URL")
database = databases.Database(DATABASE_URL)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- CENTRALIZACIÓN DE CONSULTAS SQL ---
class SQLQueries:
    CREAR_INVITADO = """
        INSERT INTO clientes_activos (credencial_externa, nombre_alias, estado_ciclo, session_token, avatar_url)
        VALUES (:credencial, :nombre, 'prospecto', :token, :avatar)
        RETURNING id_cliente
    """
    
    ACTUALIZAR_USUARIO_AUTH = """
        UPDATE clientes_activos 
        SET email = :email, password_hash = :password_hash, nombre_alias = :nombre, estado_ciclo = 'activo'
        WHERE id_cliente = :id_cliente
    """

    ACTUALIZAR_USUARIO_GOOGLE = """
        UPDATE clientes_activos 
        SET email = :email, nombre_alias = :nombre, avatar_url = :avatar, credencial_externa = :credencial, estado_ciclo = 'activo'
        WHERE id_cliente = :id_cliente
    """
    
    OBTENER_USUARIO_POR_EMAIL = """
        SELECT id_cliente, password_hash, nombre_alias, session_token, credencial_externa, chatwoot_contact_id, chatwoot_conversation_id, chatwoot_pubsub_token
        FROM clientes_activos 
        WHERE email = :email
    """
    
    OBTENER_USUARIO_POR_ID = """
        SELECT id_cliente, nombre_alias, email, session_token, credencial_externa, chatwoot_contact_id, chatwoot_conversation_id, chatwoot_pubsub_token
        FROM clientes_activos
        WHERE id_cliente = :id_cliente
    """

    ACTUALIZAR_TOKEN_SESION = """
        UPDATE clientes_activos
        SET session_token = :token
        WHERE id_cliente = :id_cliente
    """

    OBTENER_USUARIO_POR_TOKEN = """
        SELECT id_cliente, nombre_alias, email, credencial_externa, chatwoot_contact_id, chatwoot_conversation_id, chatwoot_pubsub_token
        FROM clientes_activos
        WHERE session_token = :token
    """

    OBTENER_USUARIO_POR_CREDENCIAL = """
        SELECT id_cliente, nombre_alias, email, session_token, chatwoot_contact_id, chatwoot_conversation_id, chatwoot_pubsub_token
        FROM clientes_activos
        WHERE credencial_externa = :credencial
    """

    ACTUALIZAR_CACHE_CHATWOOT = """
        UPDATE clientes_activos
        SET chatwoot_contact_id = :contact_id, chatwoot_conversation_id = :conversation_id, chatwoot_pubsub_token = :pubsub_token
        WHERE id_cliente = :id_cliente
    """

# --- GESTIÓN DE CONEXIÓN ---
async def connect_db():
    await database.connect()

async def disconnect_db():
    await database.disconnect()

# --- UTILIDADES DE SEGURIDAD ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    try:
        # print(f"DEBUG: Hashing password of length {len(password)}")
        return pwd_context.hash(password)
    except Exception as e:
        print(f"DEBUG: Error hashing password: {e}")
        # Fallback o re-raise limpio
        raise ValueError(f"Error procesando contraseña: {str(e)}")

# --- FUNCIONES DE NEGOCIO ---

async def crear_usuario_invitado(identificador: str, token: str):
    """Crea un usuario invitado y guarda su token de sesión inicial."""
    valores = {
        "credencial": identificador, 
        "nombre": f"Invitado {identificador[:6]}",
        "token": token,
        "avatar": None
    }
    try:
        id_usuario = await database.fetch_val(query=SQLQueries.CREAR_INVITADO, values=valores)
        return id_usuario
    except Exception as e:
        print(f"DEPURACIÓN: Error creando invitado: {e}")
        return None

async def registrar_usuario(id_usuario: int, email: str, password: str, nombre: str):
    """Actualiza un usuario invitado para convertirlo en registrado."""
    hash_pw = get_password_hash(password)
    valores = {
        "id_cliente": id_usuario,
        "email": email,
        "password_hash": hash_pw,
        "nombre": nombre
    }
    await database.execute(query=SQLQueries.ACTUALIZAR_USUARIO_AUTH, values=valores)

async def promover_usuario_google(id_usuario: int, email: str, nombre: str, avatar: str, sub_google: str):
    """Promueve un usuario invitado a usuario de Google."""
    valores = {
        "id_cliente": id_usuario,
        "email": email,
        "nombre": nombre,
        "avatar": avatar,
        "credencial": f"google_{sub_google}"
    }
    await database.execute(query=SQLQueries.ACTUALIZAR_USUARIO_GOOGLE, values=valores)

async def obtener_usuario_por_email(email: str):
    return await database.fetch_one(query=SQLQueries.OBTENER_USUARIO_POR_EMAIL, values={"email": email})

async def obtener_usuario_por_id(id_usuario: int):
    return await database.fetch_one(query=SQLQueries.OBTENER_USUARIO_POR_ID, values={"id_cliente": id_usuario})

async def actualizar_token_sesion(id_usuario: int, token: str):
    """Actualiza el token de sesión de un usuario existente."""
    valores = {"id_cliente": id_usuario, "token": token}
    await database.execute(query=SQLQueries.ACTUALIZAR_TOKEN_SESION, values=valores)

async def obtener_usuario_por_token(token: str):
    """Recupera un usuario usando su token de sesión."""
    return await database.fetch_one(query=SQLQueries.OBTENER_USUARIO_POR_TOKEN, values={"token": token})

async def obtener_usuario_por_credencial(credencial: str):
    """Recupera un usuario usando su credencial externa (guest_ID)."""
    return await database.fetch_one(query=SQLQueries.OBTENER_USUARIO_POR_CREDENCIAL, values={"credencial": credencial})

async def actualizar_cache_chatwoot(id_usuario: int, contact_id: int, conversation_id: int, pubsub_token: str):
    """Guarda los IDs de Chatwoot en la base de datos local."""
    valores = {
        "id_cliente": id_usuario,
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "pubsub_token": pubsub_token
    }
    await database.execute(query=SQLQueries.ACTUALIZAR_CACHE_CHATWOOT, values=valores)
