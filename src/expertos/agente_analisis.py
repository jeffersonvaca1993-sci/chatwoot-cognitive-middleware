# src/expertos/agente_analisis.py
from src.expertos.base import EstrategiaBase
from src.core.protocolos import SenalAgente, PayloadTecnicoLLM, MensajeNativo
from src.clientes_llm.gemini import ClienteGemini

class ExpertoAnalisisHechos(EstrategiaBase):

    def _configurar_cliente(self):
        return ClienteGemini()

    def _fabricar_payload(self, senal: SenalAgente) -> PayloadTecnicoLLM:
        # 1. Extraer datos de la Senal
        mensaje = senal.entrada.mensaje_texto
        
        # 2. Construir Prompt (Lógica única de este experto)
        prompt_sistema = "Eres un analista de hechos. Extrae entidades y fechas."
        
        # 3. Retornar el sobre técnico (Sin ejecutar nada todavía)
        return PayloadTecnicoLLM(
            mensajes_stack=[
                MensajeNativo(rol="system", contenido=prompt_sistema),
                MensajeNativo(rol="user", contenido=mensaje)
            ],
            parametros_api={"temperature": 0.2}, # Precisión alta
            alias_modelo_objetivo="GEMINI_FLASH"
        )
    
    # NOTA: No necesita implementar 'ejecutar_simetrico' ni '_ensamblar_salida'.
    # Ya los heredó gratis.
