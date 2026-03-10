"""
Ejemplos de uso de los observadores.

Este archivo muestra cómo usar el logger y el observador de LLMs.
"""

from src.observadores import get_logger, get_observador_llm


# =============================================================================
# EJEMPLO 1: Logger de Eventos
# =============================================================================

def ejemplo_logger():
    """Ejemplo de uso del logger."""
    logger = get_logger()
    
    # Registrar un error
    logger.error(
        "Falló la conexión a la base de datos",
        contexto={
            "host": "localhost",
            "puerto": 5432,
            "intentos": 3,
            "error_original": "Connection refused"
        }
    )
    
    # Registrar una advertencia
    logger.warning(
        "Cliente con lock ocupado, mensaje encolado",
        contexto={
            "id_cliente": 789,
            "mensajes_en_cola": 2,
            "tiempo_lock": "45s"
        }
    )
    
    # Info y debug NO se registran en desarrollo
    logger.info("Esto no se guardará")  # No hace nada
    logger.debug("Esto tampoco")  # No hace nada


# =============================================================================
# EJEMPLO 2: Observador de LLMs
# =============================================================================

def ejemplo_observador_llm():
    """Ejemplo de uso del observador de LLMs."""
    observador = get_observador_llm()
    
    # Registrar una llamada exitosa
    observador.registrar_llamada(
        modelo="gpt-4",
        prompt="Analiza el siguiente caso legal: ...",
        respuesta="Basándome en el análisis legal...",
        tokens_prompt=150,
        tokens_respuesta=300,
        tokens_totales=450,
        latencia_ms=1250.5,
        costo_estimado=0.0135,
        metadata={
            "tipo_estrategia": "ANALISIS_LEGAL",
            "id_cliente": 789,
            "id_traza": "msg-123"
        }
    )
    
    # Registrar una llamada con error
    observador.registrar_llamada(
        modelo="claude-3-opus",
        prompt="Genera un resumen de...",
        respuesta="",
        tokens_prompt=200,
        tokens_respuesta=0,
        tokens_totales=200,
        latencia_ms=500.0,
        error="Rate limit exceeded. Retry after 60s",
        metadata={
            "tipo_estrategia": "SINTETIZADOR_FINAL",
            "id_cliente": 789
        }
    )
    
    # Registrar una traza completa
    observador.registrar_trace(
        trace_id="trace-abc-123",
        nombre="moe_conversation_processing",
        input_data={"mensaje": "Hola, necesito ayuda legal"},
        output_data={"respuesta": "¡Hola! Claro, ¿en qué puedo ayudarte?"},
        metadata={
            "id_cliente": 789,
            "conversation_id": 456,
            "tokens_totales": 1500,
            "expertos_consultados": ["legal", "financiero", "rag"]
        }
    )
    
    # Obtener estadísticas
    stats = observador.get_estadisticas()
    print(f"Total de llamadas: {stats['total_llamadas']}")
    print(f"Archivo de log: {stats['archivo_log']}")


# =============================================================================
# EJEMPLO 3: Uso en Endpoints de FastAPI
# =============================================================================

def ejemplo_uso_en_endpoint():
    """Ejemplo de cómo usar en un endpoint."""
    from fastapi import HTTPException
    
    logger = get_logger()
    observador = get_observador_llm()
    
    try:
        # Simular procesamiento
        id_cliente = 789
        
        # Llamar a LLM
        import time
        start = time.time()
        
        # ... llamada al LLM ...
        prompt = "Analiza este caso..."
        respuesta = "Análisis completo..."
        
        latencia = (time.time() - start) * 1000
        
        # Registrar la llamada
        observador.registrar_llamada(
            modelo="gpt-4",
            prompt=prompt,
            respuesta=respuesta,
            tokens_prompt=100,
            tokens_respuesta=200,
            tokens_totales=300,
            latencia_ms=latencia,
            metadata={"id_cliente": id_cliente}
        )
        
    except Exception as e:
        # Registrar el error
        logger.error(
            f"Error procesando cliente {id_cliente}",
            contexto={
                "error": str(e),
                "tipo": type(e).__name__
            }
        )
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# EJEMPLO 4: Migración Futura a Langfuse
# =============================================================================

"""
Cuando migres a Langfuse, solo necesitas cambiar la implementación interna:

# En logger.py:
class Logger:
    def __init__(self):
        # Cambiar de archivos .txt a Langfuse
        from langfuse import Langfuse
        self.langfuse = Langfuse()
    
    def error(self, mensaje, contexto=None):
        # Cambiar de .txt a Langfuse
        self.langfuse.log(level="error", message=mensaje, metadata=contexto)

# En observador_llm.py:
class ObservadorLLM:
    def __init__(self):
        from langfuse import Langfuse
        self.langfuse = Langfuse()
    
    def registrar_llamada(self, ...):
        self.langfuse.generation(
            model=modelo,
            input=prompt,
            output=respuesta,
            usage={"prompt_tokens": tokens_prompt, ...}
        )

El código que usa los observadores NO CAMBIA.
Solo cambias la implementación interna de Logger y ObservadorLLM.
"""


if __name__ == "__main__":
    print("Ejecutando ejemplos de observadores...\n")
    
    print("1. Logger de eventos")
    ejemplo_logger()
    print("   ✅ Logs guardados\n")
    
    print("2. Observador de LLMs")
    ejemplo_observador_llm()
    print("   ✅ Trazas guardadas\n")
    
    print("Revisa los archivos en src/observadores/logs/")
