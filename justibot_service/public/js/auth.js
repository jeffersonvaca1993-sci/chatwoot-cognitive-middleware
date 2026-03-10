const API_BASE = '/api';

async function doLogin(email, password) {
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) throw new Error('Credenciales incorrectas');

        const data = await response.json();

        localStorage.setItem('justibot_session_token', data.token);
        localStorage.setItem('justibot_user_name', data.nombre);
        localStorage.setItem('justibot_is_registered', 'true');
        localStorage.removeItem('justibot_guest_id');

        if (data.pubsub_token) {
            localStorage.setItem('justibot_pubsub_token', data.pubsub_token);
        }

        return data;
    } catch (error) {
        throw error;
    }
}

async function doRegister(nombre, email, password) {
    let sessionToken = localStorage.getItem('justibot_session_token');

    if (!sessionToken) {
        try {
            const response = await fetch(`${API_BASE}/auth/guest`, { method: 'POST' });
            if (response.ok) {
                const data = await response.json();
                sessionToken = data.token;
                // Don't save to localStorage yet? Or yes?
                // Better save it, in case register fails, we have a session.
                localStorage.setItem('justibot_session_token', sessionToken);
                if (data.pubsub_token) {
                    localStorage.setItem('justibot_pubsub_token', data.pubsub_token);
                }
            }
        } catch (e) {
            console.error("Error init guest for register", e);
            throw new Error("No se pudo inicializar sesión para registro.");
        }
    }

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'guest_jwt': sessionToken
            },
            body: JSON.stringify({ nombre, email, password })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Error en registro');
        }

        const data = await response.json();

        // Update storage
        localStorage.setItem('justibot_is_registered', 'true');
        if (data.pubsub_token) {
            localStorage.setItem('justibot_pubsub_token', data.pubsub_token);
        }

        return data;
    } catch (error) {
        throw error;
    }
}
