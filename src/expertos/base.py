# src/expertos/base.py
from abc import ABC, abstractmethod
from src.core.protocolos import SenalAgente, PayloadTecnicoLLM, ResultadoTecnicoLLM, AnalisisCognitivo
from src.clientes_llm.base import ClienteLLMBase, ClienteSimulado

class EstrategiaBase(ABC):
    """
    EL MANUAL DE PROCEDIMIENTOS (Template Method).
    Define el esqueleto del algoritmo. Las subclases solo llenan los huecos.
    """

    def __init__(self):
        # Aquí inyectas el cliente (Gemini, Ollama, etc.)
        self.cliente = self._configurar_cliente()

    def _configurar_cliente(self) -> ClienteLLMBase:
        """
        Método hook para que las subclases elijan su cliente.
        Por defecto usa el simulado.
        """
        return ClienteSimulado()

    # --- PASOS ABSTRACTOS (Los que CADA experto debe definir) ---

    @abstractmethod
    def _fabricar_payload(self, senal: SenalAgente) -> PayloadTecnicoLLM:
        """
        LÓGICA DE NEGOCIO PURA.
        Aquí el experto decide el System Prompt, inyecta RAG y configura la temperatura.
        Convierte SenalAgente -> PayloadTecnico.
        """
        pass

    # --- PASOS CONCRETOS (Lógica compartida por defecto) ---

    def _ensamblar_salida(self, senal: SenalAgente, resultado: ResultadoTecnicoLLM) -> SenalAgente:
        """
        LÓGICA DE RE-ENSAMBLE (Reutilizable).
        Toma la respuesta cruda del LLM y la escribe en el contrato oficial.
        El 90% de los expertos usará esto tal cual.
        """
        if senal.analisis is None:
            senal.analisis = AnalisisCognitivo()
            
        # Mapeo estándar Texto -> Respuesta
        senal.analisis.respuesta_sugerida = resultado.texto_generado
        
        # Auditoría de costos
        senal.meta.tokens_acumulados += (resultado.tokens_input + resultado.tokens_output)
        # Safe access to data_raw
        model_name = "unknown"
        if resultado.data_raw and isinstance(resultado.data_raw, dict):
            model_name = resultado.data_raw.get("model_name", "unknown")
        senal.meta.modelo_ultimo_paso = model_name
        
        return senal

    # --- LA PLANTILLA MAESTRA (Flow Control) ---
    
    async def ejecutar_simetrico(self, senal: SenalAgente) -> SenalAgente:
        """
        EL METODO FINAL.
        Nadie lo sobreescribe. Garantiza la simetría del sistema.
        """
        # 1. Transformación (Negocio -> Técnico)
        # El experto define CÓMO se pide, pero la plantilla decide CUÁNDO.
        payload = self._fabricar_payload(senal)
        
        # 2. Ejecución (Rompimiento de simetría encapsulado)
        # Aquí ocurre la llamada a la API (Gemini/Ollama)
        resultado_raw = await self.cliente.invocar_privado(payload)
        
        # 3. Re-integración (Técnico -> Negocio)
        # Convertimos la respuesta técnica en formato de negocio.
        senal_actualizada = self._ensamblar_salida(senal, resultado_raw)
        
        return senal_actualizada
