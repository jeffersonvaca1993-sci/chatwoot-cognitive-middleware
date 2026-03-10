
const API_BASE = '/api';
let sessionToken = localStorage.getItem('justibot_session_token');
let userName = localStorage.getItem('justibot_user_name');
let isGuest = !localStorage.getItem('justibot_is_registered');

const messagesList = document.getElementById('messagesList');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const authButtons = document.getElementById('authButtons');
const btnLogout = document.getElementById('btnLogout');
const guestWarning = document.getElementById('guestWarning');

// --- Init ---

// FORCE RESET: Versión para obligar a limpiar caché antigua
const CLIENT_VERSION = 'v1.1-force-reset';

function checkClientVersion() {
    const current = localStorage.getItem('justibot_client_version');
    if (current !== CLIENT_VERSION) {
        console.log("Detectada versión antigua o corrupta. Limpiando sesión...");
        localStorage.clear();
        localStorage.setItem('justibot_client_version', CLIENT_VERSION);
        // Recargar para iniciar limpio
        location.reload();
    }
}

// Ejecutar limpieza antes de nada
checkClientVersion();

function updateUIState() {
    if (sessionToken) {
        if (isGuest) {
            if (authButtons) authButtons.style.display = 'block';
            if (btnLogout) btnLogout.style.display = 'none';
            if (guestWarning) guestWarning.style.display = 'block';
        } else {
            if (authButtons) authButtons.style.display = 'none';
            if (btnLogout) btnLogout.style.display = 'block';
            if (guestWarning) guestWarning.style.display = 'none';
        }

        const userDisplay = document.getElementById('currentUserDisplay');
        if (userDisplay) {
            console.log("Updating UI with User:", userName);
            userDisplay.textContent = userName || 'Visitante (Sin Nombre)';
        }

        enableChat();
        loadMessages();
        connectWebSocket(); // Use WS instead of polling
    } else {
        // Auto-start guest session
        initGuestSession();
    }
}

async function initGuestSession() {
    try {
        const response = await fetch(`${API_BASE}/auth/guest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) throw new Error('Error iniciando sesión');

        const data = await response.json();
        sessionToken = data.token;
        userName = data.nombre;
        isGuest = true;

        localStorage.setItem('justibot_session_token', sessionToken);
        localStorage.setItem('justibot_user_name', userName);
        localStorage.removeItem('justibot_is_registered');

        if (data.pubsub_token) {
            localStorage.setItem('justibot_pubsub_token', data.pubsub_token);
        }

        updateUIState();

    } catch (error) {
        console.error(error);
        if (messagesList) messagesList.innerHTML = '<div style="text-align: center; color: red;">Error de conexión</div>';
    }
}

function doLogout() {
    if (confirm('¿Cerrar sesión?')) {
        localStorage.clear();
        location.reload();
    }
}

// --- Chat Functions ---

async function loadMessages() {
    if (!sessionToken) return;
    try {
        const response = await fetch(`${API_BASE}/messages`, {
            headers: { 'X-Session-Token': sessionToken }
        });

        if (response.status === 401) {
            handleSessionExpired();
            return;
        }

        if (response.ok) {
            const messages = await response.json();
            renderMessages(messages);
        }
    } catch (error) {
        console.error("Error cargando mensajes:", error);
        if (messagesList) messagesList.innerHTML = '<div style="text-align: center; color: red; margin-top: 20px;">Error cargando historial</div>';
    }
}

async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content || !sessionToken) return;

    // Optimistic UI update
    addMessageToUI(content, 'incoming');
    messageInput.value = '';

    try {
        const response = await fetch(`${API_BASE}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-Token': sessionToken
            },
            body: JSON.stringify({ content })
        });

        if (response.status === 401) {
            console.warn("Sesión expirada. Intentando reconectar...");
            await handleSessionExpired();
            return;
        }

        if (!response.ok) {
            alert('Error enviando mensaje');
        } else {
            // WS handles update
        }
    } catch (error) {
        console.error(error);
        alert('Error de red');
    }
}

function enableChat() {
    if (messageInput) messageInput.disabled = false;
    if (sendButton) sendButton.disabled = false;
}

function renderMessages(messages) {
    if (!messagesList) return;
    messagesList.innerHTML = '';
    messages.forEach(msg => {
        const type = msg.es_mio ? 'incoming' : 'outgoing';
        addMessageToUI(msg.contenido, type);
    });
    scrollToBottom();
}

function addMessageToUI(text, type) {
    if (!messagesList) return;
    const div = document.createElement('div');
    div.className = `message ${type}`;
    div.textContent = text;
    messagesList.appendChild(div);
}

function scrollToBottom() {
    if (messagesList) messagesList.scrollTop = messagesList.scrollHeight;
}

// --- WebSocket ---
let ws;
let wsConfig = {};

async function fetchConfig() {
    try {
        const res = await fetch(`${API_BASE}/auth/config`);
        if (res.ok) {
            wsConfig = await res.json();
            console.log("Config loaded:", wsConfig);
        }
    } catch (e) {
        console.error("Error loading config:", e);
    }
}

function connectWebSocket() {
    if (!sessionToken || !wsConfig.chatwoot_ws_url) return;

    const protocol = location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${protocol}${location.host}${wsConfig.chatwoot_ws_url}?token=${sessionToken}`;

    // --- VISUAL DEBUGGER ---
    function logToChat(msg) {
        if (!messagesList) return;
        const div = document.createElement('div');
        div.style.color = 'red';
        div.style.fontSize = '10px';
        div.style.padding = '2px';
        div.style.fontFamily = 'monospace';
        div.textContent = `[DEBUG] ${msg}`;
        messagesList.appendChild(div);
        scrollToBottom();
    }

    console.log("Connecting to WS:", wsUrl);
    logToChat(`Intentando conectar WS: ${wsUrl}`);

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log("WS Connected (Bridge Mode)");
        logToChat("WS Conectado (Bridge Mode)");

        // Ya no necesitamos suscribirnos a ActionCable.
        // Solo mantenemos vivo el socket
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                // logToChat("Ping enviado..."); // Comentado para no spamear
                ws.send("ping");
            }
        }, 30000);
    };

    ws.onmessage = (event) => {
        // Ignorar pongs
        if (event.data === "pong") return;

        logToChat(`Raw Data: ${event.data}`);

        try {
            const data = JSON.parse(event.data);

            // Nuevo protocolo simple: { type: "new_message", content: "..." }
            if (data.type === "new_message") {
                console.log("Mensaje recibido por Webhook Bridge:", data);
                logToChat("Procesando 'new_message'...");
                addMessageToUI(data.content, 'outgoing');
                scrollToBottom();
            } else {
                logToChat(`Ignorando tipo: ${data.type}`);
            }

        } catch (e) {
            console.error("Error parsing WS data:", e);
            logToChat(`Error JSON: ${e.message}`);
        }
    };

    ws.onclose = () => {
        console.log("WS Disconnected");
        // Simple reconnect logic
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (err) => {
        console.error("WS Error:", err);
    };
}

async function handleSessionExpired() {
    localStorage.removeItem('justibot_session_token');
    localStorage.removeItem('justibot_pubsub_token');
    sessionToken = null;
    if (ws) ws.close();

    if (!isGuest) {
        alert("Tu sesión ha expirado. Por favor ingresa nuevamente.");
        location.href = 'login.html';
    } else {
        await initGuestSession();
    }
}

// Event Listeners
if (sendButton) sendButton.addEventListener('click', sendMessage);
if (messageInput) messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Start
document.addEventListener('DOMContentLoaded', async () => {
    await fetchConfig();
    updateUIState();
});
