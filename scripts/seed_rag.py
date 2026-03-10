# scripts/seed_rag.py
import sys
import os
import asyncio

# Añadir el directorio raíz al path para importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.rag_engine.transeunte.procesador import ProcesadorReglamentoTranseunte

async def main():
    print("🌱 Iniciando siembra de RAG (Estructura Dominio)...")
    
    # Ahora el procesador sabe dónde está su data, no hace falta pasar argumentos
    trabajos = [
        ProcesadorReglamentoTranseunte()
    ]
    
    for procesador in trabajos:
        await procesador.procesar()

    print("✅ Siembra completada.")

if __name__ == "__main__":
    asyncio.run(main())
