# src/core/orquestador.py
import redis
import requests
import json
from typing import Dict, Any, Optional
from datetime import datetime
from src.core.protocolos import SenalAgente, Instruccion, Entrada, Metadatos, MensajeNativo, ItemContexto
from src.database.connector import DatabaseConnector
import os

class OrquestadorConversacional:
    """
    Responsable de coordinar el flujo conversacional después de la expropiación de datos.
    
    ARQUITECTURA:
    1. Genera SenalAgente inicial desde datos de Chatwoot
    2. Verifica con Redis si hay otro agente procesando ese cliente (lock distribuido)
    3. Si está libre: dispara workflow de Kestra
    4. Si está ocupado: encola mensaje en Redis para procesamiento posterior
    """
    
    def __init__(self):
        # Conexión a Redis para locks y colas
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        
        # URL de Kestra
        self.kestra_url = os.getenv("KESTRA_URL", "http://moe_kestra:8080")
        
        # Timeout para el lock (segundos)
        self.lock_timeout = 300  # 5 minutos
        
        # Connector de DB
        self.db = DatabaseConnector()
    
    async def procesar_mensaje_chatwoot(
        self, 
        id_cliente: int, 
        texto_mensaje: str, 
        activos_ids: list,
        metadata_chatwoot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Función principal que orquesta el procesamiento de un mensaje de Chatwoot.
        
        :param id_cliente: ID interno del cliente en nuestra DB
        :param texto_mensaje: Contenido del mensaje del usuario
        :param activos_ids: Lista de IDs de activos recién expropiados
        :param metadata_chatwoot: Metadata adicional de Chatwoot (conversation_id, message_id, etc)
        :return: Resultado del procesamiento
        """
        lock_key = f"lock:cliente:{id_cliente}"
        queue_key = f"queue:cliente:{id_cliente}"
        
        # 1. INTENTAR ADQUIRIR LOCK
        lock_adquirido = self.redis_client.set(
            lock_key, 
            "processing", 
            nx=True,  # Solo si no existe
            ex=self.lock_timeout  # Expira automáticamente
        )
        
        if not lock_adquirido:
            # HAY OTRO AGENTE PROCESANDO ESTE CLIENTE
            print(f"⏳ Cliente {id_cliente} está siendo procesado. Encolando mensaje...")
            return await self._encolar_mensaje(
                queue_key=queue_key,
                id_cliente=id_cliente,
                texto_mensaje=texto_mensaje,
                activos_ids=activos_ids,
                metadata_chatwoot=metadata_chatwoot
            )
        
        
        # 2. LOCK ADQUIRIDO - PROCESAR INMEDIATAMENTE
        print(f"🔓 Lock adquirido para cliente {id_cliente}. Iniciando procesamiento...")
        
        # 2.1 Generar SenalAgente inicial
        senal = await self._construir_senal_inicial(
            id_cliente=id_cliente,
            texto_mensaje=texto_mensaje,
            activos_ids=activos_ids,
            metadata_chatwoot=metadata_chatwoot
        )
        
        # 2.2 Disparar workflow de Kestra
        # IMPORTANTE: El lock NO se libera aquí
        # Kestra lo liberará al final del flujo completo (después de procesar toda la cola)
        resultado = await self._invocar_kestra(senal, metadata_chatwoot)
        
        return resultado

    
    async def _construir_senal_inicial(
        self,
        id_cliente: int,
        texto_mensaje: str,
        activos_ids: list,
        metadata_chatwoot: Dict[str, Any]
    ) -> SenalAgente:
        """
        Construye la SenalAgente inicial desde los datos de Chatwoot.
        """
        # Recuperar historial de conversación desde DB
        historial = await self._recuperar_historial_chat(id_cliente, limite=10)
        
        # Recuperar contexto del cliente desde DB
        contexto_cliente = await self._recuperar_contexto_cliente(id_cliente)
        
        # Construir la señal
        senal = SenalAgente(
            meta=Metadatos(
                origen="chatwoot_webhook",
                id_traza=metadata_chatwoot.get("message_id", "unknown")
            ),
            instruccion=Instruccion(
                tipo_estrategia="ROUTER_INICIAL",  # El router decidirá qué experto usar
                configuracion_negocio={
                    "id_cliente_interno": id_cliente,
                    "conversation_id": metadata_chatwoot.get("conversation_id"),
                    "activos_nuevos": activos_ids,
                    # Configuración de expertos para el subflujo
                    "expertos": [
                        "ANALISIS_LEGAL",
                        "ANALISIS_FINANCIERO",
                        "RAG_CONOCIMIENTO"
                    ],
                    "ejecutar_router": True,
                    "estrategia_sintesis": "SINTETIZADOR_PARCIAL",
                    "config_sintesis": {
                        "formato_salida": "acumulativo"
                    }
                }
            ),
            historial_chat=historial,
            contexto=[
                ItemContexto(
                    tipo="perfil_usuario",
                    contenido=contexto_cliente
                )
            ],
            entrada=Entrada(
                mensaje_texto=texto_mensaje,
                referencias_archivos=[{"id_activo": aid} for aid in activos_ids]
            ),
            analisis=None  # Aún no ha sido procesado
        )
        
        return senal
    
    async def _recuperar_historial_chat(self, id_cliente: int, limite: int = 10) -> list[MensajeNativo]:
        """
        Recupera el historial de conversación desde la DB.
        """
        sql = """
            SELECT tipo_actor_respuesta, input_usuario, output_respuesta, fecha_cierre
            FROM transacciones_agente
            WHERE id_cliente = %s
            ORDER BY fecha_cierre DESC
            LIMIT %s
        """
        
        resultados = await self.db.ejecutar_lectura(sql, (id_cliente, limite))
        
        # Convertir a MensajeNativo
        historial = []
        for row in reversed(resultados):  # Orden cronológico
            # Mensaje del usuario
            historial.append(MensajeNativo(
                rol="user",
                contenido=row["input_usuario"]
            ))
            
            # Respuesta (si existe)
            if row["output_respuesta"]:
                rol = "assistant" if row["tipo_actor_respuesta"] == "ia" else "assistant"
                historial.append(MensajeNativo(
                    rol=rol,
                    contenido=row["output_respuesta"]
                ))
        
        return historial
    
    async def _recuperar_contexto_cliente(self, id_cliente: int) -> Dict[str, Any]:
        """
        Recupera el contexto vivo del cliente desde la DB.
        """
        sql = """
            SELECT nombre_alias, estado_ciclo, contexto_vivo
            FROM clientes_activos
            WHERE id_cliente = %s
        """
        
        resultado = await self.db.ejecutar_lectura(sql, (id_cliente,))
        
        if not resultado:
            return {}
        
        row = resultado[0]
        return {
            "nombre": row["nombre_alias"],
            "estado": row["estado_ciclo"],
            **row.get("contexto_vivo", {})
        }
    
    async def _invocar_kestra(self, senal: SenalAgente, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispara el workflow de Kestra con la señal inicial.
        """
        # Convertir SenalAgente a dict para enviar por HTTP
        payload_kestra = {
            "senal_agente": senal.model_dump(mode="json"),
            "metadata_chatwoot": metadata
        }
        
        # Endpoint del flujo de Kestra
        url = f"{self.kestra_url}/api/v1/executions/webhook/sci.vacasantana/flujo_procesamiento_moe/moe-secret-key"
        
        try:
            response = requests.post(
                url,
                json=payload_kestra,
                timeout=30
            )
            response.raise_for_status()
            
            print(f"✅ Workflow de Kestra disparado exitosamente")
            return {
                "status": "workflow_iniciado",
                "execution_id": response.json().get("id")
            }
            
        except Exception as e:
            print(f"❌ Error al invocar Kestra: {e}")
            raise
    
    async def _encolar_mensaje(
        self,
        queue_key: str,
        id_cliente: int,
        texto_mensaje: str,
        activos_ids: list,
        metadata_chatwoot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Encola un mensaje en Redis cuando el cliente está siendo procesado.
        """
        mensaje_encolado = {
            "timestamp": datetime.now().isoformat(),
            "id_cliente": id_cliente,
            "texto": texto_mensaje,
            "activos_ids": activos_ids,
            "metadata": metadata_chatwoot
        }
        
        # Agregar a la cola (lista de Redis)
        self.redis_client.rpush(queue_key, json.dumps(mensaje_encolado))
        
        print(f"📥 Mensaje encolado para cliente {id_cliente}")
        
        return {
            "status": "encolado",
            "queue_position": self.redis_client.llen(queue_key)
        }
