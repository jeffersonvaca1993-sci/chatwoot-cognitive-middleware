from fastapi import HTTPException, Request
import os
import redis
import json

async def endpoint_verificar_y_acumular_cola(request: Request):
    """
    Lógica del endpoint /api/v1/cola/verificar_y_acumular.
    
    Endpoint crítico para el patrón de acumulación conversacional.
    """
    try:
        payload = await request.json()
        senal_actual = payload["senal_actual"]
        
        # Extraer id_cliente de la señal (no como parámetro separado)
        id_cliente = senal_actual["instruccion"]["configuracion_negocio"]["id_cliente_interno"]
        
        # Conectar a Redis
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        queue_key = f"queue:cliente:{id_cliente}"
        
        # Verificar si hay mensajes en la cola
        queue_length = redis_client.llen(queue_key)
        
        if queue_length == 0:
            # NO HAY MENSAJES - Continuar con guardado
            print(f"✅ Cola vacía para cliente {id_cliente}. Procediendo a finalizar.")
            return {
                "continue": False,
                "senal_actualizada": senal_actual,
                "mensajes_procesados": 0
            }
        
        # HAY MENSAJES - Acumularlos al historial
        print(f"📥 Encontrados {queue_length} mensajes en cola para cliente {id_cliente}")
        
        mensajes_acumulados = []
        while True:
            mensaje_json = redis_client.lpop(queue_key)
            if not mensaje_json:
                break
            
            mensaje = json.loads(mensaje_json)
            mensajes_acumulados.append(mensaje)
        
        # Agregar mensajes al historial_chat
        historial_actual = senal_actual.get("historial_chat", [])
        
        for msg in mensajes_acumulados:
            # Agregar mensaje del usuario al historial
            historial_actual.append({
                "rol": "user",
                "contenido": msg["texto"],
                "adjuntos": []
            })
            
            print(f"   📝 Acumulado: '{msg['texto'][:50]}...'")
        
        # Actualizar la señal con el historial enriquecido
        senal_actual["historial_chat"] = historial_actual
        
        # Actualizar también la entrada con el último mensaje
        # (para que el router tenga contexto inmediato)
        ultimo_mensaje = mensajes_acumulados[-1]
        senal_actual["entrada"]["mensaje_texto"] = ultimo_mensaje["texto"]
        
        print(f"🔄 Reiniciando procesamiento con {len(mensajes_acumulados)} mensajes acumulados")
        
        return {
            "continue": True,
            "senal_actualizada": senal_actual,
            "mensajes_procesados": len(mensajes_acumulados)
        }
        
    except Exception as e:
        print(f"Error verificando cola: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error al verificar cola")
