# src/database/session.py
from sqlmodel import create_engine, Session, SQLModel
from src.config import settings

# Crear el motor de base de datos
# echo=True para ver las consultas SQL en desarrollo
engine = create_engine(settings.DATABASE_URL, echo=(settings.sistema.ambiente == "desarrollo"))

def get_session():
    """Dependencia para obtener una sesión de base de datos."""
    with Session(engine) as session:
        yield session

def init_db():
    """Inicializa las tablas en la base de datos."""
    SQLModel.metadata.create_all(engine)
