# 🏗️ Arquitectura de Base de Datos - Versión Objetivo Actualizada

**Última actualización:** 2025-11-26  
**Ambiente:** Desarrollo  
**Estado:** Schema sincronizado con realidad operativa

---

## 📌 Filosofía de Diseño

Este sistema de base de datos está diseñado para **expropiar progresivamente** los datos de Chatwoot, permitiendo independencia operativa mientras se mantiene compatibilidad temporal con el sistema externo.

### Principios Fundamentales

1. **Fidelidad de Datos**: Cada interacción se registra completa y estructuradamente
2. **Auditoría Total**: Trazabilidad de cada acción (quién, qué, cuándo, por qué)
3. **Independencia Progresiva**: Reducción gradual de dependencia de Chatwoot
4. **Optimización de Rendimiento**: Caché estratégico para minimizar llamadas HTTP
5. **Flexibilidad Contextual**: Uso de JSONB para datos dinámicos

---

## 🗂️ Arquitectura de Seis Pilares

### 1️⃣ **IDENTIDAD** (Tablas A y B)

Gestión separada de identidades externas (clientes) e internas (empleados).

#### **Tabla A: `clientes_activos`**

**Propósito:** Directorio maestro de usuarios externos con autenticación propia

```sql
CREATE TABLE clientes_activos (
    -- Identificación
    id_cliente SERIAL PRIMARY KEY,
    credencial_externa TEXT UNIQUE NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    nombre_alias TEXT DEFAULT 'Cliente',
    
    -- Estado y Contexto
    contexto_vivo JSONB DEFAULT '{}'::jsonb,
    estado_ciclo estado_ciclo_cliente DEFAULT 'prospecto',
    ultima_actividad TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Autenticación (para independencia de Chatwoot)
    email TEXT UNIQUE,
    password_hash TEXT,
    session_token TEXT UNIQUE,
    
    -- Caché de Integración (optimización)
    chatwoot_contact_id INTEGER,
    chatwoot_conversation_id INTEGER
);
```

**Campos Clave:**

| Campo | Tipo | Propósito | Ejemplo |
|-------|------|-----------|---------|
| `credencial_externa` | TEXT | ID único en sistemas externos | `guest_ABC123` |
| `email` | TEXT | Email del usuario (NULL para invitados) | `user@example.com` |
| `password_hash` | TEXT | Hash bcrypt (NULL para invitados) | `$2b$12$...` |
| `session_token` | TEXT | Token JWT/opaco para sesiones | `eyJhbG...` |
| `chatwoot_contact_id` | INTEGER | **CACHÉ**: ID del contacto en Chatwoot | `42` |
| `chatwoot_conversation_id` | INTEGER | **CACHÉ**: ID de conversación activa | `123` |
| `contexto_vivo` | JSONB | Datos dinámicos del cliente | `{"preferencias": {...}}` |

**Estados del Ciclo de Vida:**
- `prospecto`: Usuario anónimo/invitado
- `activo`: Cliente registrado y activo
- `riesgo`: Cliente con problemas o inactivo
- `baja`: Cliente dado de baja

**Flujo de Transición:**
```
Invitado (prospecto) → Registro → Cliente (activo)
                                      ↓
                              Inactividad/Problema
                                      ↓
                                  (riesgo)
                                      ↓
                              Cancelación/Cierre
                                      ↓
                                   (baja)
```

---

#### **Tabla B: `directorio_empleados`**

**Propósito:** Nómina interna para gestión de permisos y escalamientos

```sql
CREATE TABLE directorio_empleados (
    id_empleado SERIAL PRIMARY KEY,
    id_agente_chatwoot TEXT UNIQUE,
    nombre_real TEXT NOT NULL,
    departamento TEXT NOT NULL,
    rol_acceso rol_empleado DEFAULT 'soporte_nivel_1',
    esta_activo BOOLEAN DEFAULT TRUE
);
```

**Roles de Acceso:**
- `soporte_nivel_1`: Atención básica
- `ventas`: Equipo comercial
- `admin`: Administradores del sistema
- `auditor`: Solo lectura para auditoría

---

### 2️⃣ **MEMORIA TRANSACCIONAL** (Tabla D)

Reemplazo del chat log tradicional por una bitácora estructurada.

#### **Tabla D: `transacciones_agente`**

**Propósito:** Registro de cada interacción completa (turno conversacional)

```sql
CREATE TABLE transacciones_agente (
    id_transaccion BIGSERIAL PRIMARY KEY,
    id_cliente INT REFERENCES clientes_activos(id_cliente) NOT NULL,
    fecha_cierre TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Actor y Desenlace
    tipo_actor_respuesta tipo_actor NOT NULL,
    id_empleado_responde INT REFERENCES directorio_empleados(id_empleado),
    tipo_desenlace tipo_desenlace NOT NULL,
    destino_escalada TEXT,
    
    -- Contenido
    input_usuario TEXT NOT NULL,
    output_respuesta TEXT,
    razonamiento_tecnico TEXT,
    intencion_detectada TEXT,
    resumen_estado_actual TEXT NOT NULL,
    
    -- Referencias
    ids_activos_involucrados JSONB DEFAULT '[]'::jsonb,
    id_orquestacion_kestra TEXT,
    id_mensaje_chatwoot INT
);
```

**Tipos de Actor:**
- `ia`: Respuesta generada por IA
- `empleado`: Respuesta de agente humano
- `sistema`: Mensaje automático del sistema

**Tipos de Desenlace:**
- `respuesta_ia`: IA respondió satisfactoriamente
- `escalada_humano`: Se escaló a agente humano
- `intervencion_humana`: Agente intervino directamente
- `nota_interna`: Nota privada (no visible al cliente)

**Ejemplo de Registro:**
```json
{
  "id_transaccion": 42,
  "id_cliente": 5,
  "tipo_actor_respuesta": "ia",
  "tipo_desenlace": "respuesta_ia",
  "input_usuario": "¿Cuánto cuesta una visa de turista?",
  "output_respuesta": "El costo de la visa de turista es de $160 USD...",
  "razonamiento_tecnico": "RAG query: 'visa turista costo' → fragmento_id: 234",
  "intencion_detectada": "CONSULTA_PRECIO_VISA",
  "resumen_estado_actual": "Cliente interesado en visa de turista, sin documentos aún",
  "id_mensaje_chatwoot": 789
}
```

---

### 3️⃣ **BASE DE CONOCIMIENTO** (Tabla E)

Fuente de verdad estática para RAG (Retrieval-Augmented Generation).

#### **Tabla E: `base_conocimiento`**

**Propósito:** Biblioteca de leyes, normas y procedimientos con búsqueda semántica

```sql
CREATE TABLE base_conocimiento (
    id_fragmento SERIAL PRIMARY KEY,
    contenido_textual TEXT NOT NULL,
    fuente_cita TEXT,
    categoria TEXT,
    vector_embedding vector(1536),
    ultima_actualizacion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vector_conocimiento 
ON base_conocimiento 
USING hnsw (vector_embedding vector_cosine_ops);
```

**Dimensiones del Vector:**
- **1536**: OpenAI `text-embedding-3-small`
- **768**: Google `text-embedding-004` (alternativa)

**Categorías Sugeridas:**
- `ley_migracion`
- `procedimiento_visa`
- `requisitos_documentales`
- `tarifas_oficiales`
- `faq_general`

**Flujo de RAG:**
```
Usuario: "¿Qué documentos necesito para visa de trabajo?"
    ↓
Embedding del query (1536 dims)
    ↓
Búsqueda vectorial (HNSW) → Top 5 fragmentos
    ↓
Contexto para LLM → Respuesta fundamentada
```

---

### 4️⃣ **BÓVEDA DE ACTIVOS** (Tabla C)

Inventario físico de archivos expropiados.

#### **Tabla C: `activos_globales`**

**Propósito:** Registro de archivos subidos con verificación de integridad

```sql
CREATE TABLE activos_globales (
    id_activo SERIAL PRIMARY KEY,
    id_propietario INT REFERENCES clientes_activos(id_cliente) ON DELETE CASCADE,
    huella_digital_hash TEXT NOT NULL,
    tipo_mime_real TEXT NOT NULL,
    ruta_almacenamiento TEXT NOT NULL,
    nombre_original TEXT,
    tamano_bytes BIGINT,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Verificación de Integridad:**
```python
import hashlib

def calcular_huella(archivo_bytes):
    return hashlib.sha256(archivo_bytes).hexdigest()
```

**Detección de Duplicados:**
```sql
SELECT id_activo, nombre_original 
FROM activos_globales 
WHERE huella_digital_hash = 'abc123...'
LIMIT 1;
```

---

### 5️⃣ **MAPA DE CONTEXTO EXTERNO** (Tabla F)

Índice de información en sistemas externos.

#### **Tabla F: `punteros_contexto`**

**Propósito:** Lazy loading de datos externos (CRM, ERP, etc.)

```sql
CREATE TABLE punteros_contexto (
    id_puntero SERIAL PRIMARY KEY,
    id_cliente INT REFERENCES clientes_activos(id_cliente) ON DELETE CASCADE,
    sistema_origen TEXT NOT NULL,
    id_externo_referencia TEXT NOT NULL,
    resumen_corto TEXT NOT NULL,
    uri_carga_datos TEXT NOT NULL,
    creado_en TIMESTAMP DEFAULT NOW()
);
```

**Ejemplo de Uso:**
```json
{
  "sistema_origen": "salesforce",
  "id_externo_referencia": "CASE-12345",
  "resumen_corto": "Expediente de visa rechazada en 2023",
  "uri_carga_datos": "https://api.salesforce.com/cases/12345"
}
```

---

## 🔗 Diagrama de Relaciones

```
┌─────────────────────┐
│ clientes_activos    │
│ (Tabla A)           │
│ - id_cliente (PK)   │
│ - email             │◄──────┐
│ - session_token     │       │
│ - chatwoot_*_id     │       │
└──────┬──────────────┘       │
       │                      │
       │ 1:N                  │
       ▼                      │
┌─────────────────────┐       │
│ transacciones_agente│       │
│ (Tabla D)           │       │
│ - id_transaccion(PK)│       │
│ - id_cliente (FK)   ├───────┘
│ - input_usuario     │
│ - output_respuesta  │
└─────────────────────┘

┌─────────────────────┐
│ directorio_empleados│
│ (Tabla B)           │
│ - id_empleado (PK)  │
│ - rol_acceso        │
└──────┬──────────────┘
       │
       │ 1:N
       ▼
┌─────────────────────┐
│ transacciones_agente│
│ - id_empleado (FK)  │
└─────────────────────┘

┌─────────────────────┐
│ activos_globales    │
│ (Tabla C)           │
│ - id_propietario(FK)├──► clientes_activos
└─────────────────────┘

┌─────────────────────┐
│ punteros_contexto   │
│ (Tabla F)           │
│ - id_cliente (FK)   ├──► clientes_activos
└─────────────────────┘

┌─────────────────────┐
│ base_conocimiento   │
│ (Tabla E)           │
│ - vector_embedding  │ (Sin FK, tabla independiente)
└─────────────────────┘
```

---

## 🔄 Integración con Chatwoot

### Estrategia de Caché

**Problema Original:**
- Cada mensaje requería 3 llamadas HTTP a Chatwoot
- Latencia de ~1500ms por operación

**Solución Implementada:**

```python
# Al crear/encontrar contacto en Chatwoot
await database.execute(
    """
    UPDATE clientes_activos 
    SET chatwoot_contact_id = :contact_id,
        chatwoot_conversation_id = :conv_id
    WHERE id_cliente = :user_id
    """,
    values={
        "contact_id": chatwoot_contact_id,
        "conv_id": chatwoot_conversation_id,
        "user_id": user_id
    }
)
```

**Resultado:**
- ✅ De 3 llamadas HTTP → 1 llamada HTTP
- ✅ Latencia reducida ~70%
- ✅ Menor carga en Chatwoot

### Sincronización Bidireccional

```
Widget → justibot_service → Chatwoot
                ↓
         clientes_activos (caché actualizado)
                ↓
         transacciones_agente (registro)
```

---

## 📊 Índices Estratégicos

### Índices de Rendimiento

```sql
-- Búsqueda por email (login)
CREATE INDEX idx_clientes_email ON clientes_activos(email);

-- Validación de sesión
CREATE INDEX idx_clientes_session_token ON clientes_activos(session_token);

-- Caché de Chatwoot
CREATE INDEX idx_clientes_chatwoot_contact ON clientes_activos(chatwoot_contact_id);

-- Historial de cliente
CREATE INDEX idx_transacciones_cliente ON transacciones_agente(id_cliente);

-- Trazabilidad externa
CREATE INDEX idx_kestra_ref ON transacciones_agente(id_orquestacion_kestra);
CREATE INDEX idx_chatwoot_ref ON transacciones_agente(id_mensaje_chatwoot);

-- Búsqueda semántica (HNSW)
CREATE INDEX idx_vector_conocimiento 
ON base_conocimiento 
USING hnsw (vector_embedding vector_cosine_ops);
```

---

## 🚀 Migración desde Estado Actual

### Paso 1: Agregar Campos Faltantes

```sql
-- Si la BD ya existe, ejecutar:
ALTER TABLE clientes_activos 
ADD COLUMN IF NOT EXISTS chatwoot_contact_id INTEGER,
ADD COLUMN IF NOT EXISTS chatwoot_conversation_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_clientes_chatwoot_contact 
ON clientes_activos(chatwoot_contact_id);
```

### Paso 2: Sincronizar Datos Existentes

```sql
-- Poblar caché de IDs de Chatwoot
UPDATE clientes_activos ca
SET chatwoot_contact_id = ct.id
FROM contacts ct
WHERE ca.credencial_externa = ct.identifier;

UPDATE clientes_activos ca
SET chatwoot_conversation_id = conv.id
FROM contacts ct
JOIN conversations conv ON ct.id = conv.contact_id
WHERE ca.credencial_externa = ct.identifier
  AND conv.inbox_id = 1; -- Tu inbox_id
```

### Paso 3: Validar Sincronización

```sql
SELECT 
    COUNT(*) FILTER (WHERE chatwoot_contact_id IS NOT NULL) as con_cache,
    COUNT(*) FILTER (WHERE chatwoot_contact_id IS NULL) as sin_cache,
    COUNT(*) as total
FROM clientes_activos;
```

---

## 📝 Convenciones de Nomenclatura

### Tablas
- Plural, snake_case
- Prefijo descriptivo cuando aplique
- Ejemplo: `clientes_activos`, `transacciones_agente`

### Columnas
- snake_case
- Sufijos estándar:
  - `_id`: Identificadores
  - `_at`: Timestamps
  - `_hash`: Hashes criptográficos
  - `_url` / `_uri`: URLs/URIs

### Índices
- Prefijo `idx_`
- Nombre descriptivo de la columna
- Ejemplo: `idx_clientes_email`

### ENUMs
- snake_case
- Valores descriptivos en español
- Ejemplo: `estado_ciclo_cliente`

---

## 🔐 Consideraciones de Seguridad

### Hashing de Contraseñas

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Crear hash
password_hash = pwd_context.hash("mi_contraseña_segura")

# Verificar
is_valid = pwd_context.verify("mi_contraseña_segura", password_hash)
```

### Tokens de Sesión

```python
import secrets

# Generar token seguro (256 bits)
session_token = secrets.token_urlsafe(32)
```

### Sanitización de Datos

```python
# Nunca almacenar contraseñas en texto plano
# Nunca loggear session_tokens
# Siempre usar prepared statements (SQLModel lo hace automáticamente)
```

---

## 📈 Métricas de Éxito

| Métrica | Objetivo | Estado Actual |
|---------|----------|---------------|
| Latencia de envío de mensaje | < 500ms | ⚠️ ~1500ms (sin caché) |
| Tasa de caché de IDs | > 95% | ❌ 0% (no implementado) |
| Registro de transacciones | 100% | ❌ 0% (tabla vacía) |
| Independencia de Chatwoot | > 80% | ⚠️ ~20% (solo autenticación) |

---

## 🎯 Roadmap de Implementación

### ✅ Fase 1: Fundamentos (COMPLETADO)
- [x] Schema SQL definido
- [x] Modelos SQLModel sincronizados
- [x] Campos de autenticación agregados

### 🔄 Fase 2: Optimización (EN PROGRESO)
- [x] Caché de IDs de Chatwoot (schema listo)
- [ ] Migración a httpx async
- [ ] Implementación de caché en endpoints

### ⏳ Fase 3: Expropiación
- [ ] Logging automático en `transacciones_agente`
- [ ] Sincronización de mensajes históricos
- [ ] Análisis de intenciones

### ⏳ Fase 4: Independencia
- [ ] Login 100% propio
- [ ] Gestión de sesiones sin Chatwoot
- [ ] Migración de contactos

---

**Documento mantenido como fuente única de verdad**  
**Última sincronización con BD:** 2025-11-26
