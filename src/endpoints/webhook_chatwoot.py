from fastapi import HTTPException, Request
import os
from src.etl.expropiador import ExpropiadorDeDatos

async def endpoint_webhook_chatwoot(request: Request, x_chatwoot_signature: str):
    """
    Lógica del endpoint /api/v1/webhooks/chatwoot.
    
    Endpoint asimétrico para recibir eventos de Chatwoot.
    """
    CHATWOOT_WEBHOOK_SECRET = os.getenv("CHATWOOT_WEBHOOK_SECRET")
    
    # CAPA DE DEFENSA 1: Validación de Header Secreto
    if not CHATWOOT_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=500, 
            detail="Configuración de seguridad incompleta"
        )
    
    if x_chatwoot_signature != CHATWOOT_WEBHOOK_SECRET:
        # Respuesta genérica para no revelar información
        raise HTTPException(
            status_code=403, 
            detail="Forbidden"
        )
    
    # CAPA DE DEFENSA 2: Procesamiento Síncrono
    try:
        payload = await request.json()
        
        # PASO 1: Expropiación de Datos (ETL)
        expropiador = ExpropiadorDeDatos()
        resultado_expropiacion = await expropiador.procesar_webhook(payload)
        
        # PASO 2: Orquestación Conversacional
        # Solo si fue un mensaje nuevo (no eventos de contacto)
        if resultado_expropiacion.get("status") == "procesado":
            from src.core.orquestador import OrquestadorConversacional
            
            orquestador = OrquestadorConversacional()
            await orquestador.procesar_mensaje_chatwoot(
                id_cliente=resultado_expropiacion["id_cliente"],
                texto_mensaje=resultado_expropiacion["texto_mensaje"],
                activos_ids=resultado_expropiacion.get("activos_nuevos_ids", []),
                metadata_chatwoot={
                    "conversation_id": payload.get("conversation", {}).get("id"),
                    "message_id": payload.get("id"),
                    "account_id": payload.get("account", {}).get("id"),
                    "inbox_id": payload.get("inbox", {}).get("id")
                }
            )
        
        return {"status": "received"}
    except Exception as e:
        # Loggear error real (sin exponer detalles al cliente)
        print(f"Error en webhook: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal server error")
