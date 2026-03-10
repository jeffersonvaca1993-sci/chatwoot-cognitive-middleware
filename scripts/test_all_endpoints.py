import requests
import json
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_result(name, response):
    status = "✅" if response.status_code == 200 else "❌"
    print(f"{status} {name}: {response.status_code} - {response.elapsed.total_seconds()}s")
    if response.status_code != 200:
        print(f"   Response: {response.text}")

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/health")
        print_result("Health Check", r)
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")

def get_dummy_senal():
    return {
        "meta": {
            "id_traza": str(uuid.uuid4()),
            "timestamp_creacion": datetime.now().isoformat(),
            "origen": "test_script",
            "tokens_acumulados": 0
        },
        "instruccion": {
            "tipo_estrategia": "ANALISIS_DEFAULT",
            "configuracion_negocio": {
                "id_cliente_interno": 1,
                "activos_nuevos": []
            }
        },
        "historial_chat": [
            {"rol": "user", "contenido": "Hola, quiero probar la API"}
        ],
        "contexto": [],
        "entrada": {
            "mensaje_texto": "Hola, quiero probar la API",
            "referencias_archivos": []
        },
        "analisis": None
    }

def test_procesar_nodo():
    senal = get_dummy_senal()
    try:
        r = requests.post(f"{BASE_URL}/api/v1/procesar_nodo", json=senal)
        print_result("Procesar Nodo", r)
    except Exception as e:
        print(f"❌ Procesar Nodo Failed: {e}")

def test_join():
    senal1 = get_dummy_senal()
    senal2 = get_dummy_senal()
    payload = {
        "senales_entrantes": [senal1, senal2],
        "estrategia": "ESTRUCTURAL_COMPLETO"
    }
    try:
        r = requests.post(f"{BASE_URL}/api/v1/herramientas/join", json=payload)
        print_result("Join (Fan-In)", r)
    except Exception as e:
        print(f"❌ Join Failed: {e}")

def test_finalizar():
    senal = get_dummy_senal()
    # Add dummy analysis result
    senal["analisis"] = {
        "intencion_detectada": "TEST_API",
        "respuesta_sugerida": "Esta es una respuesta de prueba.",
        "accion_sugerida": "RESPONDER_TEXTO",
        "razonamiento": "Test script execution"
    }
    
    payload = {
        "senal_final": senal,
        "metadata_chatwoot": {
            "account_id": 1,
            "conversation_id": 1,
            "message_id": 1
        }
    }
    try:
        r = requests.post(f"{BASE_URL}/api/v1/procesamiento/finalizar", json=payload)
        print_result("Finalizar Procesamiento", r)
    except Exception as e:
        print(f"❌ Finalizar Failed: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando pruebas de endpoints API...")
    test_health()
    test_procesar_nodo()
    test_join()
    test_finalizar()
    print("🏁 Pruebas finalizadas.")
