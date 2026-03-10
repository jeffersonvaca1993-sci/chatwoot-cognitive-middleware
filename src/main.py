# src/main.py
from fastapi import FastAPI, Request, Header
from src.core.protocolos import SenalAgente, PayloadJoin
from src.database.session import init_db
from src.config import settings
from src.observadores import activar_interceptor_stdout
import os

# Importar lógica de endpoints
from src.endpoints.procesar_nodo import endpoint_procesar_nodo
from src.endpoints.health import endpoint_health
from src.endpoints.webhook_chatwoot import endpoint_webhook_chatwoot
from src.endpoints.unificar_ramas import endpoint_unificar_ramas
from src.endpoints.finalizar_procesamiento import endpoint_finalizar_procesamiento
from src.endpoints.verificar_cola import endpoint_verificar_y_acumular_cola
from src.endpoints.sintetizar_y_finalizar import endpoint_sintetizar_y_finalizar

app = FastAPI(title="MoE System API", version="1.0.0")

# Cargar configuración
config = settings

@app.on_event("startup")
def on_startup():
    """Inicialización de la aplicación."""
    # Activar interceptor de stdout para capturar todos los print()
    activar_interceptor_stdout()
    
    # Inicializar base de datos
    init_db()
    
    print("🚀 Aplicación iniciada correctamente")

@app.post("/api/v1/procesar_nodo", response_model=SenalAgente)
async def procesar_nodo(senal: SenalAgente) -> SenalAgente:
    """
    Endpoint Simétrico Puro.
    Input: SenalAgente (Estado A)
    Output: SenalAgente (Estado B)
    """
    return await endpoint_procesar_nodo(senal)

@app.get("/health")
def health_check():
    return endpoint_health()

@app.post("/api/v1/webhooks/chatwoot")
async def webhook_chatwoot(
    request: Request,
    x_chatwoot_signature: str = Header(None, alias="X-Chatwoot-Signature")
):
    """
    Endpoint asimétrico para recibir eventos de Chatwoot.
    """
    return await endpoint_webhook_chatwoot(request, x_chatwoot_signature)

@app.post("/api/v1/herramientas/join", response_model=SenalAgente)
async def unificar_ramas(payload: PayloadJoin) -> SenalAgente:
    """
    Endpoint de convergencia (Fan-In).
    """
    return await endpoint_unificar_ramas(payload)

@app.post("/api/v1/procesamiento/finalizar")
async def finalizar_procesamiento(request: Request):
    """
    Endpoint consolidado que ejecuta todos los pasos finales en una sola llamada.
    """
    return await endpoint_finalizar_procesamiento(request)

@app.post("/api/v1/cola/verificar_y_acumular")
async def verificar_y_acumular_cola(request: Request):
    """
    Endpoint crítico para el patrón de acumulación conversacional.
    """
    return await endpoint_verificar_y_acumular_cola(request)

@app.post("/api/v1/procesamiento/sintetizar_y_finalizar")
async def sintetizar_y_finalizar(request: Request):
    """
    Endpoint ultra-consolidado que ejecuta síntesis y finalización.
    """
    return await endpoint_sintetizar_y_finalizar(request)
