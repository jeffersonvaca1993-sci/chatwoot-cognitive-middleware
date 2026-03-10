# 📊 Análisis del Estado Actual de las Bases de Datos

**Fecha:** 2025-11-26  
**Instancia:** PostgreSQL compartida (`moe_postgres`)  
**Base de datos:** `chatwoot_production`

---

## 🏗️ Arquitectura General

Tienes **UNA SOLA instancia de PostgreSQL** que contiene:

1. **Tablas de Chatwoot** (94 tablas totales) - Sistema de terceros
2. **Tablas personalizadas** (6 tablas) - Tu sistema de "expropiación"

### Conexión Compartida

```yaml
# docker-compose.yml
postgres:
  image: pgvector/pgvector:pg16
  environment:
    POSTGRES_DB: chatwoot_production
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
```

**Ambas APIs comparten la misma instancia:**
- `src/main.py` (API interna/MoE) → Usa SQLModel
- `justibot_service/private/main.py` (API externa/Widget) → Usa databases (async)

---

## 📋 Estado Actual de las Tablas

### 1️⃣ Tus Tablas Personalizadas (Expropiación)

#### **A. `clientes_activos`** (5 registros)

**Propósito:** Directorio maestro de usuarios externos (compradores)

| Columna | Tipo | Descripción | Estado |
|---------|------|-------------|--------|
| `id_cliente` | integer | PK autoincremental | ✅ |
| `credencial_externa` | text | Identificador único (ej: `guest_5185wAnH`) | ✅ UNIQUE |
| `fecha_registro` | timestamp | Fecha de creación | ✅ |
| `nombre_alias` | text | Nombre para mostrar | ✅ |
| `contexto_vivo` | jsonb | Datos dinámicos | ✅ |
| `estado_ciclo` | enum | prospecto/activo/riesgo/baja | ✅ |
| `ultima_actividad` | timestamp | Última interacción | ✅ |
| **`email`** | text | ⚠️ **AGREGADO MANUALMENTE** | ✅ |
| **`password_hash`** | text | ⚠️ **AGREGADO MANUALMENTE** | ✅ |
| **`session_token`** | text | ⚠️ **AGREGADO MANUALMENTE** | ✅ |

**⚠️ PROBLEMA CRÍTICO:** Los campos `email`, `password_hash` y `session_token` fueron agregados **manualmente** (no están en `init_db.sql` ni en `models.py`). Esto causa **desincronización** entre:
- El schema SQL real
- El modelo SQLModel (`src/database/models.py`)
- El script de inicialización (`scripts/init_db.sql`)

**Datos actuales:**
```
id_cliente | credencial_externa | nombre_alias      | email | has_token
-----------+--------------------+-------------------+-------+-----------
2          | guest_5185wAnH     | Invitado guest_   | NULL  | false
3          | guest_YFi2eoCL     | Invitado guest_   | NULL  | false
4          | guest_T7-N2idJ     | Invitado guest_   | NULL  | true
1          | guest_hVza-uGZ     | Invitado guest_   | NULL  | true
53         | guest_uDVUhC6u     | Invitado guest_   | NULL  | true
```

---

#### **B. `directorio_empleados`** (0 registros)

**Propósito:** Nómina interna para gestión de permisos

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_empleado` | integer | PK |
| `id_agente_chatwoot` | text | Referencia a agente de Chatwoot |
| `nombre_real` | text | Nombre del empleado |
| `departamento` | text | Área de trabajo |
| `rol_acceso` | enum | soporte_nivel_1/ventas/admin/auditor |
| `esta_activo` | boolean | Estado del empleado |

**Estado:** ❌ Vacía (no se ha usado)

---

#### **C. `activos_globales`** (0 registros)

**Propósito:** Inventario de archivos expropiados (PDFs, imágenes, etc.)

**Estado:** ❌ Vacía (no se ha usado)

---

#### **D. `transacciones_agente`** (0 registros)

**Propósito:** Bitácora de interacciones (reemplaza el chat log de Chatwoot)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_transaccion` | bigint | PK |
| `id_cliente` | integer | FK → clientes_activos |
| `fecha_cierre` | timestamp | Cuándo se completó |
| `tipo_actor_respuesta` | enum | ia/empleado/sistema |
| `tipo_desenlace` | enum | respuesta_ia/escalada_humano/etc |
| `input_usuario` | text | Mensaje del usuario |
| `output_respuesta` | text | Respuesta generada |
| `razonamiento_tecnico` | text | Logs internos |
| `resumen_estado_actual` | text | Estado de la conversación |
| `id_mensaje_chatwoot` | integer | Referencia al mensaje original |
| `intencion_detectada` | text | Clasificación de intención |

**Estado:** ❌ Vacía (no se está registrando nada)

---

#### **E. `base_conocimiento`** (0 registros)

**Propósito:** RAG - Biblioteca de leyes y normas con embeddings

**Estado:** ❌ Vacía (no se ha cargado conocimiento)

---

#### **F. `punteros_contexto`** (0 registros)

**Propósito:** Índice de información externa (ej: expedientes en otros sistemas)

**Estado:** ❌ Vacía (no se ha usado)

---

### 2️⃣ Tablas Clave de Chatwoot

#### **A. `contacts`** (11 registros)

**Propósito:** Contactos/usuarios en Chatwoot

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | PK |
| `name` | varchar | Nombre del contacto |
| `email` | varchar | Email |
| `identifier` | varchar | ⭐ **CLAVE DE RELACIÓN** |
| `account_id` | integer | Cuenta de Chatwoot |
| `custom_attributes` | jsonb | Atributos personalizados |

**Datos actuales:**
```
id | name              | email | identifier
---+-------------------+-------+----------------
2  | cold-water-123    | NULL  | NULL
3  | blue-pine-626     | NULL  | NULL
7  | guest_hVza-uGZ    | NULL  | guest_hVza-uGZ ✅
8  | guest_5185wAnH    | NULL  | guest_5185wAnH ✅
9  | guest_YFi2eoCL    | NULL  | guest_YFi2eoCL ✅
10 | guest_T7-N2idJ    | NULL  | guest_T7-N2idJ ✅
11 | guest_uDVUhC6u    | NULL  | guest_uDVUhC6u ✅
```

**⚠️ OBSERVACIÓN:** Hay 6 contactos sin `identifier` (creados manualmente o por otro proceso)

---

#### **B. `conversations`** (7 registros)

**Propósito:** Conversaciones/hilos de chat

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | PK |
| `contact_id` | bigint | FK → contacts |
| `inbox_id` | integer | Bandeja de entrada |
| `status` | integer | 0=open, 1=resolved, etc |
| `assignee_id` | integer | Agente asignado |

**Estado:** 7 conversaciones activas

---

#### **C. `messages`** (22 registros)

**Propósito:** Mensajes individuales en las conversaciones

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id` | integer | PK |
| `conversation_id` | integer | FK → conversations |
| `content` | text | Contenido del mensaje |
| `message_type` | integer | 0=incoming (usuario), 1=outgoing (agente) |
| `sender_type` | varchar | Contact/User/AgentBot |
| `sender_id` | bigint | ID del remitente |
| `private` | boolean | Nota interna o visible |

**Estado:** 22 mensajes totales

---

## 🔗 Relación entre Tablas

### Mapeo Actual

```
clientes_activos.credencial_externa = contacts.identifier
                                          ↓
                                    conversations.contact_id = contacts.id
                                          ↓
                                    messages.conversation_id = conversations.id
```

**Ejemplo de relación:**

| Tu Tabla | Chatwoot |
|----------|----------|
| `clientes_activos.id_cliente = 1` | → |
| `credencial_externa = "guest_hVza-uGZ"` | → `contacts.identifier = "guest_hVza-uGZ"` |
| | → `contacts.id = 7` |
| | → `conversations.contact_id = 7` |
| | → `conversations.id = 3` |
| | → `messages.conversation_id = 3` (4 mensajes) |

---

## ⚠️ Problemas Identificados

### 1. **Desincronización de Schema**

**Problema:** Los campos `email`, `password_hash`, `session_token` existen en la BD pero NO en:
- ❌ `scripts/init_db.sql`
- ❌ `src/database/models.py` (clase `ClientesActivos`)

**Consecuencia:**
- Si recreas la BD, perderás estos campos
- SQLModel no puede mapear estos campos
- Migraciones futuras fallarán

**Solución:** Actualizar ambos archivos para reflejar el schema real

---

### 2. **No se Cachean IDs de Chatwoot**

**Problema:** No guardas `chatwoot_contact_id` ni `chatwoot_conversation_id` en `clientes_activos`

**Consecuencia:**
- Cada operación requiere 2-3 llamadas HTTP a Chatwoot para "descubrir" los IDs
- Latencia de 500-1500ms por mensaje

**Solución:** Agregar campos:
```sql
ALTER TABLE clientes_activos 
ADD COLUMN chatwoot_contact_id INTEGER,
ADD COLUMN chatwoot_conversation_id INTEGER;
```

---

### 3. **No se Registran Transacciones**

**Problema:** La tabla `transacciones_agente` está vacía

**Consecuencia:**
- No tienes historial propio
- Dependes 100% de Chatwoot
- No puedes hacer análisis de intenciones

**Solución:** Implementar logging en cada mensaje enviado/recibido

---

### 4. **Falta Integración con la API Interna**

**Problema:** La API interna (`src/main.py`) usa SQLModel pero no interactúa con `clientes_activos`

**Consecuencia:**
- No hay sincronización entre ambas APIs
- Datos duplicados o inconsistentes

**Solución:** Crear servicios compartidos para acceso a `clientes_activos`

---

## 📊 Resumen Ejecutivo

| Aspecto | Estado | Prioridad |
|---------|--------|-----------|
| Schema de `clientes_activos` | ⚠️ Desincronizado | 🔴 Alta |
| Caché de IDs de Chatwoot | ❌ No implementado | 🔴 Alta |
| Login con BD unificada | ⚠️ Parcial (falta sync) | 🟡 Media |
| Registro de transacciones | ❌ No implementado | 🟡 Media |
| Base de conocimiento | ❌ Vacía | 🟢 Baja |
| Gestión de empleados | ❌ No usado | 🟢 Baja |

---

## 🎯 Próximos Pasos Recomendados

### Fase 1: Sincronización de Schema (URGENTE)

1. ✅ Actualizar `src/database/models.py`
2. ✅ Actualizar `scripts/init_db.sql`
3. ✅ Crear migración para agregar campos de caché

### Fase 2: Optimización de Latencia

1. ✅ Agregar campos `chatwoot_contact_id` y `chatwoot_conversation_id`
2. ✅ Migrar de `requests` a `httpx` async
3. ✅ Implementar caché de IDs

### Fase 3: Login Unificado

1. ✅ Implementar endpoint `/auth/login` que use `clientes_activos`
2. ✅ Sincronizar datos entre Chatwoot y tu BD
3. ✅ Implementar recuperación de contraseña

### Fase 4: Expropiación de Datos

1. ⏳ Implementar logging en `transacciones_agente`
2. ⏳ Crear proceso de sincronización de mensajes históricos
3. ⏳ Implementar análisis de intenciones

---

## 🔍 Comandos Útiles para Inspección

```bash
# Ver todas las tablas
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "\dt"

# Ver estructura de una tabla
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "\d clientes_activos"

# Ver datos de clientes
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "SELECT * FROM clientes_activos;"

# Ver relación completa
docker exec moe_postgres psql -U postgres -d chatwoot_production -c "
SELECT 
  c.id_cliente, 
  c.credencial_externa, 
  ct.id as contact_id, 
  conv.id as conversation_id,
  COUNT(m.id) as num_messages
FROM clientes_activos c
LEFT JOIN contacts ct ON c.credencial_externa = ct.identifier
LEFT JOIN conversations conv ON ct.id = conv.contact_id
LEFT JOIN messages m ON conv.id = m.conversation_id
GROUP BY c.id_cliente, c.credencial_externa, ct.id, conv.id;"
```

---

**Generado automáticamente por Antigravity**
