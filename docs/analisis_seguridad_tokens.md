# 🔐 Análisis de Seguridad: Sistema de Tokens y Exposición de Datos

**Fecha:** 2025-11-26  
**Severidad:** 🔴 ALTA  
**Estado:** Análisis (NO MODIFICAR CÓDIGO AÚN)

---

## 🚨 Problema Identificado

### Exposición Innecesaria de Datos en el Cliente

**Archivo:** `justibot_service/public/index.html`

```javascript
// ❌ PROBLEMA: Datos sensibles en localStorage del navegador
let sessionToken = localStorage.getItem('justibot_session_token');
let userName = localStorage.getItem('justibot_user_name');        // ⚠️ Innecesario
let isGuest = !localStorage.getItem('justibot_is_registered');    // ⚠️ Innecesario
let guestIdentifier = localStorage.getItem('justibot_guest_id');  // ⚠️ PELIGROSO
```

### ¿Por qué es un problema?

#### 1️⃣ **Violación del Principio de Mínimo Privilegio**

El cliente (navegador) **NO NECESITA** conocer:
- `userName` → Puede obtenerlo del backend con el token
- `isGuest` → El backend lo sabe por el estado del usuario
- `guestIdentifier` → **CRÍTICO**: Esto es un identificador interno de Chatwoot

#### 2️⃣ **Exposición de Identificadores Internos**

```javascript
guestIdentifier = localStorage.getItem('justibot_guest_id');  // ej: "guest_ABC123"
```

**Riesgo:**
- Un atacante puede ver este ID en DevTools
- Puede intentar hacerse pasar por otro usuario modificando el localStorage
- Expone la estructura interna de tu sistema

#### 3️⃣ **Token Generado en el Servidor (Correcto) pero Mal Usado**

**Actualmente:**
```javascript
// Backend genera el token ✅
session_token = secrets.token_urlsafe(32)

// Pero el frontend almacena datos redundantes ❌
localStorage.setItem('justibot_guest_id', guestIdentifier);
localStorage.setItem('justibot_user_name', userName);
localStorage.setItem('justibot_is_registered', 'true');
```

**Problema:** Si el token ya identifica al usuario, ¿para qué guardar más datos?

---

## 🎯 Arquitectura Correcta: Token-Only

### Principio Fundamental

```
┌─────────────────────────────────────────────────────────┐
│  EL ÚNICO DATO QUE EL CLIENTE DEBE ALMACENAR ES EL TOKEN │
└─────────────────────────────────────────────────────────┘
```

### Flujo Correcto

```
┌──────────────┐
│  NAVEGADOR   │
│              │
│ localStorage:│
│  - token     │ ← ÚNICO DATO
└──────┬───────┘
       │
       │ GET /api/me (con token en header)
       ▼
┌──────────────┐
│   BACKEND    │
│              │
│ Decodifica   │
│ token y      │
│ retorna:     │
│  - name      │
│  - email     │
│  - isGuest   │
│  - etc.      │
└──────────────┘
```

---

## 🔍 Análisis Detallado del Código Actual

### 1. Inicio de Sesión Invitado

**Backend (`session.py`):**
```python
# ✅ CORRECTO: Genera token seguro
session_token = secrets.token_urlsafe(32)

# ✅ CORRECTO: Guarda en BD
await create_guest_user(identifier, session_token)

# ❌ PROBLEMA: Envía datos innecesarios al cliente
return {
    "token": session_token,      # ✅ Necesario
    "user_name": identifier       # ❌ Innecesario (puede obtenerse con el token)
}
```

**Frontend (`index.html`):**
```javascript
const data = await response.json();
sessionToken = data.token;           // ✅ Necesario
userName = data.user_name;           // ❌ Innecesario

// ❌ PROBLEMA: Almacena datos derivados
localStorage.setItem('justibot_session_token', sessionToken);
localStorage.setItem('justibot_user_name', userName);        // ❌
localStorage.removeItem('justibot_is_registered');           // ❌

// ❌ CRÍTICO: Almacena identificador interno
if (userName.startsWith('guest_')) {
    guestIdentifier = userName;
    localStorage.setItem('justibot_guest_id', guestIdentifier);  // 🚨
}
```

### 2. Login de Usuario

**Backend (`auth.py`):**
```python
# ✅ CORRECTO
session_token = secrets.token_urlsafe(32)
await update_session_token(user["id_cliente"], session_token)

# ❌ PROBLEMA: Envía nombre al cliente
return {
    "token": session_token,
    "name": user["nombre_alias"]  # ❌ Innecesario
}
```

**Frontend:**
```javascript
sessionToken = data.token;
userName = data.name;           // ❌ Innecesario
isGuest = false;                // ❌ Innecesario

localStorage.setItem('justibot_session_token', sessionToken);
localStorage.setItem('justibot_user_name', userName);        // ❌
localStorage.setItem('justibot_is_registered', 'true');      // ❌
```

### 3. Registro

**Frontend:**
```javascript
// ❌ PROBLEMA: Modifica estado local en lugar de confiar en el backend
isGuest = false;
localStorage.setItem('justibot_is_registered', 'true');
localStorage.removeItem('justibot_guest_id');
```

**Riesgo:** El cliente puede mentir sobre su estado.

---

## 🛡️ Solución Propuesta: Arquitectura Token-Only

### Cambios en el Backend

#### 1. Crear Endpoint `/api/me`

**Archivo:** `justibot_service/private/endpoints/auth.py`

```python
@router.get("/auth/me")
async def get_current_user(x_session_token: str = Header(None)):
    """
    Retorna información del usuario actual basado en el token.
    El cliente NO debe almacenar esta información.
    """
    if not x_session_token:
        raise HTTPException(status_code=401, detail="Token faltante")
    
    user = await get_user_by_token(x_session_token)
    if not user:
        raise HTTPException(status_code=401, detail="Sesión inválida")
    
    return {
        "id": user["id_cliente"],
        "name": user["nombre_alias"],
        "email": user["email"],
        "is_guest": user["email"] is None,  # Si no tiene email, es invitado
        "estado_ciclo": user["estado_ciclo"]
    }
```

#### 2. Modificar Respuestas de Autenticación

**`session.py` - start_session:**
```python
# ANTES
return {"token": session_token, "user_name": identifier}

# DESPUÉS
return {"token": session_token}  # Solo el token
```

**`auth.py` - login:**
```python
# ANTES
return {"token": session_token, "name": user["nombre_alias"]}

# DESPUÉS
return {"token": session_token}  # Solo el token
```

**`auth.py` - register:**
```python
# ANTES
return {"status": "ok", "name": request.name}

# DESPUÉS
return {"status": "ok"}  # Sin datos del usuario
```

### Cambios en el Frontend

#### 1. Simplificar localStorage

**ANTES:**
```javascript
let sessionToken = localStorage.getItem('justibot_session_token');
let userName = localStorage.getItem('justibot_user_name');
let isGuest = !localStorage.getItem('justibot_is_registered');
let guestIdentifier = localStorage.getItem('justibot_guest_id');
```

**DESPUÉS:**
```javascript
let sessionToken = localStorage.getItem('justibot_session_token');
// ¡Eso es todo! No más datos locales
```

#### 2. Crear Función para Obtener Datos del Usuario

```javascript
let currentUser = null;  // Cache en memoria (no en localStorage)

async function fetchCurrentUser() {
    if (!sessionToken) return null;
    
    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'X-Session-Token': sessionToken }
        });
        
        if (!response.ok) {
            // Token inválido
            sessionToken = null;
            localStorage.removeItem('justibot_session_token');
            return null;
        }
        
        currentUser = await response.json();
        return currentUser;
    } catch (error) {
        console.error("Error obteniendo usuario:", error);
        return null;
    }
}
```

#### 3. Actualizar Flujo de Inicio

```javascript
async function updateUIState() {
    if (!sessionToken) {
        // Auto-start guest session
        await initGuestSession();
        return;
    }
    
    // Obtener datos del usuario desde el backend
    const user = await fetchCurrentUser();
    
    if (!user) {
        // Token inválido, reiniciar sesión
        await initGuestSession();
        return;
    }
    
    // Actualizar UI basado en datos del backend
    if (user.is_guest) {
        authButtons.style.display = 'block';
        btnLogout.style.display = 'none';
        guestWarning.style.display = 'block';
    } else {
        authButtons.style.display = 'none';
        btnLogout.style.display = 'block';
        guestWarning.style.display = 'none';
    }
    
    enableChat();
    loadMessages();
    startPolling();
}
```

#### 4. Actualizar Funciones de Autenticación

**Login:**
```javascript
async function doLogin() {
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) throw new Error('Credenciales incorrectas');

        const data = await response.json();
        sessionToken = data.token;  // Solo guardamos el token
        localStorage.setItem('justibot_session_token', sessionToken);

        closeModals();
        await updateUIState();  // Obtiene datos del usuario desde el backend
        
        // Obtener nombre para el mensaje
        const user = await fetchCurrentUser();
        alert(`Bienvenido de nuevo, ${user.name}`);

    } catch (error) {
        alert(error.message);
    }
}
```

**Registro:**
```javascript
async function doRegister() {
    const name = document.getElementById('regName').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;

    if (!sessionToken) await initGuestSession();

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-Token': sessionToken
            },
            body: JSON.stringify({ name, email, password })
        });

        if (!response.ok) throw new Error('Error en registro');

        closeModals();
        await updateUIState();  // Obtiene datos actualizados del backend
        alert('Cuenta creada exitosamente');

    } catch (error) {
        alert(error.message);
    }
}
```

**Inicio de Sesión Invitado:**
```javascript
async function initGuestSession() {
    try {
        const payload = {};
        // ❌ ELIMINAR: No enviar guestIdentifier
        // if (guestIdentifier) {
        //     payload.contact_identifier = guestIdentifier;
        // }

        const response = await fetch(`${API_BASE}/session/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Error iniciando sesión');

        const data = await response.json();
        sessionToken = data.token;  // Solo el token
        localStorage.setItem('justibot_session_token', sessionToken);

        await updateUIState();  // Obtiene datos del usuario

    } catch (error) {
        console.error(error);
        messagesList.innerHTML = '<div style="text-align: center; color: red;">Error de conexión</div>';
    }
}
```

---

## 🔒 Beneficios de Seguridad

### 1. Principio de Mínimo Privilegio

| Antes | Después |
|-------|---------|
| Cliente conoce: token, nombre, email, estado, ID interno | Cliente conoce: **solo token** |
| Datos en localStorage (persistentes) | Solo token en localStorage |
| Datos en memoria (volátiles) | Datos obtenidos on-demand |

### 2. Prevención de Manipulación

**ANTES:**
```javascript
// ❌ Atacante puede hacer:
localStorage.setItem('justibot_is_registered', 'true');
localStorage.setItem('justibot_user_name', 'Admin');
// Y el frontend confía en estos datos
```

**DESPUÉS:**
```javascript
// ✅ Atacante no puede manipular nada
// Todos los datos vienen del backend validado por el token
```

### 3. Reducción de Superficie de Ataque

**Datos expuestos en DevTools:**

| Antes | Después |
|-------|---------|
| `justibot_session_token` | `justibot_session_token` |
| `justibot_user_name` | ❌ Eliminado |
| `justibot_is_registered` | ❌ Eliminado |
| `justibot_guest_id` | ❌ Eliminado |

### 4. Consistencia de Estado

**ANTES:**
```
Backend: usuario es invitado
Frontend: localStorage dice que es registrado
Resultado: Inconsistencia 🚨
```

**DESPUÉS:**
```
Backend: usuario es invitado
Frontend: Pregunta al backend → es invitado
Resultado: Siempre consistente ✅
```

---

## 🎯 Generación de Token: ¿Cliente o Servidor?

### Tu Pregunta Original

> "el token debería generarse en la maquina local del usuario usando javascript"

### Respuesta: **NO, debe generarse en el servidor**

#### ¿Por qué?

**1. Seguridad Criptográfica**

```javascript
// ❌ INSEGURO: Token generado en el cliente
const clientToken = Math.random().toString(36);  // Predecible
const clientToken2 = Date.now().toString();      // Predecible
const clientToken3 = crypto.randomUUID();        // Mejor, pero...
```

**Problemas:**
- El cliente puede generar tokens predecibles
- No hay validación de unicidad
- No hay control de expiración

```python
# ✅ SEGURO: Token generado en el servidor
import secrets
server_token = secrets.token_urlsafe(32)  # 256 bits de entropía
```

**Ventajas:**
- Entropía criptográficamente segura
- Unicidad garantizada (verificada en BD)
- Control total del ciclo de vida

**2. Validación y Control**

| Aspecto | Cliente | Servidor |
|---------|---------|----------|
| Unicidad | ❌ No verificable | ✅ Verificada en BD |
| Expiración | ❌ No controlable | ✅ Controlada |
| Revocación | ❌ Imposible | ✅ Posible |
| Auditoría | ❌ No rastreable | ✅ Rastreable |

**3. Arquitectura Stateless Correcta**

```
┌──────────────┐
│  CLIENTE     │
│              │
│ 1. Solicita  │
│    sesión    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  SERVIDOR    │
│              │
│ 2. Genera    │
│    token     │
│    seguro    │
│              │
│ 3. Guarda en │
│    BD        │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  CLIENTE     │
│              │
│ 4. Recibe y  │
│    almacena  │
│    token     │
└──────────────┘
```

**Conclusión:** El servidor **DEBE** generar el token, pero el cliente **SOLO** debe almacenar el token (nada más).

---

## 📊 Comparativa: Antes vs Después

### localStorage

**ANTES:**
```javascript
{
  "justibot_session_token": "abc123...",
  "justibot_user_name": "Invitado guest_",
  "justibot_is_registered": null,
  "justibot_guest_id": "guest_ABC123"
}
```

**DESPUÉS:**
```javascript
{
  "justibot_session_token": "abc123..."
}
```

**Reducción:** 75% menos datos expuestos

### Flujo de Autenticación

**ANTES:**
```
1. Login → Recibe {token, name}
2. Guarda en localStorage: token, name, is_registered
3. UI lee de localStorage
4. ⚠️ Datos pueden estar desincronizados
```

**DESPUÉS:**
```
1. Login → Recibe {token}
2. Guarda en localStorage: token
3. GET /api/me → Recibe {name, email, is_guest}
4. UI usa datos frescos del backend
5. ✅ Siempre sincronizado
```

---

## 🚀 Plan de Implementación

### Fase 1: Backend (Sin Romper Compatibilidad)

1. ✅ Crear endpoint `/api/auth/me`
2. ✅ Mantener respuestas actuales (compatibilidad)
3. ✅ Testing del nuevo endpoint

### Fase 2: Frontend (Migración Gradual)

1. ✅ Agregar función `fetchCurrentUser()`
2. ✅ Usar `/api/me` en lugar de localStorage
3. ✅ Mantener localStorage antiguo (fallback)
4. ✅ Testing de compatibilidad

### Fase 3: Limpieza

1. ✅ Eliminar campos innecesarios de respuestas del backend
2. ✅ Eliminar localStorage antiguo del frontend
3. ✅ Limpiar localStorage de usuarios existentes

### Fase 4: Validación

1. ✅ Testing de seguridad
2. ✅ Validar que no hay datos sensibles expuestos
3. ✅ Auditoría de código

---

## 🔍 Checklist de Seguridad

### Datos en el Cliente

- [ ] ✅ Solo `session_token` en localStorage
- [ ] ❌ No `user_name` en localStorage
- [ ] ❌ No `is_registered` en localStorage
- [ ] ❌ No `guest_id` en localStorage
- [ ] ❌ No IDs internos de Chatwoot expuestos

### Generación de Tokens

- [ ] ✅ Tokens generados en el servidor
- [ ] ✅ Usa `secrets.token_urlsafe(32)` (256 bits)
- [ ] ✅ Tokens únicos verificados en BD
- [ ] ✅ Tokens almacenados hasheados (opcional, futuro)

### Validación

- [ ] ✅ Endpoint `/api/me` implementado
- [ ] ✅ Todas las operaciones validan token
- [ ] ✅ Token en header (no en URL)
- [ ] ✅ Respuestas no incluyen datos sensibles

---

## ⚠️ Riesgos del Estado Actual

| Riesgo | Severidad | Probabilidad | Impacto |
|--------|-----------|--------------|---------|
| Manipulación de `is_registered` | 🟡 Media | Alta | Usuario puede verse como registrado |
| Exposición de `guest_id` | 🔴 Alta | Alta | Atacante puede enumerar usuarios |
| Inconsistencia de estado | 🟡 Media | Media | Bugs difíciles de debuggear |
| Datos sensibles en DevTools | 🟢 Baja | Alta | Información innecesaria expuesta |

---

## ✅ Conclusión

### Problema Principal

**El cliente almacena y confía en datos que deberían ser solo del servidor.**

### Solución

**Token-Only Architecture:**
1. Cliente solo almacena el token
2. Todos los datos se obtienen del backend con el token
3. Backend es la única fuente de verdad

### Beneficios

- ✅ Seguridad mejorada
- ✅ Consistencia garantizada
- ✅ Menor superficie de ataque
- ✅ Más fácil de mantener

---

**PRÓXIMO PASO:** Implementar endpoint `/api/me` y migrar frontend gradualmente
