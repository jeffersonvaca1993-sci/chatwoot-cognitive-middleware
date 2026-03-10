/**
 * Cliente API para Chatwoot (Public Client API)
 * Referencia: https://developers.chatwoot.com/api-reference/
 */
class ChatwootAPI {
    constructor(config) {
        this.baseUrl = config.CHATWOOT_BASE_URL;
        this.inboxId = config.INBOX_IDENTIFIER;
        this.contact = null;
        this.conversation = null;
    }

    /**
     * Crea un contacto nuevo o recupera uno existente (basado en cookies/localStorage si implementáramos persistencia)
     */
    async createContact(name, email) {
        const url = `${this.baseUrl}/public/api/v1/inboxes/${this.inboxId}/contacts`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email })
            });

            if (!response.ok) throw new Error(`Error creating contact: ${response.status}`);

            const data = await response.json();
            // Guardamos source_id (contact_identifier) y pubsub_token
            this.contact = {
                id: data.source_id,
                pubsub_token: data.pubsub_token,
                name: data.name,
                email: data.email
            };
            console.log("Contact created:", this.contact);
            return this.contact;
        } catch (error) {
            console.error("API Error:", error);
            throw error;
        }
    }

    /**
     * Crea una nueva conversación para el contacto actual
     */
    async createConversation() {
        if (!this.contact) throw new Error("Contact not initialized");

        const url = `${this.baseUrl}/public/api/v1/inboxes/${this.inboxId}/contacts/${this.contact.id}/conversations`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error(`Error creating conversation: ${response.status}`);

            const data = await response.json();
            this.conversation = { id: data.id };
            console.log("Conversation created:", this.conversation);
            return this.conversation;
        } catch (error) {
            console.error("API Error:", error);
            throw error;
        }
    }

    /**
     * Envía un mensaje a la conversación actual
     */
    async sendMessage(content) {
        if (!this.contact || !this.conversation) throw new Error("Session not initialized");

        const url = `${this.baseUrl}/public/api/v1/inboxes/${this.inboxId}/contacts/${this.contact.id}/conversations/${this.conversation.id}/messages`;
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });

            if (!response.ok) throw new Error(`Error sending message: ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error("API Error:", error);
            throw error;
        }
    }

    /**
     * Obtiene los mensajes de la conversación actual
     */
    async getMessages() {
        if (!this.contact || !this.conversation) return [];

        const url = `${this.baseUrl}/public/api/v1/inboxes/${this.inboxId}/contacts/${this.contact.id}/conversations/${this.conversation.id}/messages`;
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Error fetching messages: ${response.status}`);
            const data = await response.json();
            return data; // Array de mensajes
        } catch (error) {
            console.error("API Error:", error);
            return [];
        }
    }
}

window.ChatwootAPI = ChatwootAPI;
