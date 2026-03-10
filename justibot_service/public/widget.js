document.addEventListener('DOMContentLoaded', () => {
    const api = new ChatwootAPI(window.JustibotConfig);

    // Elementos DOM
    const launcher = document.getElementById('justibot-launcher');
    const container = document.getElementById('justibot-container');
    const closeBtn = document.getElementById('close-btn');
    const startScreen = document.getElementById('start-screen');
    const chatScreen = document.getElementById('chat-screen');
    const startBtn = document.getElementById('start-chat-btn');
    const nameInput = document.getElementById('user-name');
    const emailInput = document.getElementById('user-email');
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesList = document.getElementById('messages-list');

    let isChatOpen = false;
    let pollingInterval = null;
    let lastMessageId = 0;

    // Toggle Chat
    function toggleChat() {
        isChatOpen = !isChatOpen;
        container.classList.toggle('open', isChatOpen);
        if (isChatOpen && api.conversation) {
            scrollToBottom();
            startPolling();
        } else {
            stopPolling();
        }
    }

    launcher.addEventListener('click', toggleChat);
    closeBtn.addEventListener('click', toggleChat);

    // Iniciar Chat
    startBtn.addEventListener('click', async () => {
        const name = nameInput.value.trim();
        const email = emailInput.value.trim();

        if (!name || !email) {
            alert("Por favor ingresa tu nombre y correo.");
            return;
        }

        startBtn.disabled = true;
        startBtn.innerText = "Iniciando...";

        try {
            // 1. Crear Contacto
            await api.createContact(name, email);
            // 2. Crear Conversación
            await api.createConversation();

            // UI Switch
            startScreen.classList.add('hidden');
            chatScreen.classList.remove('hidden');

            // Iniciar Polling
            startPolling();

        } catch (error) {
            console.error(error);
            alert("Error al iniciar el chat. Verifica la configuración.");
            startBtn.disabled = false;
            startBtn.innerText = "Iniciar Chat";
        }
    });

    // Enviar Mensaje
    async function sendMessage() {
        const content = messageInput.value.trim();
        if (!content) return;

        // Optimistic UI: Mostrar mensaje inmediatamente
        addMessageToUI({ content, message_type: 0, created_at: Date.now() / 1000 }, true);
        messageInput.value = '';

        try {
            await api.sendMessage(content);
            // El polling actualizará el estado real
        } catch (error) {
            console.error("Error sending message:", error);
            alert("No se pudo enviar el mensaje.");
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    // Polling de Mensajes
    function startPolling() {
        if (pollingInterval) return;
        fetchMessages(); // Primera llamada inmediata
        pollingInterval = setInterval(fetchMessages, window.JustibotConfig.POLLING_INTERVAL);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    async function fetchMessages() {
        try {
            const messages = await api.getMessages();
            // Filtrar mensajes nuevos
            const newMessages = messages.filter(m => m.id > lastMessageId);

            if (newMessages.length > 0) {
                // Ordenar por ID ascendente (antiguos primero)
                newMessages.sort((a, b) => a.id - b.id);

                newMessages.forEach(msg => {
                    // Evitar duplicados si ya los mostramos optimísticamente (simple check)
                    // En una app real, usaríamos IDs temporales para deducir.
                    // Aquí simplemente limpiamos y repintamos o añadimos solo los entrantes.
                    // Para simplicidad: Si es incoming (1) lo añadimos. Si es outgoing (0), asumimos que ya está o lo actualizamos.
                    // Mejor enfoque simple: Añadir solo si ID > lastMessageId
                    addMessageToUI(msg);
                    lastMessageId = Math.max(lastMessageId, msg.id);
                });
                scrollToBottom();
            }
        } catch (error) {
            console.error("Polling error:", error);
        }
    }

    function addMessageToUI(msg, isOptimistic = false) {
        // message_type: 0 = outgoing (cliente), 1 = incoming (agente)
        const type = msg.message_type === 0 ? 'outgoing' : 'incoming';

        // Si es optimista, no chequeamos duplicados por ID
        if (!isOptimistic) {
            // Check si ya existe (por si acaso)
            const exists = document.querySelector(`[data-msg-id="${msg.id}"]`);
            if (exists) return;
        }

        const div = document.createElement('div');
        div.className = `message ${type}`;
        if (msg.id) div.dataset.msgId = msg.id;
        div.innerText = msg.content;

        messagesList.appendChild(div);
    }

    function scrollToBottom() {
        messagesList.scrollTop = messagesList.scrollHeight;
    }
});
