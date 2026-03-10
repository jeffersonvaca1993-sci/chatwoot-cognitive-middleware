import asyncio
import os
from dotenv import load_dotenv
from private.endpoints.auth import sincronizar_contacto_chatwoot
from private.database import database

load_dotenv()

async def test_pubsub():
    await database.connect()
    try:
        # Usar un ID de usuario ficticio
        id_usuario = 9999
        print("Probando sincronización...")
        
        # Llamar a la función que ya tenemos
        # Nota: esto creará un contacto real en Chatwoot
        contact_id, conversation_id = await sincronizar_contacto_chatwoot(
            nombre="Test PubSub",
            email="testpubsub@example.com",
            identificador="test_pubsub_user",
            id_usuario=id_usuario,
            es_nuevo=True
        )
        
        print(f"Contact ID: {contact_id}")
        print(f"Conversation ID: {conversation_id}")
        
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(test_pubsub())
