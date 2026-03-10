# ☢️ PROTOCOLO NUCLEAR: Reseteo Total de Chatwoot & Justibot

Este documento explica cómo borrar **TODO** y reconfigurar el sistema desde cero.
Usa esto solo si la base de datos está corrupta o quieres iniciar una instalación limpia (ej. Producción).

---

## 🛑 PASO 1: DETONACIÓN (Borrado Total)

Abre la terminal en la carpeta del proyecto y ejecuta:

```powershell
# 1. Detener servicios y borrar volúmenes de datos (ELIMINA TODA LA INFO)
docker-compose down -v
```

> ⚠️ **ADVERTENCIA:** Esto eliminará usuarios, conversaciones, configuraciones y datos de PostgreSQL. No hay vuelta atrás.

---

## 🏗️ PASO 2: RECONSTRUCCIÓN (Infraestructura)

```powershell
# 1. Instalar el esquema de Base de Datos de Chatwoot
docker-compose --profile setup up chatwoot_installer

# 2. Levantar los servicios (Chatwoot, Postgres, Redis, Justibot)
docker-compose up -d

# 3. Restaurar tablas de Justibot (Schema propio)
# Copia y pega este comando completo:
docker-compose exec -T postgres psql -U postgres -d chatwoot_production -c "
DO \$\$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_ciclo_cliente') THEN
        CREATE TYPE estado_ciclo_cliente AS ENUM ('prospecto', 'activo', 'riesgo', 'baja');
    END IF;
END \$\$;
CREATE TABLE IF NOT EXISTS clientes_activos (
    id_cliente SERIAL PRIMARY KEY,
    credencial_externa TEXT UNIQUE NOT NULL,
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    nombre_alias TEXT DEFAULT 'Cliente',
    contexto_vivo JSONB DEFAULT '{}'::jsonb,
    estado_ciclo estado_ciclo_cliente DEFAULT 'prospecto',
    ultima_actividad TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    email TEXT UNIQUE,
    password_hash TEXT,
    session_token TEXT UNIQUE,
    chatwoot_contact_id INTEGER,
    chatwoot_conversation_id INTEGER,
    chatwoot_pubsub_token TEXT
);"
```

---

## 🔧 PASO 3: CONFIGURACIÓN MANUAL (Chatwoot UI)

1.  **Entra a Chatwoot:**
    *   Ve a `https://chat.sci-vacasantana.org` (o tu dominio público si el túnel está activo).
    *   Crea una cuenta nueva (será el Administrador).

2.  **Crear bandeja de entrada (Inbox):**
    *   Ve a **Ajustes** -> **Bandejas de entrada** -> **Añadir bandeja**.
    *   Elige **"API"**.
    *   Nombre: `Justibot API`.
    *   Webhook URL: (Déjalo vacío por ahora).
    *   Finaliza la creación.

3.  **Obtener Credenciales (IMPORTANTE):**
    *   **Account ID:** Mira la URL de tu navegador. Si es `.../app/accounts/3/...`, tu ID es `3`.
    *   **API Token:** Ve a **Ajustes de Perfil** (abajo izquierda) -> **Token de acceso**. Copialo.
    *   **Inbox Identifier:** Abre la terminal y ejecuta esto para ver el código secreto de tu nueva bandeja:
        ```powershell
        docker-compose exec postgres psql -U postgres -d chatwoot_production -c "SELECT identifier FROM channel_api ORDER BY id DESC LIMIT 1;"
        ```
        *(Copia el código alfanumérico que salga, ej: `rBfq...`)*

4.  **Crear el Webhook (El Puente):**
    *   Ve a **Ajustes** -> **Integraciones** -> **Webhooks**.
    *   **Añadir nuevo webhook**.
    *   URL: `https://justibot.sci-vacasantana.org/api/ws/webhook` (Usa tu dominio público real).
    *   Eventos: Marca **Message Created** y **Conversation Updated**.
    *   Guardar.

---

## 📝 PASO 4: ACTUALIZAR JUSTIBOT

Edita tus archivos de configuración con los datos nuevos del Paso 3.

**Archivo `.env`:**
```ini
CHATWOOT_ACCOUNT_ID=3               # Tu ID de cuenta (ej. 1, 2, 3)
CHATWOOT_API_TOKEN=tu_token_aqui    # El token de perfil que copiaste
CHATWOOT_INBOX_ID=codigo_rBfq...    # El código Identifier de la bandeja
```

**Archivo `config.toml`:**
```toml
[chatwoot]
# ...
account_id = 3
inbox_id = "codigo_rBfq..."         # Asegúrate que coincida
```

---

## 🚀 PASO 5: REINICIO FINAL

Aplica los cambios para que Justibot conecte con el nuevo cerebro.

```powershell
docker-compose up -d --force-recreate justibot
```

¡Listo! 🎉 El sistema está reseteado y conectado.
