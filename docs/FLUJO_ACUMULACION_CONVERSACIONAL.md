# Flujo MoE con Acumulación Conversacional

## 🎯 Arquitectura Mejorada

Se ha implementado un **patrón de acumulación conversacional** que permite procesar mensajes fragmentados del usuario como una sola conversación coherente.

---

## 🔄 Flujo Completo con Loop

```
┌─────────────────────────────────────────────────────────────────┐
│ USUARIO: "Hola"                                                 │
│ USUARIO: "Quiero una consulta legal"  (encolado)               │
│ USUARIO: "Sobre residencia de mi marido" (encolado)            │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 1. WEBHOOK CHATWOOT → FastAPI                                  │
│    - Validación de seguridad                                   │
│    - Expropiación de datos (guardar en DB)                     │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. ORQUESTADOR CONVERSACIONAL                                  │
│    ┌──────────────────────────────────────────────────────┐    │
│    │ ¿Lock disponible?                                    │    │
│    │  ├─ NO → Encolar mensaje en Redis                    │    │
│    │  └─ SÍ → Adquirir lock y continuar                   │    │
│    └──────────────────────────────────────────────────────┘    │
│    - Generar SenalAgente inicial                               │
│    - Recuperar historial (últimos 10 mensajes)                 │
│    - Recuperar contexto del cliente                            │
│    - Disparar workflow de Kestra                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. KESTRA - LOOP DE PROCESAMIENTO                              │
│                                                                 │
│  ╔═══════════════════════════════════════════════════════╗     │
│  ║ INICIO DEL LOOP                                       ║     │
│  ╚═══════════════════════════════════════════════════════╝     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 1: Router Inteligente                           │     │
│  │ - Analiza intención del mensaje                      │     │
│  │ - Decide qué expertos invocar                        │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 2: Fan-Out (Procesamiento Paralelo)            │     │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐     │     │
│  │ │ Experto     │ │ Experto     │ │ Experto     │     │     │
│  │ │ Legal       │ │ Financiero  │ │ RAG         │     │     │
│  │ └─────────────┘ └─────────────┘ └─────────────┘     │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 3: Fan-In (Unificación Estructural)            │     │
│  │ - Combina resultados de todos los expertos          │     │
│  │ - Preserva razonamiento completo                    │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 4: Síntesis Parcial                            │     │
│  │ - Genera respuesta intermedia                        │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 4.5: VERIFICAR COLA ⭐ (CRÍTICO)                │     │
│  │                                                       │     │
│  │ Endpoint: /api/v1/cola/verificar_y_acumular          │     │
│  │                                                       │     │
│  │ ¿Hay mensajes en la cola?                            │     │
│  │  ├─ SÍ:                                              │     │
│  │  │   1. Extraer todos los mensajes de la cola       │     │
│  │  │   2. Agregarlos al historial_chat                │     │
│  │  │   3. Actualizar entrada con último mensaje       │     │
│  │  │   4. Retornar continue=true                       │     │
│  │  │   5. ↩️ VOLVER AL PASO 1 (loop)                   │     │
│  │  │                                                    │     │
│  │  └─ NO:                                              │     │
│  │      1. Retornar continue=false                      │     │
│  │      2. Continuar al paso 5 ↓                        │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ╔═══════════════════════════════════════════════════════╗     │
│  ║ FIN DEL LOOP (solo si cola vacía)                    ║     │
│  ╚═══════════════════════════════════════════════════════╝     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 5: Síntesis Final                              │     │
│  │ - Genera respuesta completa y coherente              │     │
│  │ - Considera todo el contexto acumulado               │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 6: Guardar en Base de Datos                    │     │
│  │ - Persiste transacción completa                      │     │
│  │ - Guarda razonamiento de todos los expertos         │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 7: Enviar Respuesta a Chatwoot                 │     │
│  │ - Responde al usuario con mensaje final             │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 8: Liberar Lock de Redis ⭐                     │     │
│  │ - Permite que nuevos mensajes se procesen           │     │
│  └───────────────────────────────────────────────────────┘     │
│    ↓                                                            │
│  ┌───────────────────────────────────────────────────────┐     │
│  │ PASO 9: Log en Langfuse                             │     │
│  │ - Auditoría completa                                 │     │
│  │ - Métricas de tokens y costos                        │     │
│  │ - Trazabilidad end-to-end                           │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Ejemplo de Caso de Uso

### **Escenario: Usuario envía mensajes fragmentados**

```
T=0s:  Usuario: "Hola"
       → Sistema adquiere lock
       → Procesa: Router → Expertos → Síntesis
       → Verifica cola: vacía
       → Responde: "¡Hola! ¿En qué puedo ayudarte?"
       → Libera lock

T=2s:  Usuario: "Quiero una consulta legal"
       → Sistema intenta adquirir lock: OCUPADO (procesando "Hola")
       → ENCOLA mensaje en Redis
       → Retorna: {"status": "encolado"}

T=4s:  Usuario: "Sobre residencia de mi marido"
       → Sistema intenta adquirir lock: OCUPADO
       → ENCOLA mensaje en Redis
       → Retorna: {"status": "encolado"}

T=5s:  Sistema termina de procesar "Hola"
       → Verifica cola: HAY 2 MENSAJES
       → Extrae: ["Quiero una consulta legal", "Sobre residencia de mi marido"]
       → Agrega al historial_chat
       → VUELVE AL PASO 1 (Router)
       
       Historial ahora:
       [
         {"rol": "user", "contenido": "Hola"},
         {"rol": "assistant", "contenido": "¡Hola! ¿En qué puedo ayudarte?"},
         {"rol": "user", "contenido": "Quiero una consulta legal"},
         {"rol": "user", "contenido": "Sobre residencia de mi marido"}
       ]
       
       → Router analiza TODO el contexto
       → Detecta: CONSULTA_LEGAL + RESIDENCIA
       → Invoca: Experto Legal + Experto RAG
       → Síntesis: "Entiendo que necesitas información sobre residencia..."
       → Verifica cola: vacía
       → Guarda en DB
       → Envía a Chatwoot
       → Libera lock
```

---

## 🔑 Componentes Clave

### **1. Endpoint: `/api/v1/cola/verificar_y_acumular`**

**Responsabilidad:** Verificar si hay mensajes encolados y acumularlos al historial.

**Input:**
```json
{
  "senal_actual": { /* SenalAgente con resultado parcial */ },
  "id_cliente": 123,
  "metadata_chatwoot": { /* metadata */ }
}
```

**Output (si hay cola):**
```json
{
  "continue": true,
  "senal_actualizada": { 
    /* SenalAgente con historial_chat enriquecido */ 
  },
  "mensajes_procesados": 2
}
```

**Output (si NO hay cola):**
```json
{
  "continue": false,
  "senal_actualizada": { /* sin cambios */ },
  "mensajes_procesados": 0
}
```

---

### **2. Endpoint: `/api/v1/cola/liberar_lock`**

**Responsabilidad:** Liberar el lock de Redis para permitir nuevos procesamientos.

**Input:**
```json
{
  "id_cliente": 123
}
```

**Output:**
```json
{
  "status": "liberado",
  "id_cliente": 123
}
```

---

### **3. Flujo de Kestra con Condicional**

**Paso 4.6: Decisión de Loop**

```yaml
- id: 4_6_decision_loop
  type: io.kestra.plugin.core.flow.If
  condition: "{{ outputs['4_5_verificar_y_acumular_cola'].body.continue == true }}"
  then:
    # HAY MÁS MENSAJES - VOLVER AL PASO 1
    - id: reiniciar_con_mensajes_acumulados
      type: io.kestra.plugin.core.http.Request
      uri: "http://moe_api:8000/api/v1/procesar_nodo"
      # ... (vuelve a invocar router con historial actualizado)
  else:
    # NO HAY MÁS MENSAJES - CONTINUAR CON GUARDADO
    - id: continuar_sin_loop
      type: io.kestra.plugin.core.log.Log
      message: "✅ Cola vacía. Procediendo a finalizar."
```

---

## 🎯 Ventajas del Patrón

### **1. Contexto Completo**
✅ El sistema procesa todos los mensajes fragmentados como una sola conversación  
✅ El router ve el contexto completo y puede tomar mejores decisiones  
✅ Los expertos tienen acceso a toda la información

### **2. Eficiencia**
✅ No se pierde tiempo procesando mensajes incompletos  
✅ Se reduce el número de llamadas a LLMs  
✅ Se optimiza el uso de tokens

### **3. Mejor Experiencia de Usuario**
✅ Respuestas más coherentes y contextuales  
✅ No hay respuestas prematuras a mensajes incompletos  
✅ El sistema "espera" a que el usuario termine de escribir

### **4. Robustez**
✅ No se pierden mensajes (se encolan)  
✅ No hay condiciones de carrera (locks distribuidos)  
✅ El lock se libera siempre (incluso si hay errores)

---

## 📊 Métricas y Observabilidad

### **Langfuse Integration**

Cada ejecución completa se registra en Langfuse con:

```json
{
  "id": "uuid-traza",
  "name": "moe_conversation_processing",
  "userId": "123",
  "metadata": {
    "conversation_id": "456",
    "intencion": "CONSULTA_LEGAL_RESIDENCIA",
    "expertos_consultados": ["legal", "financiero", "rag", "sintetizador"],
    "tokens_totales": 2500,
    "modelo": "gemini-1.5-pro",
    "mensajes_acumulados": 2,
    "loops_ejecutados": 1
  },
  "input": "Hola\nQuiero una consulta legal\nSobre residencia de mi marido",
  "output": "Entiendo que necesitas información sobre residencia..."
}
```

---

## 🔧 Configuración Necesaria

### **Variables de Entorno**

```bash
# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Kestra
KESTRA_URL=http://moe_kestra:8080

# Langfuse
LANGFUSE_API_URL=https://cloud.langfuse.com
LANGFUSE_API_KEY=tu_public_key
LANGFUSE_SECRET_KEY=tu_secret_key
```

### **Secrets en Kestra**

Configurar en Kestra UI:
- `CHATWOOT_API_URL`
- `CHATWOOT_API_TOKEN`
- `LANGFUSE_API_URL`
- `LANGFUSE_API_KEY`

---

## 🚨 Consideraciones Importantes

### **Timeout del Lock**
- **Valor actual:** 300 segundos (5 minutos)
- **Riesgo:** Si el procesamiento tarda más, el lock expira y puede haber duplicación
- **Solución:** Monitorear tiempos de procesamiento y ajustar timeout

### **Límite de Cola**
- **Actual:** Sin límite
- **Riesgo:** Un usuario malicioso podría llenar la cola
- **Solución:** Implementar límite máximo (ej: 10 mensajes por cliente)

### **Límite de Loops**
- **Actual:** Sin límite
- **Riesgo:** Loop infinito si hay un bug
- **Solución:** Implementar contador de loops máximo (ej: 5 loops)

---

## ✅ Testing

### **Caso 1: Mensaje Simple**
```
Input: "Hola"
Expected: Respuesta inmediata, sin loops
```

### **Caso 2: Mensajes Fragmentados**
```
Input: "Hola" + "Quiero consulta legal" + "Sobre residencia"
Expected: 1 loop, respuesta consolidada
```

### **Caso 3: Lock Ocupado**
```
Input: 2 mensajes simultáneos del mismo cliente
Expected: Uno procesa, otro se encola
```

### **Caso 4: Cola Vacía**
```
Input: Mensaje único sin cola
Expected: Procesa y finaliza sin loops
```

---

**Fecha de Implementación:** 2025-11-24  
**Versión:** 3.0.0  
**Estado:** ✅ Arquitectura completa implementada con patrón de acumulación conversacional
