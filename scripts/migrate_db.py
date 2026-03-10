import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    if not DATABASE_URL:
        print("Error: DATABASE_URL no encontrada en .env")
        return

    print(f"Conectando a {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'DB'}...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Verificar si la columna avatar_url existe
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='clientes_activos' AND column_name='avatar_url';
        """)
        row = cur.fetchone()
        
        if not row:
            print("Agregando columna avatar_url...")
            cur.execute("ALTER TABLE clientes_activos ADD COLUMN avatar_url TEXT;")
            conn.commit()
            print("Columna agregada.")
        else:
            print("La columna avatar_url ya existe.")

        # Verificar si la columna chatwoot_pubsub_token existe
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='clientes_activos' AND column_name='chatwoot_pubsub_token';
        """)
        row = cur.fetchone()
        
        if not row:
            print("Agregando columna chatwoot_pubsub_token...")
            cur.execute("ALTER TABLE clientes_activos ADD COLUMN chatwoot_pubsub_token TEXT;")
            conn.commit()
            print("Columna agregada.")
        else:
            print("La columna chatwoot_pubsub_token ya existe.")
            
        cur.close()
        conn.close()
        print("Migración completada.")
        
    except Exception as e:
        print(f"Error durante la migración: {e}")

if __name__ == "__main__":
    migrate()
