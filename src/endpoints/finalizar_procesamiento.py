from fastapi import HTTPException, Request
import os
import requests
import redis
import json
from src.database.connector import DatabaseConnector
from src.database.models import TipoActor, TipoDesenlace

async def endpoint_finalizar_procesamiento(request: Request):
    """
    Lógica del endpoint /api/v1/procesamiento/finalizar.
    
    Endpoint consolidado que ejecuta todos los pasos finales en una sola llamada.
    """
    try:
        payload = await request.json()
        senal_final = payload["senal_final"]
        metadata = payload["metadata_chatwoot"]
        
        # Extraer datos comunes
        id_cliente = senal_final["instruccion"]["configuracion_negocio"]["id_cliente_interno"]
        analisis = senal_final.get("analisis", {})
        respuesta_texto = analisis.get("respuesta_sugerida", "")
        id_traza = senal_final["meta"]["id_traza"]
        
        resultados = {
            "paso_1_db": None,
            "paso_2_chatwoot": None,
            "paso_3_lock": None,
            "paso_4_langfuse": None
        }
        
        # ======================================================================
        # PASO 1: GUARDAR EN BASE DE DATOS
        # ======================================================================
        try:
            print(f"📊 [1/4] Guardando transacción en DB...")
            
            db = DatabaseConnector()
            
            # Determinar tipo de actor y desenlace
            accion = analisis.get("accion_sugerida", "RESPONDER_TEXTO")
            tipo_actor = TipoActor.ia
            
            if "ESCALAR" in accion or "HUMANO" in accion:
                tipo_desenlace = TipoDesenlace.escalada_humano
            else:
                tipo_desenlace = TipoDesenlace.respuesta_ia
            
            # Insertar transacción
            sql = """
                INSERT INTO transacciones_agente (
                    id_cliente,
                    tipo_actor_respuesta,
                    tipo_desenlace,
                    input_usuario,
                    output_respuesta,
                    razonamiento_tecnico,
                    intencion_detectada,
                    resumen_estado_actual,
                    ids_activos_involucrados,
                    id_orquestacion_kestra,
                    id_mensaje_chatwoot
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id_transaccion
            """
            
            activos_ids = senal_final["instruccion"]["configuracion_negocio"].get("activos_nuevos", [])
            
            resultado_db = await db.ejecutar_escritura(sql, (
                id_cliente,
                tipo_actor.value,
                tipo_desenlace.value,
                senal_final["entrada"]["mensaje_texto"],
                respuesta_texto,
                analisis.get("razonamiento"),
                analisis.get("intencion_detectada", "DESCONOCIDA"),
                f"Procesado por MoE - {len(senal_final.get('contexto', []))} items de contexto",
                json.dumps(activos_ids),
                id_traza,
                metadata.get("message_id")
            ))
            
            resultados["paso_1_db"] = {
                "status": "success",
                "id_transaccion": resultado_db["id_transaccion"]
            }
            print(f"   ✅ Transacción guardada: ID {resultado_db['id_transaccion']}")
            
        except Exception as e:
            print(f"   ❌ Error guardando en DB: {e}")
            resultados["paso_1_db"] = {"status": "error", "error": str(e)}
            # Continuar con otros pasos aunque falle DB
        
        # ======================================================================
        # PASO 2: ENVIAR RESPUESTA A CHATWOOT
        # ======================================================================
        try:
            print(f"💬 [2/4] Enviando respuesta a Chatwoot...")
            
            chatwoot_url = os.getenv("CHATWOOT_API_URL", "http://moe_chatwoot_web:3000")
            chatwoot_token = os.getenv("CHATWOOT_API_TOKEN")
            
            if not chatwoot_token:
                raise ValueError("CHATWOOT_API_TOKEN no configurado")
            
            account_id = metadata.get("account_id")
            conversation_id = metadata.get("conversation_id")
            
            url = f"{chatwoot_url}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
            
            response = requests.post(
                url,
                headers={
                    "api_access_token": chatwoot_token,
                    "Content-Type": "application/json"
                },
                json={
                    "content": respuesta_texto,
                    "message_type": "outgoing",
                    "private": False
                },
                timeout=10
            )
            response.raise_for_status()
            
            resultados["paso_2_chatwoot"] = {
                "status": "success",
                "message_id": response.json().get("id")
            }
            print(f"   ✅ Mensaje enviado a Chatwoot")
            
        except Exception as e:
            print(f"   ❌ Error enviando a Chatwoot: {e}")
            resultados["paso_2_chatwoot"] = {"status": "error", "error": str(e)}
            # Continuar con otros pasos
        
        # ======================================================================
        # PASO 3: LIBERAR LOCK DE REDIS
        # ======================================================================
        try:
            print(f"🔓 [3/4] Liberando lock de Redis...")
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            
            lock_key = f"lock:cliente:{id_cliente}"
            deleted = redis_client.delete(lock_key)
            
            resultados["paso_3_lock"] = {
                "status": "success",
                "lock_liberado": bool(deleted)
            }
            print(f"   ✅ Lock liberado para cliente {id_cliente}")
            
        except Exception as e:
            print(f"   ❌ Error liberando lock: {e}")
            resultados["paso_3_lock"] = {"status": "error", "error": str(e)}
            # Continuar con Langfuse
        
        # ======================================================================
        # PASO 4: LOG EN OBSERVADOR (Reemplazo de Langfuse)
        # ======================================================================
        try:
            print(f"📈 [4/4] Registrando en Observador...")
            
            from src.observadores import get_observador_llm
            observador = get_observador_llm()
            
            observador.registrar_trace(
                trace_id=id_traza,
                nombre="moe_conversation_processing",
                input_data=senal_final["entrada"]["mensaje_texto"],
                output_data=respuesta_texto,
                metadata={
                    "id_cliente": id_cliente,
                    "conversation_id": metadata.get("conversation_id"),
                    "intencion": analisis.get("intencion_detectada", "DESCONOCIDA"),
                    "expertos_consultados": ["legal", "financiero", "rag", "sintetizador"],
                    "tokens_totales": senal_final["meta"].get("tokens_acumulados", 0),
                    "modelo": senal_final["meta"].get("modelo_ultimo_paso", "unknown"),
                    "tipo_desenlace": tipo_desenlace.value if 'tipo_desenlace' in locals() else "unknown"
                }
            )
            
            resultados["paso_4_langfuse"] = {"status": "success", "backend": "observador_local"}
            print(f"   ✅ Registrado en Observador Local")
                
        except Exception as e:
            print(f"   ❌ Error registrando en Observador: {e}")
            resultados["paso_4_langfuse"] = {"status": "error", "error": str(e)}
        
        # ======================================================================
        # RESUMEN FINAL
        # ======================================================================
        print(f"\n✅ Procesamiento finalizado para cliente {id_cliente}")
        print(f"   Traza: {id_traza}")
        
        # Determinar si hubo errores críticos
        errores_criticos = []
        if resultados["paso_1_db"]["status"] == "error":
            errores_criticos.append("db")
        if resultados["paso_2_chatwoot"]["status"] == "error":
            errores_criticos.append("chatwoot")
        
        return {
            "status": "completado" if not errores_criticos else "completado_con_errores",
            "errores_criticos": errores_criticos,
            "resultados": resultados,
            "id_traza": id_traza,
            "id_cliente": id_cliente
        }
        
    except Exception as e:
        print(f"❌ Error crítico en finalización: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al finalizar procesamiento: {str(e)}")
