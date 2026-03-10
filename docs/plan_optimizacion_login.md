# 🔐 Análisis y Plan de Optimización del Sistema de Login

**Fecha:** 2025-11-26  
**Estado:** Planificación (NO MODIFICAR CÓDIGO AÚN)

---

## 📊 Estado Actual del Sistema

### Flujos Existentes

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUJOS DE AUTENTICACIÓN                  │
└─────────────────────────────────────────────────────────────┘

1️⃣ INICIO DE SESIÓN INVITADO (session/start)
2️⃣ REGISTRO (auth/register)
3️⃣ LOGIN (auth/login)
4️⃣ ENVÍO DE MENSAJES (messages)
5️⃣ OBTENCIÓN DE MENSAJES (messages GET)
```

---

## 1️⃣ Flujo: Inicio de Sesión Invitado

### Endpoint: `POST /api/session/start`

**Archivo:** `justibot_service/private/endpoints/session.py`

### Diagrama de Flujo Actual

```
Usuario abre widget
    ↓
Frontend: initGuestSession()
    ↓
POST /api/session/start
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: start_session()                            │
├─────────────────────────────────────────────────────┤
│ 1. Generar session_token                            │
│ 2. Generar identifier (guest_ABC123)                │
│                                                      │
│ 3. 🔴 HTTP #1: POST /contacts (Chatwoot)           │
│    - Si 422 → HTTP #2: GET /contacts/search        │
│    - Si existe → HTTP #3: GET /contacts/{id}       │
│                                                      │
│ 4. 🟢 DB Query: get_user_by_credential()           │
│    - Si existe → update_session_token()             │
│    - Si no → create_guest_user()                    │
│                                                      │
│ 5. 🔴 HTTP #4: GET /contacts/{id}/conversations    │
│                                                      │
│ 6. Si no hay conversación:                          │
│    🔴 HTTP #5: POST /conversations                 │
│                                                      │
│ 7. ❌ NO CACHEA contact_id ni conversation_id      │
└─────────────────────────────────────────────────────┘
    ↓
Return: {token, user_name}
```

### ⚠️ Problemas Identificados

| # | Problema | Impacto | Severidad |
|---|----------|---------|-----------|
| 1 | **5 llamadas HTTP a Chatwoot** en el peor caso | Latencia ~2000ms | 🔴 Alta |
| 2 | **No cachea IDs** de Chatwoot en BD | Repetición en cada operación | 🔴 Alta |
| 3 | **Requests síncrono** (bloqueante) | Bloquea event loop | 🟡 Media |
| 4 | **Manejo de errores básico** | Poca resiliencia | 🟡 Media |
| 5 | **Logs excesivos** en producción | Ruido en logs | 🟢 Baja |

### 📈 Métricas Actuales

```
Tiempo promedio: ~1500-2500ms
Llamadas HTTP: 3-5 (dependiendo de si existe)
Queries DB: 1-2
```

---

## 2️⃣ Flujo: Registro de Usuario

### Endpoint: `POST /api/auth/register`

**Archivo:** `justibot_service/private/endpoints/auth.py`

### Diagrama de Flujo Actual

```
Usuario completa formulario de registro
    ↓
Frontend: doRegister()
    ↓
POST /api/auth/register
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: register()                                  │
├─────────────────────────────────────────────────────┤
│ 1. 🟢 Validar session_token (header)                │
│ 2. 🟢 DB: get_user_by_token()                       │
│ 3. 🟢 DB: get_user_by_email() (verificar duplicado) │
│ 4. 🟢 DB: register_user() (actualizar BD local)     │
│                                                      │
│ 5. 🔴 HTTP #1: GET /contacts/search (Chatwoot)     │
│                                                      │
│ 6. 🔴 HTTP #2: PUT /contacts/{id} (actualizar)     │
│                                                      │
│ 7. 🔴 HTTP #3: GET /contacts/{id}/conversations    │
│                                                      │
│ 8. 🔴 HTTP #4: POST /conversations/{id}/labels     │
│                                                      │
│ 9. ❌ NO CACHEA contact_id ni conversation_id      │
└─────────────────────────────────────────────────────┘
    ↓
Return: {status: "ok", name}
```

### ⚠️ Problemas Identificados

| # | Problema | Impacto | Severidad |
|---|----------|---------|-----------|
| 1 | **4 llamadas HTTP a Chatwoot** | Latencia ~1500ms | 🔴 Alta |
| 2 | **No cachea IDs** después de buscar | Desperdicio de búsqueda | 🔴 Alta |
| 3 | **No actualiza session_token** tras registro | Usuario debe hacer login manual | 🟡 Media |
| 4 | **Requests síncrono** | Bloquea event loop | 🟡 Media |
| 5 | **Sincronización parcial** con Chatwoot | Datos pueden desincronizarse | 🟢 Baja |

### 📈 Métricas Actuales

```
Tiempo promedio: ~1200-1800ms
Llamadas HTTP: 4
Queries DB: 3
```

---

## 3️⃣ Flujo: Login de Usuario

### Endpoint: `POST /api/auth/login`

**Archivo:** `justibot_service/private/endpoints/auth.py`

### Diagrama de Flujo Actual

```
Usuario ingresa email/password
    ↓
Frontend: doLogin()
    ↓
POST /api/auth/login
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: login()                                     │
├─────────────────────────────────────────────────────┤
│ 1. 🟢 DB: get_user_by_email()                       │
│ 2. 🟢 Verificar password (bcrypt)                   │
│ 3. 🟢 Generar nuevo session_token                   │
│ 4. 🟢 DB: update_session_token()                    │
│                                                      │
│ ✅ NO HAY LLAMADAS HTTP A CHATWOOT                  │
└─────────────────────────────────────────────────────┘
    ↓
Return: {token, name}
    ↓
Frontend: Actualiza localStorage
    ↓
Frontend: loadMessages() → Aquí empiezan los problemas
```

### ✅ Aspectos Positivos

| Aspecto | Descripción |
|---------|-------------|
| ✅ **100% local** | No depende de Chatwoot |
| ✅ **Rápido** | ~50-100ms |
| ✅ **Seguro** | Usa bcrypt para passwords |
| ✅ **Stateless** | Token en BD, no en memoria |

### ⚠️ Problema Post-Login

**Después del login exitoso**, cuando el usuario intenta cargar mensajes:

```
Frontend: loadMessages()
    ↓
GET /api/messages
    ↓
Backend: get_messages()
    ↓
🔴 HTTP #1: GET /contacts/search (buscar contact_id)
🔴 HTTP #2: GET /contacts/{id}/conversations
🔴 HTTP #3: GET /conversations/{id}/messages
```

**Problema:** Aunque el login es rápido, **la primera carga de mensajes es lenta** porque no tenemos los IDs cacheados.

---

## 4️⃣ Flujo: Envío de Mensajes

### Endpoint: `POST /api/messages`

**Archivo:** `justibot_service/private/endpoints/messages.py`

### Diagrama de Flujo Actual

```
Usuario escribe mensaje
    ↓
Frontend: sendMessage()
    ↓
POST /api/messages
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: send_message()                              │
├─────────────────────────────────────────────────────┤
│ 1. 🟢 DB: get_user_by_token()                       │
│                                                      │
│ 2. 🔴 HTTP #1: GET /contacts/search                │
│ 3. 🔴 HTTP #2: GET /contacts/{id}/conversations    │
│                                                      │
│ 4. 🔴 HTTP #3: POST /conversations/{id}/messages   │
│                                                      │
│ ❌ NO CACHEA conversation_id                        │
└─────────────────────────────────────────────────────┘
    ↓
Return: mensaje creado
```

### ⚠️ Problemas Identificados

| # | Problema | Impacto | Severidad |
|---|----------|---------|-----------|
| 1 | **3 llamadas HTTP por mensaje** | Latencia ~1500ms | 🔴 Crítica |
| 2 | **Búsqueda repetida** de IDs | Desperdicio de recursos | 🔴 Alta |
| 3 | **Requests síncrono** | Bloquea event loop | 🟡 Media |
| 4 | **Sin retry logic** | Fallos no recuperables | 🟡 Media |

### 📈 Métricas Actuales

```
Tiempo promedio: ~1500ms ⚠️ INACEPTABLE
Llamadas HTTP: 3 por mensaje
Queries DB: 1
```

**Experiencia del usuario:**
```
Usuario: "Hola" [Enter]
    ↓
⏳ 1.5 segundos de espera...
    ↓
Mensaje aparece
```

---

## 5️⃣ Flujo: Obtención de Mensajes

### Endpoint: `GET /api/messages`

**Archivo:** `justibot_service/private/endpoints/messages.py`

### Diagrama de Flujo Actual

```
Frontend: loadMessages() (cada 3 segundos)
    ↓
GET /api/messages
    ↓
┌─────────────────────────────────────────────────────┐
│ Backend: get_messages()                              │
├─────────────────────────────────────────────────────┤
│ 1. 🟢 DB: get_user_by_token()                       │
│                                                      │
│ 2. 🔴 HTTP #1: GET /contacts/search                │
│ 3. 🔴 HTTP #2: GET /contacts/{id}/conversations    │
│ 4. 🔴 HTTP #3: GET /conversations/{id}/messages    │
└─────────────────────────────────────────────────────┘
    ↓
Return: lista de mensajes
```

### ⚠️ Problemas Identificados

| # | Problema | Impacto | Severidad |
|---|----------|---------|-----------|
| 1 | **3 llamadas HTTP cada 3 segundos** | Carga excesiva en Chatwoot | 🔴 Crítica |
| 2 | **Polling agresivo** | Desperdicio de recursos | 🟡 Media |
| 3 | **Sin WebSockets** | Latencia en respuestas | 🟢 Baja |

### 📈 Métricas Actuales

```
Frecuencia: Cada 3 segundos
Llamadas HTTP: 3 por polling
Carga en Chatwoot: ~20 requests/minuto por usuario
```

---

## 🎯 Plan de Optimización

### Fase 1: Implementar Caché de IDs (PRIORIDAD MÁXIMA)

**Objetivo:** Reducir llamadas HTTP de 3 → 1 en envío/recepción de mensajes

#### Cambios Necesarios

**1. Actualizar `database.py`**

Agregar queries para cachear IDs:

```python
UPDATE_CHATWOOT_CACHE = """
    UPDATE clientes_activos
    SET chatwoot_contact_id = :contact_id,
        chatwoot_conversation_id = :conversation_id
    WHERE id_cliente = :user_id
"""

GET_USER_WITH_CACHE = """
    SELECT id_cliente, nombre_alias, email, credencial_externa,
           chatwoot_contact_id, chatwoot_conversation_id
    FROM clientes_activos
    WHERE session_token = :token
"""
```

**2. Modificar `session.py` (start_session)**

Después de obtener `contact_id` y `conversation_id`:

```python
# Cachear IDs en BD
await database.execute(
    query=SQLQueries.UPDATE_CHATWOOT_CACHE,
    values={
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "user_id": user_db_id or existing_user['id_cliente']
    }
)
```

**3. Modificar `auth.py` (register)**

Después de buscar en Chatwoot:

```python
# Cachear IDs después de la búsqueda
await database.execute(
    query=SQLQueries.UPDATE_CHATWOOT_CACHE,
    values={
        "contact_id": contact_id,
        "conversation_id": conversation_id,
        "user_id": user["id_cliente"]
    }
)
```

**4. Modificar `messages.py` (send_message y get_messages)**

Eliminar función `get_chatwoot_conversation_id()` y usar caché:

```python
async def send_message(request: SendMessageRequest, x_session_token: str = Header(None)):
    user = await get_user_by_token(x_session_token)  # Ahora incluye IDs cacheados
    
    conversation_id = user["chatwoot_conversation_id"]
    
    if not conversation_id:
        # Fallback: buscar y cachear
        conversation_id = await find_and_cache_conversation_id(user)
    
    # Solo 1 llamada HTTP
    resp = requests.post(
        f"{settings.chatwoot.base_url}/.../messages",
        json={"content": request.content, "message_type": "incoming"},
        headers=get_headers()
    )
```

**Resultado Esperado:**

```
ANTES: 3 HTTP calls → ~1500ms
DESPUÉS: 1 HTTP call → ~500ms
MEJORA: 66% más rápido ✅
```

---

### Fase 2: Migrar a httpx Async (PRIORIDAD ALTA)

**Objetivo:** No bloquear el event loop de FastAPI

#### Cambios Necesarios

**1. Agregar httpx a requirements**

```txt
httpx==0.27.0
```

**2. Reemplazar requests por httpx**

```python
# ANTES
import requests
resp = requests.get(url, headers=headers)

# DESPUÉS
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get(url, headers=headers)
```

**3. Crear cliente HTTP reutilizable**

```python
# private/http_client.py
import httpx
from private.config_loader import settings

class ChatwootClient:
    def __init__(self):
        self.base_url = settings.chatwoot.base_url
        self.headers = {
            "api_access_token": settings.chatwoot.api_token,
            "Content-Type": "application/json"
        }
    
    async def get(self, endpoint: str):
        async with httpx.AsyncClient() as client:
            return await client.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                timeout=10.0
            )
    
    async def post(self, endpoint: str, json_data: dict):
        async with httpx.AsyncClient() as client:
            return await client.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=json_data,
                timeout=10.0
            )
```

**Resultado Esperado:**

```
ANTES: Bloquea event loop → otros usuarios esperan
DESPUÉS: Async → concurrencia real
MEJORA: Mejor throughput del servidor ✅
```

---

### Fase 3: Optimizar Polling (PRIORIDAD MEDIA)

**Objetivo:** Reducir carga en Chatwoot

#### Opciones

**Opción A: Polling Inteligente**

```javascript
// Aumentar intervalo cuando no hay actividad
let pollingInterval = 3000; // Inicial: 3s

function startPolling() {
    setInterval(() => {
        loadMessages();
        // Si no hay mensajes nuevos, aumentar intervalo
        if (noNewMessages) {
            pollingInterval = Math.min(pollingInterval * 1.5, 30000); // Max 30s
        } else {
            pollingInterval = 3000; // Reset a 3s
        }
    }, pollingInterval);
}
```

**Opción B: WebSockets (Ideal pero complejo)**

Requiere implementar servidor WebSocket o usar ActionCable de Chatwoot.

**Recomendación:** Opción A por ahora

---

### Fase 4: Mejorar Manejo de Errores (PRIORIDAD MEDIA)

**Objetivo:** Resiliencia ante fallos de Chatwoot

#### Implementaciones

**1. Retry Logic**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
async def send_to_chatwoot(endpoint, data):
    async with httpx.AsyncClient() as client:
        resp = await client.post(endpoint, json=data)
        resp.raise_for_status()
        return resp.json()
```

**2. Circuit Breaker**

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def get_from_chatwoot(endpoint):
    # Si falla 5 veces, abre el circuito por 60s
    ...
```

---

### Fase 5: Logging Estructurado (PRIORIDAD BAJA)

**Objetivo:** Logs útiles sin ruido

#### Implementación

```python
import structlog

logger = structlog.get_logger()

# ANTES
print(f"DEPURACIÓN: Usuario {user_id}", flush=True)

# DESPUÉS
logger.info("user_session_started", user_id=user_id, identifier=identifier)
```

---

## 📊 Comparativa: Antes vs Después

### Envío de Mensaje

| Métrica | Antes | Después (Fase 1) | Después (Fase 2) | Mejora |
|---------|-------|------------------|------------------|--------|
| HTTP Calls | 3 | 1 | 1 | -66% |
| Latencia | ~1500ms | ~500ms | ~400ms | -73% |
| Blocking | Sí | Sí | No | ✅ |
| Caché | No | Sí | Sí | ✅ |

### Inicio de Sesión Invitado

| Métrica | Antes | Después (Fase 1) | Después (Fase 2) | Mejora |
|---------|-------|------------------|------------------|--------|
| HTTP Calls | 3-5 | 3-5 | 3-5 | 0% (primera vez) |
| Latencia | ~2000ms | ~2000ms | ~1500ms | -25% |
| Caché | No | Sí | Sí | ✅ |
| Blocking | Sí | Sí | No | ✅ |

**Nota:** Primera sesión siempre será lenta (debe crear en Chatwoot), pero sesiones subsecuentes serán rápidas.

### Login de Usuario

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| HTTP Calls | 0 | 0 | - |
| Latencia | ~100ms | ~100ms | - |
| **Primera carga de mensajes** | ~1500ms | ~500ms | -66% ✅ |

---

## 🚀 Orden de Implementación Recomendado

### Sprint 1: Caché de IDs (1-2 días)

1. ✅ Ejecutar migración `001_add_chatwoot_cache.sql`
2. ✅ Actualizar `database.py` con queries de caché
3. ✅ Modificar `session.py` para cachear en start_session
4. ✅ Modificar `auth.py` para cachear en register
5. ✅ Modificar `messages.py` para usar caché
6. ✅ Testing manual
7. ✅ Deploy a desarrollo

**Resultado:** Latencia de mensajes de 1500ms → 500ms

---

### Sprint 2: Async HTTP (1 día)

1. ✅ Agregar httpx a requirements
2. ✅ Crear `http_client.py` con ChatwootClient
3. ✅ Reemplazar requests por httpx en todos los endpoints
4. ✅ Testing de concurrencia
5. ✅ Deploy a desarrollo

**Resultado:** Mejor throughput del servidor

---

### Sprint 3: Optimizaciones Adicionales (2 días)

1. ✅ Implementar polling inteligente en frontend
2. ✅ Agregar retry logic con tenacity
3. ✅ Implementar logging estructurado
4. ✅ Testing de resiliencia
5. ✅ Deploy a desarrollo

**Resultado:** Sistema más robusto y eficiente

---

## 🔍 Métricas de Éxito

### KPIs a Monitorear

| Métrica | Objetivo | Medición |
|---------|----------|----------|
| Latencia de envío | < 500ms | Promedio de tiempo de respuesta |
| Tasa de caché hit | > 95% | % de requests que usan caché |
| Errores de Chatwoot | < 1% | % de requests fallidos |
| Throughput | > 100 req/s | Requests concurrentes soportados |

### Herramientas de Monitoreo

```python
# Agregar métricas con prometheus_client
from prometheus_client import Counter, Histogram

chatwoot_requests = Counter('chatwoot_requests_total', 'Total requests to Chatwoot')
cache_hits = Counter('cache_hits_total', 'Total cache hits')
message_latency = Histogram('message_send_latency_seconds', 'Message send latency')
```

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Caché desincronizado | Media | Alto | Invalidar caché en errores 404 |
| Chatwoot caído | Baja | Crítico | Circuit breaker + fallback |
| Migración con datos existentes | Alta | Medio | Script de migración idempotente |
| Regresiones en funcionalidad | Media | Alto | Testing exhaustivo pre-deploy |

---

## 📝 Checklist de Implementación

### Antes de Empezar

- [ ] Backup de base de datos
- [ ] Documentar estado actual con métricas
- [ ] Crear rama de desarrollo `feature/optimize-login`

### Durante Implementación

- [ ] Ejecutar migración SQL
- [ ] Actualizar código según plan
- [ ] Testing unitario de funciones críticas
- [ ] Testing de integración con Chatwoot
- [ ] Validar métricas de rendimiento

### Después de Implementación

- [ ] Comparar métricas antes/después
- [ ] Monitorear logs por 24h
- [ ] Documentar cambios en README
- [ ] Merge a main con PR revisado

---

**Documento de planificación - NO MODIFICAR CÓDIGO HASTA APROBACIÓN**
