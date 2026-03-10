# src/expertos/agente_resumen.py
from src.expertos.base import EstrategiaBase
from src.core.protocolos import SenalAgente, PayloadTecnicoLLM, MensajeNativo

class ExpertoResumen(EstrategiaBase):
    
    def _fabricar_payload(self, senal: SenalAgente) -> PayloadTecnicoLLM:
        # Solo se preocupa de crear el prompt correcto
        texto_usuario = senal.entrada.mensaje_texto
        
        return PayloadTecnicoLLM(
            mensajes_stack=[
                MensajeNativo(rol="system", contenido="Eres un experto en resumir textos."),
                MensajeNativo(rol="user", contenido=f"Resume esto: {texto_usuario}")
            ],
            parametros_api={"temperature": 0.5},
            alias_modelo_objetivo="gemini-1.5-flash" # Valor por defecto
        )
