from fastapi import HTTPException, Request
import os
import requests
import redis
import json
from src.database.connector import DatabaseConnector
from src.database.models import TipoActor, TipoDesenlace

async def endpoint_sintetizar_y_finalizar(request: Request):
    """
    Lógica del endpoint /api/v1/procesamiento/sintetizar_y_finalizar.
    
    Endpoint ultra-consolidado que ejecuta:
    1. Síntesis Final
    2. Guardar en DB
    3. Enviar a Chatwoot
    4. Liberar lock de Redis
    5. Log en Langfuse
    """
    try:
        payload = await request.json()
        senal_actual = payload["senal_actual"]
        
        # Extraer metadata de la señal
        id_cliente = senal_actual["instruccion"]["configuracion_negocio"]["id_cliente_interno"]
        conversation_id = senal_actual["instruccion"]["configuracion_negocio"].get("conversation_id")
        
        resultados = {
            "paso_1_sintesis": None,
            "paso_2_db": None,
            "paso_3_chatwoot": None,
            "paso_4_lock": None,
            "paso_5_langfuse": None
        }
        
        # ======================================================================
        # PASO 1: SÍNTESIS FINAL
        # ======================================================================
        try:
            print(f"🎨 [1/5] Generando síntesis final...")
            
            # Llamar al sintetizador final
            # Nota: Aquí estamos haciendo una llamada HTTP interna a otro endpoint de la misma API.
            # Idealmente, deberíamos llamar a la función directamente si es posible, 
            # pero para mantener la arquitectura de microservicios/nodos, la llamada HTTP es válida.
            # Sin embargo, dado que estamos refactorizando, podríamos importar la función de procesar_nodo.
            # Por ahora mantendremos la llamada HTTP para no romper la lógica existente,
            # pero apuntando a localhost.
            
            # IMPORTANTE: Si estamos dentro del mismo proceso, llamar a localhost puede ser problemático si no hay concurrencia adecuada.
            # Pero como es async, debería estar bien.
            # Alternativa: Importar endpoint_procesar_nodo y llamarlo directamente.
            # Vamos a intentar mantener la lógica original por seguridad.
            
            sintesis_response = requests.post(
                "http://moe_api:8000/api/v1/procesar_nodo",
                json={
                    "meta": senal_actual["meta"],
                    "instruccion": {
                        "tipo_estrategia": "SINTETIZADOR_FINAL",
                        "configuracion_negocio": {
                            "conversation_id": conversation_id,
                            "formato_salida": "texto_natural_completo"
                        }
                    },
                    "historial_chat": senal_actual["historial_chat"],
                    "contexto": senal_actual["contexto"],
                    "entrada": senal_actual["entrada"],
                    "analisis": None
                },
                timeout=30
            )
            sintesis_response.raise_for_status()
            senal_final = sintesis_response.json()
            
            resultados["paso_1_sintesis"] = {"status": "success"}
            print(f"   ✅ Síntesis final generada")
            
        except Exception as e:
            print(f"   ❌ Error en síntesis final: {e}")
            resultados["paso_1_sintesis"] = {"status": "error", "error": str(e)}
            raise  # Error crítico, no continuar
        
        # Extraer datos de la síntesis
        analisis = senal_final.get("analisis", {})
        respuesta_texto = analisis.get("respuesta_sugerida", "")
        id_traza = senal_final["meta"]["id_traza"]
        
        # ======================================================================
        # PASO 2: GUARDAR EN BASE DE DATOS
        # ======================================================================
        try:
            print(f"📊 [2/5] Guardando transacción en DB...")
            
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
            message_id = senal_final["instruccion"]["configuracion_negocio"].get("message_id")
            
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
                message_id
            ))
            
            resultados["paso_2_db"] = {
                "status": "success",
                "id_transaccion": resultado_db["id_transaccion"]
            }
            print(f"   ✅ Transacción guardada: ID {resultado_db['id_transaccion']}")
            
        except Exception as e:
            print(f"   ❌ Error guardando en DB: {e}")
            resultados["paso_2_db"] = {"status": "error", "error": str(e)}
            # Continuar con otros pasos
        
        # ======================================================================
        # PASO 3: ENVIAR RESPUESTA A CHATWOOT
        # ======================================================================
        try:
            print(f"💬 [3/5] Enviando respuesta a Chatwoot...")
            
            chatwoot_url = os.getenv("CHATWOOT_API_URL", "http://moe_chatwoot_web:3000")
            chatwoot_token = os.getenv("CHATWOOT_API_TOKEN")
            
            if not chatwoot_token:
                raise ValueError("CHATWOOT_API_TOKEN no configurado")
            
            account_id = senal_actual["instruccion"]["configuracion_negocio"].get("account_id")
            
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
            
            resultados["paso_3_chatwoot"] = {
                "status": "success",
                "message_id": response.json().get("id")
            }
            print(f"   ✅ Mensaje enviado a Chatwoot")
            
        except Exception as e:
            print(f"   ❌ Error enviando a Chatwoot: {e}")
            resultados["paso_3_chatwoot"] = {"status": "error", "error": str(e)}
            # Continuar con otros pasos
        
        # ======================================================================
        # PASO 4: LIBERAR LOCK DE REDIS
        # ======================================================================
        try:
            print(f"🔓 [4/5] Liberando lock de Redis...")
            
            redis_host = os.getenv("REDIS_HOST", "redis")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            
            lock_key = f"lock:cliente:{id_cliente}"
            deleted = redis_client.delete(lock_key)
            
            resultados["paso_4_lock"] = {
                "status": "success",
                "lock_liberado": bool(deleted)
            }
            print(f"   ✅ Lock liberado para cliente {id_cliente}")
            
        except Exception as e:
            print(f"   ❌ Error liberando lock: {e}")
            resultados["paso_4_lock"] = {"status": "error", "error": str(e)}
            # Continuar con Langfuse
        
        # ======================================================================
        # PASO 5: LOG EN OBSERVADOR (Reemplazo de Langfuse)
        # ======================================================================
        try:
            print(f"📈 [5/5] Registrando en Observador...")
            
            from src.observadores import get_observador_llm
            observador = get_observador_llm()
            
            observador.registrar_trace(
                trace_id=id_traza,
                nombre="moe_conversation_processing",
                input_data=senal_final["entrada"]["mensaje_texto"],
                output_data=respuesta_texto,
                metadata={
                    "id_cliente": id_cliente,
                    "conversation_id": conversation_id,
                    "intencion": analisis.get("intencion_detectada", "DESCONOCIDA"),
                    "expertos_consultados": ["legal", "financiero", "rag", "sintetizador"],
                    "tokens_totales": senal_final["meta"].get("tokens_acumulados", 0),
                    "modelo": senal_final["meta"].get("modelo_ultimo_paso", "unknown"),
                    "tipo_desenlace": tipo_desenlace.value if 'tipo_desenlace' in locals() else "unknown"
                }
            )
            
            resultados["paso_5_langfuse"] = {"status": "success", "backend": "observador_local"}
            print(f"   ✅ Registrado en Observador Local")
                
        except Exception as e:
            print(f"   ❌ Error registrando en Observador: {e}")
            resultados["paso_5_langfuse"] = {"status": "error", "error": str(e)}
        
        # ======================================================================
        # RESUMEN FINAL
        # ======================================================================
        print(f"\n✅ Procesamiento completo finalizado para cliente {id_cliente}")
        print(f"   Traza: {id_traza}")
        
        # Determinar si hubo errores críticos
        errores_criticos = []
        if resultados["paso_1_sintesis"]["status"] == "error":
            errores_criticos.append("sintesis")
        if resultados["paso_2_db"]["status"] == "error":
            errores_criticos.append("db")
        if resultados["paso_3_chatwoot"]["status"] == "error":
            errores_criticos.append("chatwoot")
        
        return {
            "status": "completado" if not errores_criticos else "completado_con_errores",
            "errores_criticos": errores_criticos,
            "resultados": resultados,
            "senal_final": senal_final,
            "id_traza": id_traza,
            "id_cliente": id_cliente
        }
        
    except Exception as e:
        print(f"❌ Error crítico en sintetizar_y_finalizar: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al sintetizar y finalizar: {str(e)}")
