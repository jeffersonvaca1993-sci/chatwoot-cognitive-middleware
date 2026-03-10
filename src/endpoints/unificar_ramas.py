from fastapi import HTTPException
from src.core.protocolos import SenalAgente, PayloadJoin
from src.core.unificador import UnificadorEstructural

async def endpoint_unificar_ramas(payload: PayloadJoin) -> SenalAgente:
    """
    Lógica del endpoint /api/v1/herramientas/join.
    
    Endpoint de convergencia (Fan-In).
    """
    try:
        return UnificadorEstructural.unificar(payload.senales_entrantes)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error crítico en Join: {e}")
        raise HTTPException(status_code=500, detail="Error interno al unificar señales.")
