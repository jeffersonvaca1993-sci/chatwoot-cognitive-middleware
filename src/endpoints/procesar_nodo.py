from fastapi import HTTPException
from src.core.protocolos import SenalAgente
from src.core.factory import obtener_clase_estrategia

async def endpoint_procesar_nodo(senal: SenalAgente) -> SenalAgente:
    """
    Lógica del endpoint /api/v1/procesar_nodo.
    
    Endpoint Simétrico Puro.
    Input: SenalAgente (Estado A)
    Output: SenalAgente (Estado B)
    """
    try:
        # 1. Identificar Estrategia (Routing)
        tipo_estrategia = senal.instruccion.tipo_estrategia
        ClaseEstrategia = obtener_clase_estrategia(tipo_estrategia)
        
        # 2. Instanciar Estrategia
        # La estrategia encapsula la lógica de Cliente/Payload
        estrategia = ClaseEstrategia()
        
        # 3. Ejecución Simétrica (Senal -> Senal)
        # Toda la complejidad técnica (Payloads, APIs) ocurre dentro de esta llamada.
        senal_procesada = await estrategia.ejecutar_simetrico(senal)
        
        return senal_procesada

    except ValueError as e:
        # Error de negocio (Estrategia no encontrada, etc)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Error técnico no controlado
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del nodo: {str(e)}")
