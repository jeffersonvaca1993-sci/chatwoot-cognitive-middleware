# src/clientes_llm/base.py
from abc import ABC, abstractmethod
import os
from src.core.protocolos import PayloadTecnicoLLM, ResultadoTecnicoLLM

class ClienteLLMBase(ABC):
    """
    PLANTILLA ADAPTADORA (The Universal Adapter).
    Su trabajo es traducir nuestro 'Esperanto' técnico al idioma nativo del proveedor.
    """
    
    def __init__(self):
        # Carga configuraciones globales (Keys, Timeouts) desde variables de entorno
        self.api_key = self._cargar_api_key()
        self._inicializar_sdk()

    @abstractmethod
    def _cargar_api_key(self) -> str:
        """Cada cliente sabe qué variable de entorno buscar (GEMINI_KEY, OPENAI_KEY)."""
        pass

    @abstractmethod
    def _inicializar_sdk(self):
        """Configuración inicial de la librería externa."""
        pass

    @abstractmethod
    async def invocar_privado(self, payload: PayloadTecnicoLLM) -> ResultadoTecnicoLLM:
        """
        El único método público.
        Recibe la petición genérica y devuelve el resultado genérico.
        """
        pass

class ClienteSimulado(ClienteLLMBase):
    """Cliente para pruebas que no gasta tokens."""
    
    def _cargar_api_key(self) -> str:
        return "dummy_key"

    def _inicializar_sdk(self):
        pass

    async def invocar_privado(self, payload: PayloadTecnicoLLM) -> ResultadoTecnicoLLM:
        print(f"   [ClienteSimulado] Invocando modelo: {payload.alias_modelo_objetivo}")
        return ResultadoTecnicoLLM(
            texto_generado=f"Respuesta simulada para: {payload.mensajes_stack[-1].contenido[:20]}...",
            tokens_input=10,
            tokens_output=5,
            data_raw={"model_name": payload.alias_modelo_objetivo}
        )
