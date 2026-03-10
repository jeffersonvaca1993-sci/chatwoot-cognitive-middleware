from fastapi import Header, HTTPException, Depends
from typing import Optional
from private.database import obtener_usuario_por_token

async def obtener_usuario_actual(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None, alias="X-Session-Token")
):
    """
    Recupera el usuario actual basado en el token de sesión.
    Acepta header 'Authorization: Bearer <token>' o 'X-Session-Token: <token>'.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif x_session_token:
        token = x_session_token
        
    if not token:
        raise HTTPException(status_code=401, detail="Token de autenticación faltante")
        
    usuario = await obtener_usuario_por_token(token)
    if not usuario:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
        
    return dict(usuario)
