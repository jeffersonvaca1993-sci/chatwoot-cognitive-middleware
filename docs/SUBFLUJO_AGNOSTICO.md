# Subflujo Agnóstico: Señal → Procesamiento → Señal

## 🎯 Concepto

El subflujo ahora es **completamente agnóstico**: recibe una `SenalAgente`, la procesa (Router + Fan-Out + Fan-In + Síntesis), y devuelve una `SenalAgente` enriquecida.

Es una **caja negra reutilizable** que no conoce el contexto del flujo principal.

---

## 📦 Arquitectura del Subflujo

### **Input: SenalAgente**
```yaml
inputs:
  - id: senal_entrada
    type: JSON
    description: "SenalAgente a procesar"
  
  - id: configuracion_expertos
    type: JSON
    defaults:
      expertos: [ANALISIS_LEGAL, ANALISIS_FINANCIERO, RAG_CONOCIMIENTO]
      ejecutar_router: true
      estrategia_sintesis: "SINTETIZADOR_PARCIAL"
      config_sintesis:
        formato_salida: "acumulativo"
```

### **Procesamiento Interno**
```
1. Router Inteligente (opcional)
   ↓
2. Fan-Out: 3 expertos en paralelo
   ↓
3. Fan-In: Unificación estructural
   ↓
4. Síntesis: Genera respuesta coherente
```

### **Output: SenalAgente Enriquecida**
```yaml
outputs:
  - id: senal_procesada
    type: JSON
    value: "{{ outputs['4_sintesis'].body }}"
```

---

## 🔄 Flujo Principal Simplificado

### **Antes (7 pasos):**
```
1. Subflujo (Router + Fan-Out + Fan-In)
2. Síntesis Parcial ← DUPLICADO
3. Verificar Cola
4. Loop → Subflujo + Síntesis Parcial ← DUPLICADO
5. Síntesis Final
6. Finalización
7. Log
```

### **Ahora (6 pasos):**
```
1. Subflujo (Router + Fan-Out + Fan-In + Síntesis) ← TODO INCLUIDO
2. Verificar Cola
3. Loop → Subflujo ← REUTILIZA LÓGICA
4. Síntesis Final
5. Finalización
6. Log
```

**Mejora:**
- ✅ **-1 paso** en el flujo principal
- ✅ **Sin duplicación** de lógica de síntesis
- ✅ **Subflujo completamente agnóstico**

---

## 🎨 Configuración Flexible

### **Caso 1: Síntesis Parcial (para loops)**
```yaml
configuracion_expertos:
  expertos: [ANALISIS_LEGAL, ANALISIS_FINANCIERO, RAG_CONOCIMIENTO]
  ejecutar_router: true
  estrategia_sintesis: "SINTETIZADOR_PARCIAL"
  config_sintesis:
    formato_salida: "acumulativo"
```

### **Caso 2: Síntesis Final (sin loop)**
```yaml
configuracion_expertos:
  expertos: [ANALISIS_LEGAL, ANALISIS_FINANCIERO, RAG_CONOCIMIENTO]
  ejecutar_router: true
  estrategia_sintesis: "SINTETIZADOR_FINAL"
  config_sintesis:
    formato_salida: "texto_natural_completo"
```

### **Caso 3: Sin Síntesis (solo agregación)**
```yaml
configuracion_expertos:
  expertos: [RAG_CONOCIMIENTO, RAG_CONOCIMIENTO, RAG_CONOCIMIENTO]
  ejecutar_router: false
  estrategia_sintesis: "AGREGADOR_SIMPLE"
  config_sintesis:
    modo: "concatenar"
```

---

## 📊 Comparación de Arquitecturas

### **Antes: Subflujo Parcial**
```
Subflujo:
├── Router
├── Fan-Out
└── Fan-In

Flujo Principal:
├── Llamar Subflujo
├── Síntesis Parcial ← Lógica en flujo principal
├── Verificar Cola
├── Loop:
│   ├── Llamar Subflujo
│   └── Síntesis Parcial ← DUPLICADO
└── Síntesis Final
```

**Problemas:**
- ❌ Lógica de síntesis duplicada
- ❌ Subflujo no es autosuficiente
- ❌ Flujo principal conoce detalles de síntesis

### **Ahora: Subflujo Agnóstico**
```
Subflujo:
├── Router
├── Fan-Out
├── Fan-In
└── Síntesis ← INCLUIDO

Flujo Principal:
├── Llamar Subflujo (con config de síntesis)
├── Verificar Cola
├── Loop:
│   └── Llamar Subflujo (con config de síntesis) ← REUTILIZA
└── Síntesis Final
```

**Ventajas:**
- ✅ Sin duplicación
- ✅ Subflujo autosuficiente
- ✅ Flujo principal solo orquesta

---

## 🔧 Uso del Subflujo

### **Primera Llamada (Loop)**
```yaml
- id: 1_procesar_expertos
  type: io.kestra.plugin.core.flow.Subflow
  flowId: subflujo_procesamiento_expertos
  inputs:
    senal_entrada: "{{ inputs.senal_agente }}"
    configuracion_expertos:
      estrategia_sintesis: "SINTETIZADOR_PARCIAL"
      config_sintesis:
        formato_salida: "acumulativo"
```

### **Llamada en Loop (con mensajes acumulados)**
```yaml
- id: reiniciar_con_mensajes_acumulados
  type: io.kestra.plugin.core.flow.Subflow
  flowId: subflujo_procesamiento_expertos
  inputs:
    senal_entrada: "{{ outputs['2_verificar_y_acumular_cola'].body.senal_actualizada }}"
    configuracion_expertos:
      estrategia_sintesis: "SINTETIZADOR_PARCIAL"  # Misma config
      config_sintesis:
        formato_salida: "acumulativo"
```

**Nota:** La misma configuración se reutiliza, sin duplicar lógica.

---

## 🎯 Principios de Diseño

### **1. Agnóstico**
El subflujo **no conoce**:
- ❌ Si está en un loop
- ❌ Si hay mensajes encolados
- ❌ Qué hará el flujo principal después

El subflujo **solo conoce**:
- ✅ La señal de entrada
- ✅ Qué expertos invocar
- ✅ Cómo sintetizar

### **2. Reutilizable**
El mismo subflujo se puede usar en:
- ✅ Flujo de Chatwoot
- ✅ Flujo de análisis de documentos
- ✅ Flujo de atención médica
- ✅ Cualquier flujo que necesite procesamiento de expertos

### **3. Configurable**
Todo es configurable vía inputs:
- ✅ Qué expertos invocar
- ✅ Si ejecutar router
- ✅ Qué estrategia de síntesis usar
- ✅ Configuración de síntesis

### **4. Autosuficiente**
El subflujo es una **unidad completa**:
- ✅ Recibe señal
- ✅ Procesa completamente
- ✅ Devuelve señal enriquecida

---

## 📈 Ventajas de la Refactorización

### **1. Menos Código**
| Componente | Antes | Ahora | Mejora |
|------------|-------|-------|--------|
| Pasos en flujo principal | 7 | 6 | -14% |
| Duplicación de síntesis | 2x | 0x | -100% |
| Líneas en flujo principal | 180 | 170 | -6% |

### **2. Mejor Separación de Responsabilidades**
- **Subflujo:** Procesar expertos y sintetizar
- **Flujo Principal:** Orquestar loop y finalización

### **3. Más Flexible**
Ahora se puede cambiar la estrategia de síntesis sin modificar el flujo principal:

```yaml
# Desarrollo: Síntesis simple
estrategia_sintesis: "SINTETIZADOR_SIMPLE"

# Producción: Síntesis avanzada
estrategia_sintesis: "SINTETIZADOR_PARCIAL"
```

### **4. Más Testeable**
El subflujo se puede testear independientemente con diferentes configuraciones:

```yaml
# Test 1: Con router
configuracion_expertos:
  ejecutar_router: true

# Test 2: Sin router
configuracion_expertos:
  ejecutar_router: false

# Test 3: Síntesis final
configuracion_expertos:
  estrategia_sintesis: "SINTETIZADOR_FINAL"
```

---

## 🚀 Casos de Uso Futuros

### **Caso 1: Flujo de Análisis Rápido**
```yaml
id: flujo_analisis_rapido
tasks:
  - id: procesar
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
    inputs:
      senal_entrada: "{{ ... }}"
      configuracion_expertos:
        expertos: [RAG_CONOCIMIENTO, RAG_CONOCIMIENTO, RAG_CONOCIMIENTO]
        ejecutar_router: false  # Más rápido
        estrategia_sintesis: "AGREGADOR_SIMPLE"
```

### **Caso 2: Flujo de Análisis Profundo**
```yaml
id: flujo_analisis_profundo
tasks:
  - id: procesar
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
    inputs:
      senal_entrada: "{{ ... }}"
      configuracion_expertos:
        expertos: [ANALISIS_LEGAL, ANALISIS_FINANCIERO, ANALISIS_MEDICO]
        ejecutar_router: true
        estrategia_sintesis: "SINTETIZADOR_AVANZADO"
        config_sintesis:
          profundidad: "maxima"
          incluir_razonamiento: true
```

### **Caso 3: Flujo sin Síntesis**
```yaml
id: flujo_solo_agregacion
tasks:
  - id: procesar
    type: io.kestra.plugin.core.flow.Subflow
    flowId: subflujo_procesamiento_expertos
    inputs:
      senal_entrada: "{{ ... }}"
      configuracion_expertos:
        expertos: [EXTRACTOR_DATOS, VALIDADOR, CLASIFICADOR]
        ejecutar_router: false
        estrategia_sintesis: "SIN_SINTESIS"  # Solo agrega contexto
```

---

## ✅ Checklist de Implementación

- [x] Agregar paso de síntesis al subflujo
- [x] Actualizar inputs del subflujo (estrategia_sintesis, config_sintesis)
- [x] Eliminar paso de síntesis parcial del flujo principal
- [x] Actualizar llamadas al subflujo con nueva configuración
- [x] Renumerar pasos del flujo principal
- [x] Documentar arquitectura agnóstica
- [ ] Testear subflujo independientemente
- [ ] Testear flujo completo con loop

---

**Fecha de Refactorización:** 2025-11-24  
**Versión:** 4.1.0  
**Estado:** ✅ Subflujo completamente agnóstico implementado
