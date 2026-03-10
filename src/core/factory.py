# src/core/factory.py
from typing import Type
from src.expertos.base import EstrategiaBase
from src.expertos.agente_resumen import ExpertoResumen
from src.expertos.agente_analisis import ExpertoAnalisisHechos

class EstrategiaDefault(EstrategiaBase):
    """Estrategia por defecto si no se encuentra la solicitada."""
    def _fabricar_payload(self, senal):
        # Implementación mínima
        from src.core.protocolos import PayloadTecnicoLLM, MensajeNativo
        return PayloadTecnicoLLM(
            mensajes_stack=[MensajeNativo(rol="user", contenido=senal.entrada.mensaje_texto)],
            parametros_api={},
            alias_modelo_objetivo="default"
        )

def obtener_clase_estrategia(tipo_estrategia: str) -> Type[EstrategiaBase]:
    """
    Retorna la CLASE de la estrategia (no la instancia).
    """
    # Mapeo de estrategias
    mapa_estrategias = {
        "ANALISIS_DEFAULT": EstrategiaDefault,
        "RESUMEN": ExpertoResumen,
        "ANALISIS_HECHOS": ExpertoAnalisisHechos,
    }
    
    clase = mapa_estrategias.get(tipo_estrategia)
    
    if not clase:
        # Fallback o error según configuración
        return EstrategiaDefault
        
    return clase
