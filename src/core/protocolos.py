# src/core/protocolos.py
from typing import List, Dict, Any, Optional, Literal, Union, ForwardRef
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import uuid

# ==============================================================================
# 0. REFERENCIAS Y TIPOS AUXILIARES
# ==============================================================================

# ForwardRef es necesario para permitir la "Recursividad".
# Nos permite decir: "Un Item de Contexto puede contener una SenalAgente completa dentro".
# Esto es vital para que un agente pueda leer la memoria completa de un agente anterior.
SenalAgenteRef = ForwardRef('SenalAgente')

# Estandarización de roles para normalizar la conversación antes de enviarla a cualquier LLM.
# No importa si usamos Gemini, Ollama o GPT; internamente siempre usamos estos roles.
RolLLM = Literal["system", "user", "assistant", "tool"]

class MensajeNativo(BaseModel):
    """Formato intermedio normalizado para construir prompts (ChatML style)."""
    rol: RolLLM
    contenido: str
    # Soporte multimodal abstracto (imágenes/archivos para el modelo)
    adjuntos: List[str] = []

# Tipos de datos que pueden vivir en la memoria del agente.
TipoContenidoContexto = Literal[
    "payload_webhook",       # Datos crudos recibidos (ej: JSON de Chatwoot)
    "perfil_usuario",        # Datos estructurados leídos del CRM/DB
    "fragmento_rag",         # Texto recuperado de la Base de Datos Vectorial (pgvector)
    "memoria_agente_previo"  # CRÍTICO: Resultado de otro nodo experto (Patrón Fan-In)
]

# ==============================================================================
# 1. LA ESCLUSA DE SEGURIDAD (CAPA PÚBLICA / HTTP)
# Estos modelos definen la interfaz con el mundo exterior (Chatwoot/Webhooks).
# Actúan como barrera de seguridad.
# ==============================================================================

class ArchivoPublico(BaseModel):
    """Representación insegura de un archivo que viene de internet."""
    nombre: str
    url_descarga: str
    tipo_mime: str

class PeticionUsuario(BaseModel):
    """
    [INPUT PÚBLICO - INSEGURO]
    Contrato de entrada para el endpoint HTTP público.
    
    ARQUITECTURA:
    El Main (FastAPI) recibe esto y lo TRANSFORMA inmediatamente en una 'SenalAgente'.
    Nunca pasamos este objeto crudo a los expertos para evitar inyecciones o datos sucios.
    """
    mensaje: str
    archivos: List[ArchivoPublico] = []
    # Metadatos externos (ej: IDs de Chatwoot, IP del usuario) que se limpian al entrar
    meta_externa: Dict[str, Any] = Field(default_factory=dict) 

class RespuestaPublica(BaseModel):
    """
    [OUTPUT PÚBLICO - SEGURO]
    Proyección de salida para el cliente final (Chatwoot).
    
    MITIGACIÓN DE SEGURIDAD (Data Leakage):
    - Este objeto NO tiene campos para 'System Prompt', 'Contexto RAG' o 'Historial'.
    - Al forzar la salida a este formato, garantizamos matemáticamente que no
      podemos filtrar secretos internos o instrucciones del sistema por error.
    """
    respuesta_texto: str
    acciones_sugeridas: List[str] = []
    archivos_generados: List[str] = []
    id_traza: str # Para soporte técnico, permite buscar el log interno sin exponerlo

# ==============================================================================
# 2. EL NÚCLEO DEL NEGOCIO (LA TUBERÍA SIMÉTRICA - INTERNA)
# Estos objetos viajan entre Kestra y Python. Representan el ESTADO DEL SISTEMA.
# Kestra recibe 'SenalAgente' y devuelve 'SenalAgente'.
# ==============================================================================

class Metadatos(BaseModel):
    """Trazabilidad técnica del viaje de la señal por los nodos."""
    id_traza: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_creacion: datetime = Field(default_factory=datetime.now)
    origen: str = "api_publica"
    # Métricas acumulativas vitales para control de costos y performance
    tokens_acumulados: int = 0
    modelo_ultimo_paso: Optional[str] = None


class Instruccion(BaseModel):
    """
    [LA ORDEN EJECUTIVA]
    Determina qué 'Estrategia' (Clase Python) se debe instanciar para procesar esta señal.
    
    ARQUITECTURA:
    Kestra configura este campo en el YAML antes de llamar al nodo Python.
    Es el "Router" quien decide qué poner aquí.
    """
    tipo_estrategia: str = "ANALISIS_DEFAULT" # Ej: "RAG_LEGAL", "FUSIONAR_RESPUESTAS"
    # Parámetros de negocio (no técnicos). Ej: {"nivel_rigurosidad": "alto", "idioma": "es"}
    configuracion_negocio: Dict[str, Any] = {}

class Entrada(BaseModel):
    """
    La entrada del usuario, ya internalizada, validada y limpia.
    Los archivos aquí ya no son URLs inseguras, sino referencias a rutas internas o blobs.
    """
    mensaje_texto: str
    referencias_archivos: List[Dict[str, Any]] = []

class AnalisisCognitivo(BaseModel):
    """
    [EL DICTAMEN DEL EXPERTO]
    Es la estructura estándar donde CUALQUIER experto escribe su conclusión.
    Este es el objeto más importante que se guarda en el historial.
    """
    intencion_detectada: str = "DESCONOCIDA"
    # La respuesta textual final para el humano
    respuesta_sugerida: Optional[str] = None
    # La acción sistémica que el orquestador debe ejecutar (ej: TRANSFERIR_HUMANO, GUARDAR_DB)
    accion_sugerida: str = "RESPONDER_TEXTO"
    # Explicación del porqué (Chain of Thought). Útil para auditoría y debug.
    razonamiento: Optional[str] = None

class ItemContexto(BaseModel):
    """
    [LA MEMORIA DE CORTO PLAZO]
    Unidad atómica de información disponible para el experto.
    
    ARQUITECTURA (Recursividad):
    Gracias a 'SenalAgenteRef', podemos guardar el ESTADO COMPLETO de un agente anterior.
    Esto permite que el 'Agente Sintetizador' reciba el trabajo crudo del 'Agente Legal'
    y del 'Agente Financiero' sin perder detalle.
    """
    tipo: TipoContenidoContexto
    # Union polimórfica: Puede guardar datos planos, listas, o una SenalAgente completa.
    contenido: Union[Dict[str, Any], List[Any], str, AnalisisCognitivo, SenalAgenteRef]

class SenalAgente(BaseModel):
    """
    [EL CONTRATO SIMÉTRICO UNIVERSAL]
    Objeto Único de Transferencia (DTO Maestro).
    
    REGLA DE ORO:
    - Input del Main -> Output del Main.
    - Input de Kestra -> Output de Kestra.
    - Input de la Estrategia -> Output de la Estrategia.
    
    Todo el sistema está diseñado para enriquecer este objeto paso a paso,
    nunca para destruirlo o reemplazarlo.
    """
    meta: Metadatos = Field(default_factory=Metadatos)
    instruccion: Instruccion
    historial_chat: List[MensajeNativo]   # Lista de mensajes previos de la conversación
    contexto: List[ItemContexto] = []
    entrada: Entrada
    # El resultado final se escribe aquí. Si es None, el agente no ha pensado aún.
    analisis: Optional[AnalisisCognitivo] = None


    class Config:
        # Permite la inyección de tipos complejos definidos en ForwardRef
        arbitrary_types_allowed = True

# ==============================================================================
# 3. EL PROTOCOLO DE EJECUCIÓN (ENCAPSULAMIENTO TÉCNICO - PRIVADO)
# Estos objetos SOLO viven dentro de la carpeta /expertos/ y /clientes_llm/.
# El Main (FastAPI) NO debe usarlos.
# Rompen la simetría temporalmente para hablar con el Cliente LLM (Gemini/Ollama).
# ==============================================================================

class PayloadTecnicoLLM(BaseModel):
    """
    [BORRADOR TÉCNICO]
    Lo que la Estrategia fabrica. Contiene instrucciones específicas
    para el driver del modelo (temperatura, stop_sequences, JSON mode).
    
    Esto aísla a la 'SenalAgente' de ensuciarse con detalles técnicos de la API.
    """
    mensajes_stack: List[MensajeNativo]
    parametros_api: Dict[str, Any] # { temperature: 0.7, top_k: 40, response_format: 'json' }
    alias_modelo_objetivo: str     # "GEMINI_FLASH_1.5", "OLLAMA_LLAMA3"

class ResultadoTecnicoLLM(BaseModel):
    """
    [NOTA SUCIA DE LA MÁQUINA]
    Respuesta cruda del driver del modelo antes de ser re-ensamblada.
    La estrategia toma esto, lo limpia, y actualiza 'SenalAgente.analisis'.
    """
    texto_generado: str
    tokens_input: int
    tokens_output: int
    data_raw: Any = None # Payload original del proveedor (para debug profundo)

class PayloadJoin(BaseModel):
    """
    Contrato para el endpoint de convergencia (Fan-In).
    Recibe múltiples señales (ramas paralelas) para unificarlas.
    """
    senales_entrantes: List[SenalAgente] = Field(..., min_items=1)
    estrategia: Literal['ESTRUCTURAL_COMPLETO'] = "ESTRUCTURAL_COMPLETO"

# 4. RESOLUCIÓN DE REFERENCIAS
# Importante: Actualiza las referencias recursivas (ForwardRef) ahora que todo está definido.
# Sin esto, Pydantic fallaría al intentar entender 'SenalAgenteRef'.
SenalAgente.update_forward_refs()
