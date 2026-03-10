# Observadores - Sistema de Logging y Observabilidad

Sistema de observabilidad para desarrollo que será reemplazado por Langfuse en producción.

---

## 📁 **Estructura**

```
src/observadores/
├── __init__.py                 # Exports principales
├── logger.py                   # Logger de eventos generales
├── observador_llm.py           # Observador de llamadas a LLMs
├── interceptor_stdout.py       # Interceptor de print() ⭐ NUEVO
├── ejemplos_uso.py             # Ejemplos de uso
└── logs/                       # Archivos de log (ignorados en Git)
    ├── .gitignore              # Ignora *.txt
    ├── eventos/                # Logs de eventos generales
    │   ├── .gitkeep
    │   └── log_YYYYMMDD_HHMMSS.txt
    ├── llm/                    # Logs de llamadas a LLMs
    │   ├── .gitkeep
    │   └── llm_trace_YYYYMMDD_HHMMSS.txt
    └── stdout/                 # Logs de print() capturados ⭐ NUEVO
        ├── .gitkeep
        └── stdout_YYYYMMDD_HHMMSS.txt
```

---

## 🎯 **Propósito**

### **Desarrollo:**
- Guardar logs en archivos `.txt` planos
- Formato legible para humanos
- Un archivo por ejecución (cada vez que levantas Docker)
- Solo errores y advertencias en el logger
- Todas las llamadas a LLMs en el observador
- **⭐ NUEVO:** Captura automática de todos los `print()` sin cambiar código

### **Producción (Futuro):**
- Migrar a Langfuse
- Solo cambiar implementación interna
- El código que usa los observadores NO cambia

---

## 🔍 **Interceptor de Stdout (⭐ NUEVO)**

### **¿Qué hace?**
Captura **automáticamente** todos los `print()` del sistema y los guarda en archivos de log, **sin necesidad de cambiar el código existente**.

### **Activación Automática:**
```python
# En main.py (ya configurado)
from src.observadores import activar_interceptor_stdout

@app.on_event("startup")
def on_startup():
    activar_interceptor_stdout()  # ← Activa captura automática
    init_db()
```

### **Resultado:**
```python
# Cualquier print() en cualquier parte del código
print("🚀 Procesando cliente 789")
print(f"✅ Transacción guardada: ID {id_transaccion}")
print(f"❌ Error: {error}")

# Se captura automáticamente en:
# src/observadores/logs/stdout/stdout_20251124_230000.txt
```

### **Formato del Log:**
```
================================================================================
CAPTURA DE STDOUT - ChatGravity MoE
Iniciado: 2025-11-24 23:00:00
================================================================================

[2025-11-24 23:00:01.123] ✅ Interceptor de stdout activado
[2025-11-24 23:00:01.456] 🚀 Aplicación iniciada correctamente
[2025-11-24 23:01:15.789] 🚀 Procesando cliente 789
[2025-11-24 23:01:16.012] ✅ Transacción guardada: ID 123
[2025-11-24 23:02:30.345] ❌ Error: Connection refused
```

### **Ventajas:**
✅ **Cero cambios en código existente** - Todos los `print()` se capturan automáticamente  
✅ **Mantiene salida en consola** - Sigue viendo los logs en tiempo real  
✅ **Persistencia** - Todo queda guardado en archivos  
✅ **Timestamp automático** - Cada línea tiene fecha y hora  
✅ **Un archivo por ejecución** - Fácil de organizar

---

## 📝 **Logger de Eventos**

### **Uso:**
```python
from src.observadores import get_logger

logger = get_logger()

# Registrar error
logger.error(
    "Falló la conexión a la base de datos",
    contexto={
        "host": "localhost",
        "puerto": 5432,
        "error": "Connection refused"
    }
)

# Registrar advertencia
logger.warning(
    "Cliente con lock ocupado",
    contexto={"id_cliente": 789}
)
```

### **Formato del Log:**
```
================================================================================
LOG DE EVENTOS - ChatGravity MoE
Iniciado: 2025-11-24 23:00:00
Nivel: ERRORES Y ADVERTENCIAS
================================================================================

[2025-11-24 23:01:15] ❌ ERROR
Falló la conexión a la base de datos
Contexto:
  - host: localhost
  - puerto: 5432
  - error: Connection refused
--------------------------------------------------------------------------------

[2025-11-24 23:02:30] ⚠️ ADVERTENCIA
Cliente con lock ocupado
Contexto:
  - id_cliente: 789
--------------------------------------------------------------------------------
```

---

## 🤖 **Observador de LLMs**

### **Uso:**
```python
from src.observadores import get_observador_llm

observador = get_observador_llm()

# Registrar llamada a LLM
observador.registrar_llamada(
    modelo="gpt-4",
    prompt="Analiza el siguiente caso legal: ...",
    respuesta="Basándome en el análisis...",
    tokens_prompt=150,
    tokens_respuesta=300,
    tokens_totales=450,
    latencia_ms=1250.5,
    costo_estimado=0.0135,
    metadata={
        "tipo_estrategia": "ANALISIS_LEGAL",
        "id_cliente": 789
    }
)

# Registrar traza completa
observador.registrar_trace(
    trace_id="trace-abc-123",
    nombre="moe_conversation_processing",
    input_data={"mensaje": "Hola"},
    output_data={"respuesta": "¡Hola!"},
    metadata={"id_cliente": 789}
)
```

### **Formato del Log:**
```
================================================================================
LLAMADA #1
Timestamp: 2025-11-24 23:01:15.123
================================================================================

📊 MODELO
  Nombre: gpt-4
  Latencia: 1250.50 ms
  Costo estimado: $0.013500 USD

🔢 TOKENS
  Prompt: 150
  Respuesta: 300
  Total: 450

📋 METADATA
  tipo_estrategia: ANALISIS_LEGAL
  id_cliente: 789

📝 PROMPT
--------------------------------------------------------------------------------
Analiza el siguiente caso legal: ...
--------------------------------------------------------------------------------

✅ RESPUESTA
--------------------------------------------------------------------------------
Basándome en el análisis...
--------------------------------------------------------------------------------
```

---

## 🔄 **Migración a Langfuse**

Cuando estés listo para migrar a Langfuse:

### **1. Instalar Langfuse:**
```bash
pip install langfuse
```

### **2. Actualizar `logger.py`:**
```python
class Logger:
    def __init__(self):
        from langfuse import Langfuse
        self.langfuse = Langfuse()
    
    def error(self, mensaje, contexto=None):
        self.langfuse.log(
            level="error",
            message=mensaje,
            metadata=contexto
        )
```

### **3. Actualizar `observador_llm.py`:**
```python
class ObservadorLLM:
    def __init__(self):
        from langfuse import Langfuse
        self.langfuse = Langfuse()
    
    def registrar_llamada(self, modelo, prompt, respuesta, ...):
        self.langfuse.generation(
            model=modelo,
            input=prompt,
            output=respuesta,
            usage={
                "prompt_tokens": tokens_prompt,
                "completion_tokens": tokens_respuesta,
                "total_tokens": tokens_totales
            }
        )
```

### **4. El código que usa los observadores NO CAMBIA:**
```python
# Este código funciona igual con archivos .txt o con Langfuse
logger = get_logger()
logger.error("Error", contexto={...})

observador = get_observador_llm()
observador.registrar_llamada(...)
```

---

## 📊 **Características**

### **Logger:**
- ✅ Solo errores y advertencias
- ✅ Formato legible para humanos
- ✅ Un archivo por ejecución
- ✅ Timestamp en cada entrada
- ✅ Contexto opcional

### **Observador LLM:**
- ✅ Todas las llamadas a LLMs
- ✅ Prompt completo
- ✅ Respuesta completa
- ✅ Tokens detallados
- ✅ Latencia
- ✅ Costo estimado
- ✅ Metadata personalizada
- ✅ Manejo de errores

---

## 🗑️ **Limpieza de Logs**

Los archivos de log se crean con timestamp y debes eliminarlos manualmente:

```bash
# Eliminar logs de eventos
rm src/observadores/logs/eventos/*.txt

# Eliminar logs de LLMs
rm src/observadores/logs/llm/*.txt

# Eliminar todos los logs
rm src/observadores/logs/**/*.txt
```

---

## 🎓 **Ejemplos**

Ver `ejemplos_uso.py` para ejemplos completos de:
- Logger de eventos
- Observador de LLMs
- Uso en endpoints de FastAPI
- Migración a Langfuse

---

**Fecha de Creación:** 2025-11-24  
**Versión:** 1.0.0  
**Estado:** ✅ Listo para desarrollo
