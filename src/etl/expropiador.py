# src/etl/expropiador.py
import hashlib
import requests
from datetime import datetime
from typing import Dict, Any, List
from src.database.models import ClientesActivos as ClienteActivo, ActivosGlobales as ActivoGlobal

class ExpropiadorDeDatos:
    def __init__(self, db_connector, storage_service):
        """
        :param db_connector: Instancia para ejecutar SQL (tu OrquestadorDeMemoria o similar).
        :param storage_service: Servicio que guarda bytes en disco/S3 y devuelve la URI.
        """
        self.db = db_connector
        self.storage = storage_service
        
        # EL SWITCH (Dispatcher)
        # Aquí registras los métodos que saben manejar cada evento de Chatwoot
        self._estrategias = {
            "contact_updated": self._caso_actualizacion_contacto,
            "contact_created": self._caso_actualizacion_contacto, # Tratamos crear/editar igual (Upsert)
            "message_created": self._caso_nuevo_mensaje,
            # Futuro: "conversation_status_changed": self._caso_cambio_estado
        }

    # =================================================================
    # MÉTODO PÚBLICO: EL PUNTO DE ENTRADA
    # =================================================================
    def procesar_webhook(self, tipo_evento: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recibe el evento crudo, busca la estrategia adecuada y ejecuta la expropiación.
        """
        estrategia = self._estrategias.get(tipo_evento)
        
        if not estrategia:
            # Si llega un evento que no nos importa (ej. 'typing_on'), lo ignoramos elegantemente.
            return {"status": "ignorado", "razon": f"Evento {tipo_evento} no tiene estrategia definida."}
        
        print(f"⚡ Iniciando expropiación para evento: {tipo_evento}")
        return estrategia(payload)

    # =================================================================
    # ESTRATEGIA 1: ACTUALIZACIÓN DE CONTACTO (Identidad)
    # =================================================================
    def _caso_actualizacion_contacto(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Toma los datos de Chatwoot y actualiza nuestra tabla maestra 'clientes_activos'.
        Separa datos duros (Email) de datos flexibles (Custom Attributes).
        """
        # 1. Extracción Segura
        datos_contacto = payload if "email" in payload else payload.get("meta", {}).get("sender", {})
        
        credencial = str(datos_contacto.get("id")) # ID de Chatwoot
        nombre = datos_contacto.get("name", "Cliente Desconocido")
        email = datos_contacto.get("email")
        telefono = datos_contacto.get("phone_number")
        
        # 2. Construcción del Cerebro Vivo (JSONB)
        # Mezclamos atributos personalizados con datos de contacto secundarios
        contexto_vivo = datos_contacto.get("custom_attributes", {})
        contexto_vivo.update({
            "email_secundario": email,
            "telefono_secundario": telefono,
            "ultima_actualizacion_origen": datetime.now().isoformat()
        })

        # 3. UPSERT en Base de Datos (Insertar o Actualizar)
        # "Si existe la credencial, actualiza el JSON. Si no, crea el cliente."
        sql = """
            INSERT INTO clientes_activos (credencial_externa, nombre_alias, contexto_vivo, ultima_actividad)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (credencial_externa) 
            DO UPDATE SET 
                nombre_alias = EXCLUDED.nombre_alias,
                contexto_vivo = clientes_activos.contexto_vivo || EXCLUDED.contexto_vivo,
                ultima_actividad = NOW()
            RETURNING id_cliente;
        """
        # Nota: En producción usarías json.dumps(contexto_vivo)
        import json
        resultado = self.db.ejecutar_escritura(sql, (credencial, nombre, json.dumps(contexto_vivo)))
        
        return {"status": "expropiado", "id_interno": resultado['id_cliente'], "tipo": "identidad"}

    # =================================================================
    # ESTRATEGIA 2: NUEVO MENSAJE (El Chat y los Archivos)
    # =================================================================
    def _caso_nuevo_mensaje(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja el flujo crítico:
        1. Garantiza que el cliente exista.
        2. Detecta archivos adjuntos.
        3. Si hay archivos, inicia el PROTOCOLO DE SECUESTRO.
        """
        mensaje_data = payload # Chatwoot a veces envía el mensaje directo o dentro de 'content'
        sender_data = mensaje_data.get("sender", {})
        
        # A. Garantizar Identidad (No podemos guardar archivos de un fantasma)
        # Llamamos a la estrategia de contacto para asegurar que el ID existe
        res_cliente = self._caso_actualizacion_contacto(sender_data)
        id_cliente_interno = res_cliente["id_interno"]

        activos_procesados = []
        adjuntos = mensaje_data.get("attachments", [])

        # B. Protocolo de Secuestro de Activos
        if adjuntos:
            print(f"   🚨 Detectados {len(adjuntos)} archivos. Iniciando secuestro...")
            activos_procesados = self._secuestrar_archivos_fisicos(adjuntos, id_cliente_interno)

        # C. Retorno para el Grafo
        # No guardamos el texto aquí (eso va a agent_transactions después), 
        # pero devolvemos los IDs de los activos para que el Agente sepa qué acaba de llegar.
        return {
            "status": "procesado",
            "id_cliente": id_cliente_interno,
            "texto_mensaje": mensaje_data.get("content"),
            "activos_nuevos_ids": [a.id_activo for a in activos_procesados] # Lista de IDs para la Pizarra
        }

    # =================================================================
    # MÉTODO PRIVADO: SECUESTRO FÍSICO (Expropiación Real)
    # =================================================================
    def _secuestrar_archivos_fisicos(self, lista_adjuntos: List[dict], id_propietario: int) -> List[ActivoGlobal]:
        """
        Descarga, Hasa, Verifica y Persiste.
        """
        activos_guardados = []

        for adjunto in lista_adjuntos:
            url_origen = adjunto.get("data_url")
            nombre_archivo = adjunto.get("title", "sin_nombre")
            
            # 1. DESCARGA (Latencia de Red)
            # Aquí pagamos el precio de la fidelidad.
            try:
                response = requests.get(url_origen, timeout=10)
                if response.status_code != 200:
                    print(f"Error descargando {url_origen}")
                    continue
                
                bytes_contenido = response.content
                
                # 2. GENERACIÓN DE HUELLA DIGITAL (Hash)
                sha256_hash = hashlib.sha256(bytes_contenido).hexdigest()
                
                # 3. VERIFICACIÓN DE VERDAD (MIME Type Real)
                # No confiamos en Chatwoot, miramos los bytes.
                # (Simplificado, en prod usarías biblioteca 'magic')
                mime_real = response.headers.get("Content-Type", "application/octet-stream")
                
                # 4. ALMACENAMIENTO FRÍO (S3 / Disco)
                # El storage_service nos devuelve la URI donde quedó guardado para siempre
                ruta_final = self.storage.guardar(
                    nombre_archivo=f"{sha256_hash}_{nombre_archivo}", 
                    contenido=bytes_contenido
                )
                
                # 5. PERSISTENCIA EN BÓVEDA (Base de Datos)
                sql_activo = """
                    INSERT INTO activos_globales 
                    (id_propietario, huella_digital_hash, tipo_mime_real, ruta_almacenamiento, nombre_original, tamano_bytes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id_activo;
                """
                res = self.db.ejecutar_escritura(sql_activo, (
                    id_propietario, sha256_hash, mime_real, ruta_final, nombre_archivo, len(bytes_contenido)
                ))
                
                # Creamos el objeto en memoria para devolverlo
                activos_guardados.append(ActivoGlobal(
                    id_activo=res['id_activo'],
                    id_propietario=id_propietario,
                    huella_digital_hash=sha256_hash,
                    tipo_mime_real=mime_real,
                    ruta_almacenamiento=ruta_final,
                    tamano_bytes=len(bytes_contenido)
                ))
            except Exception as e:
                print(f"Error procesando adjunto {url_origen}: {e}")
                continue
            
        return activos_guardados
