# Arquitectura Modular con Subflujos Reutilizables

## 🎯 Objetivo

Crear una arquitectura modular donde el procesamiento de expertos (Router → Fan-Out → Fan-In) esté encapsulado en un **subflujo reutilizable** que puede ser invocado desde múltiples flujos principales con diferentes configuraciones.

---

## 🏗️ Arquitectura

### **Antes: Monolítico**
```
flujo_chatwoot.yaml (250 líneas)
├── Router
├── Fan-Out (3 expertos hardcodeados)
├── Fan-In
├── Síntesis Parcial
├── Verificar Cola
├── Loop
├── Síntesis Final
└── Finalización
```

### **Ahora: Modular**
```
flujo_chatwoot.yaml (180 líneas)
├── Llamar subflujo_procesamiento_expertos
├── Síntesis Parcial
├── Verificar Cola
├── Loop (llama subflujo nuevamente)
├── Síntesis Final
└── Finalización

subflujo_procesamiento_expertos.yaml (160 líneas)
├── Router (opcional)
├── Fan-Out (configurable)
└── Fan-In
```

---

## 📦 Subflujo Reutilizable

### **`subflujo_procesamiento_expertos.yaml`**

**Inputs:**
```yaml
inputs:
  - id: senal_entrada
    type: JSON
    description: "SenalAgente a procesar"
  
  - id: configuracion_expertos
    type: JSON
    description: "Qué expertos invocar"
    defaults:
      expertos:
        - ANALISIS_LEGAL
        - ANALISIS_FINANCIERO
        - RAG_CONOCIMIENTO
      ejecutar_router: true
```

**Outputs:**
```yaml
outputs:
  - id: senal_procesada
    type: JSON
    value: "{{ outputs['3_unificacion_resultados'].body }}"
```

**Características:**
- ✅ **Reutilizable**: Puede ser llamado desde cualquier flujo
- ✅ **Configurable**: Los expertos se pasan como parámetros
- ✅ **Modular**: Encapsula Router → Fan-Out → Fan-In
- ✅ **Router opcional**: Se puede deshabilitar si no se necesita

---

## 🔄 Uso del Subflujo

### **Llamada desde Flujo Principal**

```yaml
- id: 1_procesar_expertos
  type: io.kestra.plugin.core.flow.Subflow
  namespace: sci.vacasantana
  flowId: subflujo_procesamiento_expertos
  inputs:
    senal_entrada: "{{ inputs.senal_agente }}"
    configuracion_expertos:
      expertos:
        - ANALISIS_LEGAL
        - ANALISIS_FINANCIERO
        - RAG_CONOCIMIENTO
      ejecutar_router: true
  wait: true
  transmitFailed: true
```

**Parámetros:**
- `wait: true` → Espera a que termine el subflujo
- `transmitFailed: true` → Si falla el subflujo, falla el flujo principal
- `inputs` → Parámetros que se pasan al subflujo

---

## 🎨 Casos de Uso

### **Caso 1: Flujo Estándar (3 expertos)**
```yaml
configuracion_expertos:
  expertos:
    - ANALISIS_LEGAL
    - ANALISIS_FINANCIERO
    - RAG_CONOCIMIENTO
  ejecutar_router: true
```

### **Caso 2: Solo Análisis Legal**
```yaml
configuracion_expertos:
  expertos:
    - ANALISIS_LEGAL
    - ANALISIS_LEGAL  # Se puede repetir
    - ANALISIS_LEGAL
  ejecutar_router: false  # Sin router
```

### **Caso 3: Expertos Personalizados**
```yaml
configuracion_expertos:
  expertos:
    - ANALISIS_MEDICO
    - ANALISIS_PSICOLOGICO
    - RAG_SALUD
  ejecutar_router: true
```

### **Caso 4: Flujo Rápido (sin router)**
```yaml
configuracion_expertos:
  expertos:
    - RAG_CONOCIMIENTO
    - RAG_CONOCIMIENTO
    - RAG_CONOCIMIENTO
  ejecutar_router: false  # Más rápido
```

---

## 🔁 Loop con Subflujo

El loop ahora también usa el subflujo:

```yaml
- id: 4_decision_loop
  type: io.kestra.plugin.core.flow.If
  condition: "{{ outputs['3_verificar_y_acumular_cola'].body.continue == true }}"
  then:
    # VOLVER A LLAMAR AL SUBFLUJO con mensajes acumulados
    - id: reiniciar_con_mensajes_acumulados
      type: io.kestra.plugin.core.flow.Subflow
      namespace: sci.vacasantana
      flowId: subflujo_procesamiento_expertos
      inputs:
        senal_entrada: "{{ outputs['3_verificar_y_acumular_cola'].body.senal_actualizada }}"
        configuracion_expertos:
          expertos:
            - ANALISIS_LEGAL
            - ANALISIS_FINANCIERO
            - RAG_CONOCIMIENTO
          ejecutar_router: true
```

---

## 📊 Ventajas de la Modularidad

### **1. Reutilización de Código**
✅ El subflujo se puede usar en múltiples flujos principales  
✅ No hay duplicación de código  
✅ Cambios en el subflujo afectan a todos los flujos que lo usan

### **2. Flexibilidad**
✅ Diferentes flujos pueden usar diferentes expertos  
✅ Se puede deshabilitar el router si no se necesita  
✅ Fácil agregar nuevos expertos

### **3. Mantenibilidad**
✅ Código más limpio y organizado  
✅ Más fácil de entender  
✅ Más fácil de debuggear

### **4. Testing**
✅ Se puede testear el subflujo independientemente  
✅ Se puede testear el flujo principal con un subflujo mock  
✅ Mejor aislamiento de errores

---

## 🗂️ Estructura de Archivos

```
kestra/flows/
├── flujo_chatwoot.yaml                    # Flujo principal (180 líneas)
├── subflujo_procesamiento_expertos.yaml   # Subflujo reutilizable (160 líneas)
└── [futuros subflujos]
    ├── subflujo_analisis_medico.yaml
    ├── subflujo_analisis_legal.yaml
    └── subflujo_rag_especializado.yaml
```

---

## 🔧 Creación de Nuevos Subflujos

### **Ejemplo: Subflujo de Análisis Médico**

```yaml
id: subflujo_analisis_medico
namespace: sci.vacasantana

inputs:
  - id: senal_entrada
    type: JSON
  
  - id: especialidad
    type: STRING
    defaults: "GENERAL"

tasks:
  - id: analisis_sintomas
    type: io.kestra.plugin.core.http.Request
    uri: "http://moe_api:8000/api/v1/procesar_nodo"
    body: |
      {
        "instruccion": {
          "tipo_estrategia": "ANALISIS_MEDICO_{{ inputs.especialidad }}"
        },
        ...
      }
  
  - id: analisis_diagnostico
    type: io.kestra.plugin.core.http.Request
    ...
  
  - id: unificar
    type: io.kestra.plugin.core.http.Request
    uri: "http://moe_api:8000/api/v1/herramientas/join"
    ...

outputs:
  - id: diagnostico
    value: "{{ outputs['unificar'].body }}"
```

**Uso:**
```yaml
- id: diagnostico_medico
  type: io.kestra.plugin.core.flow.Subflow
  flowId: subflujo_analisis_medico
  inputs:
    senal_entrada: "{{ ... }}"
    especialidad: "CARDIOLOGIA"
```

---

## 📈 Comparación de Complejidad

| Métrica | Antes | Ahora | Mejora |
|---------|-------|-------|--------|
| **Líneas en flujo principal** | 250 | 180 | -28% |
| **Duplicación de código** | Alta | Ninguna | -100% |
| **Reutilización** | 0% | 100% | +100% |
| **Mantenibilidad** | Baja | Alta | +++++ |
| **Flexibilidad** | Baja | Alta | +++++ |

---

## 🎯 Flujos Futuros Posibles

Con esta arquitectura modular, es fácil crear nuevos flujos:

### **1. Flujo de Análisis de Documentos**
```yaml
id: flujo_analisis_documentos
tasks:
  - id: extraer_texto
    type: ...
  
  - id: procesar_expertos
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
    inputs:
      configuracion_expertos:
        expertos:
          - ANALISIS_LEGAL_DOCUMENTOS
          - EXTRACCION_DATOS
          - VALIDACION_FORMATO
```

### **2. Flujo de Atención Médica**
```yaml
id: flujo_atencion_medica
tasks:
  - id: analisis_medico
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_analisis_medico
  
  - id: procesar_expertos_generales
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
```

### **3. Flujo de Análisis Financiero**
```yaml
id: flujo_analisis_financiero
tasks:
  - id: procesar_expertos
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
    inputs:
      configuracion_expertos:
        expertos:
          - ANALISIS_RIESGO
          - ANALISIS_CREDITO
          - ANALISIS_FRAUDE
```

---

## ✅ Checklist de Implementación

- [x] Crear subflujo reutilizable
- [x] Simplificar flujo principal
- [x] Eliminar código duplicado
- [x] Documentar arquitectura
- [ ] Testear subflujo independientemente
- [ ] Testear flujo principal con subflujo
- [ ] Crear subflujos adicionales según necesidad

---

## 🚀 Próximos Pasos

1. **Implementar Expertos:**
   - Cada experto debe ser una estrategia en Python
   - Registrar en `src/core/factory.py`

2. **Crear Subflujos Especializados:**
   - Subflujo para análisis legal
   - Subflujo para análisis médico
   - Subflujo para RAG especializado

3. **Optimizar Configuración:**
   - Permitir configuración dinámica de número de expertos
   - Permitir configuración de timeouts por experto
   - Permitir configuración de estrategia de unificación

---

**Fecha de Implementación:** 2025-11-24  
**Versión:** 4.0.0  
**Estado:** ✅ Arquitectura modular implementada
