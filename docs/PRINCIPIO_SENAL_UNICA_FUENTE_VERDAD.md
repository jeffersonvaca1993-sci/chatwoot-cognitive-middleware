# Principio: SenalAgente como Única Fuente de Verdad

## 🎯 **Concepto**

**Toda la información necesaria para el procesamiento debe viajar dentro de la `SenalAgente`.**

No se deben pasar parámetros adicionales por separado. La señal es la **única fuente de verdad**.

---

## ✅ **Correcto: Todo en la Señal**

### **Flujo de Kestra**
```yaml
- id: verificar_cola
  body: |
    {
      "senal_actual": {{ outputs['procesar_expertos'].outputs.senal_procesada | json }}
    }
```

### **Endpoint de Python**
```python
@app.post("/api/v1/cola/verificar_y_acumular")
async def verificar_y_acumular_cola(request: Request):
    payload = await request.json()
    senal_actual = payload["senal_actual"]
    
    # Extraer TODO de la señal
    id_cliente = senal_actual["instruccion"]["configuracion_negocio"]["id_cliente_interno"]
    conversation_id = senal_actual["instruccion"]["configuracion_negocio"]["conversation_id"]
    expertos = senal_actual["instruccion"]["configuracion_negocio"]["expertos"]
    # ... etc
```

---

## ❌ **Incorrecto: Parámetros Separados**

### **Flujo de Kestra (MAL)**
```yaml
- id: verificar_cola
  body: |
    {
      "senal_actual": {{ ... }},
      "id_cliente": {{ inputs.senal_agente.instruccion.configuracion_negocio.id_cliente_interno }},  # ❌ REDUNDANTE
      "metadata_chatwoot": {{ inputs.metadata_chatwoot | json }}  # ❌ REDUNDANTE
    }
```

### **Endpoint de Python (MAL)**
```python
@app.post("/api/v1/cola/verificar_y_acumular")
async def verificar_y_acumular_cola(request: Request):
    payload = await request.json()
    senal_actual = payload["senal_actual"]
    id_cliente = payload["id_cliente"]  # ❌ REDUNDANTE
    metadata = payload["metadata_chatwoot"]  # ❌ REDUNDANTE
```

**Problemas:**
- ❌ Información duplicada
- ❌ Posible inconsistencia (¿qué pasa si `id_cliente` != `senal.id_cliente`?)
- ❌ Más complejo de mantener
- ❌ Rompe el principio de diseño

---

## 🏗️ **Estructura de la SenalAgente**

```python
{
  "meta": {
    "id_traza": "msg-123",
    "tokens_acumulados": 1500,
    "modelo_ultimo_paso": "gpt-4"
  },
  "instruccion": {
    "tipo_estrategia": "ROUTER_INICIAL",
    "configuracion_negocio": {
      # ✅ TODA LA METADATA AQUÍ
      "id_cliente_interno": 789,
      "conversation_id": 456,
      "account_id": 1,
      "message_id": "msg-123",
      "activos_nuevos": [101, 102],
      
      # Configuración de expertos
      "expertos": ["ANALISIS_LEGAL", "ANALISIS_FINANCIERO", "RAG_CONOCIMIENTO"],
      "ejecutar_router": true,
      "estrategia_sintesis": "SINTETIZADOR_PARCIAL",
      "config_sintesis": {"formato_salida": "acumulativo"}
    }
  },
  "historial_chat": [...],
  "contexto": [...],
  "entrada": {...},
  "analisis": {...}
}
```

---

## 📋 **Reglas de Diseño**

### **1. La Señal es Autosuficiente**
✅ Cualquier endpoint debe poder procesar la señal con solo recibirla  
✅ No debe necesitar parámetros adicionales del contexto externo  
✅ Toda la información está dentro de la señal

### **2. Inmutabilidad de Metadata**
✅ `id_cliente`, `conversation_id`, etc. **no cambian** durante el procesamiento  
✅ Se establecen al inicio (en el Orquestador) y viajan con la señal  
✅ Todos los pasos usan la misma metadata

### **3. Enriquecimiento Progresivo**
✅ La señal se **enriquece** en cada paso  
✅ Se agrega contexto, análisis, historial  
✅ Pero la metadata base permanece constante

---

## 🔄 **Ejemplo de Flujo**

### **Paso 1: Orquestador (Python)**
```python
# Crear señal inicial con TODA la metadata
senal = SenalAgente(
    meta=Meta(...),
    instruccion=Instruccion(
        configuracion_negocio={
            "id_cliente_interno": 789,
            "conversation_id": 456,
            "account_id": 1,
            "expertos": ["LEGAL", "FINANCIERO", "RAG"],
            # ... todo lo necesario
        }
    ),
    # ...
)

# Enviar a Kestra
kestra.trigger_workflow(senal_agente=senal.dict())
```

### **Paso 2: Kestra → Subflujo**
```yaml
- id: procesar_expertos
  inputs:
    senal_entrada: "{{ inputs.senal_agente }}"  # ✅ Solo la señal
```

### **Paso 3: Subflujo → Expertos**
```yaml
- id: experto_legal
  body: |
    {
      "meta": {{ inputs.senal_entrada.meta | json }},
      "instruccion": {
        "tipo_estrategia": {{ inputs.senal_entrada.instruccion.configuracion_negocio.expertos[0] | json }},
        # ✅ Lee de la señal
      }
    }
```

### **Paso 4: Verificar Cola**
```yaml
- id: verificar_cola
  body: |
    {
      "senal_actual": {{ outputs['procesar_expertos'].outputs.senal_procesada | json }}
      # ✅ Solo la señal, nada más
    }
```

### **Paso 5: Endpoint Python**
```python
@app.post("/api/v1/cola/verificar_y_acumular")
async def verificar_y_acumular_cola(request: Request):
    senal = request.json()["senal_actual"]
    
    # ✅ Extraer TODO de la señal
    id_cliente = senal["instruccion"]["configuracion_negocio"]["id_cliente_interno"]
    
    # Usar para Redis
    queue_key = f"queue:cliente:{id_cliente}"
    lock_key = f"lock:cliente:{id_cliente}"
```

---

## 🎯 **Ventajas de Este Diseño**

### **1. Consistencia Garantizada**
✅ No puede haber inconsistencia entre parámetros  
✅ Una sola fuente de verdad  
✅ Menos bugs

### **2. Simplicidad**
✅ Menos parámetros en cada llamada  
✅ Código más limpio  
✅ Más fácil de entender

### **3. Trazabilidad**
✅ Toda la información está en un solo objeto  
✅ Fácil de loggear y debuggear  
✅ Fácil de serializar/deserializar

### **4. Reutilización**
✅ Los endpoints son más genéricos  
✅ No dependen de parámetros específicos del contexto  
✅ Más fácil de reutilizar en otros flujos

### **5. Testing**
✅ Solo necesitas crear una señal válida  
✅ No necesitas mockear múltiples parámetros  
✅ Tests más simples

---

## 📊 **Comparación**

| Aspecto | Con Parámetros Separados | Solo SenalAgente |
|---------|-------------------------|------------------|
| **Parámetros por endpoint** | 3-5 | 1 |
| **Riesgo de inconsistencia** | Alto | Ninguno |
| **Complejidad de código** | Alta | Baja |
| **Facilidad de testing** | Difícil | Fácil |
| **Reutilización** | Limitada | Alta |
| **Mantenibilidad** | Difícil | Fácil |

---

## ✅ **Checklist de Validación**

Antes de crear un nuevo endpoint, pregúntate:

- [ ] ¿Estoy pasando parámetros que ya están en la señal?
- [ ] ¿Podría extraer esta información de `senal.instruccion.configuracion_negocio`?
- [ ] ¿Estoy duplicando información?
- [ ] ¿El endpoint podría funcionar solo con la señal?

Si respondes "sí" a cualquiera, **refactoriza para usar solo la señal**.

---

## 🚀 **Implementación Actual**

### **Endpoints que Respetan el Principio:**
✅ `/api/v1/procesar_nodo` - Solo recibe SenalAgente  
✅ `/api/v1/herramientas/join` - Solo recibe señales  
✅ `/api/v1/cola/verificar_y_acumular` - Solo recibe señal (CORREGIDO)  
✅ `/api/v1/procesamiento/sintetizar_y_finalizar` - Solo recibe señal

### **Subflujos que Respetan el Principio:**
✅ `subflujo_procesamiento_expertos` - Solo recibe `senal_entrada`  
✅ Flujo principal - Pasa solo señales entre pasos

---

**Fecha de Implementación:** 2025-11-24  
**Versión:** 5.0.0  
**Principio:** SenalAgente como Única Fuente de Verdad ✅
