# src/rag_engine/indexador.py
from typing import List
from sqlmodel import Session
from src.database.models import BaseConocimiento
from src.database.session import engine

class Indexador:
    def __init__(self):
        self.engine = engine

    def indexar_fragmento(self, texto: str, vector: List[float], fuente: str, categoria: str):
        """
        Guarda un fragmento y su vector en la base de datos.
        """
        with Session(self.engine) as session:
            nuevo_fragmento = BaseConocimiento(
                contenido_textual=texto,
                vector_embedding=vector,
                fuente_cita=fuente,
                categoria=categoria
            )
            session.add(nuevo_fragmento)
            session.commit()
            session.refresh(nuevo_fragmento)
            return nuevo_fragmento.id_fragmento
