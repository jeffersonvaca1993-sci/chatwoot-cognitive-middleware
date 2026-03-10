# src/rag_engine/core/vectorizador_gemini.py
from typing import List
import google.generativeai as genai
from src.clientes_llm.gemini import ClienteGemini

class VectorizadorGemini:
    def __init__(self):
        # Reutilizamos la configuración del cliente Gemini para obtener la API Key
        # pero usamos el método embed_content directamente.
        self.cliente = ClienteGemini()
        # Aseguramos que el SDK esté configurado
        genai.configure(api_key=self.cliente.api_key)

    async def generar_embedding(self, texto: str) -> List[float]:
        """
        Genera un vector de 768 dimensiones usando models/text-embedding-004.
        """
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texto,
            task_type="retrieval_document",
            title="Documento RAG"
        )
        return result['embedding']
