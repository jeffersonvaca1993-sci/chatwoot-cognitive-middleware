# src/config.py
import os
import toml
from dotenv import load_dotenv
from pydantic import BaseModel

# Cargar variables de entorno
load_dotenv()

class ConfigSistema(BaseModel):
    ambiente: str
    idioma_default: str
    nivel_log: str

class ConfigLLM(BaseModel):
    modelo_razonamiento: str
    modelo_rapido: str
    modelo_embeddings: str

class ConfigVectores(BaseModel):
    dimensiones: int
    metrica: str
    tabla_conocimiento: str

class ConfigAgentes(BaseModel):
    estrategia_default: str
    estrategia_fallback: str

class GlobalConfig(BaseModel):
    sistema: ConfigSistema
    llm: ConfigLLM
    vectores: ConfigVectores
    agentes: ConfigAgentes
    
    # Secrets from env
    DATABASE_URL: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str

def load_config() -> GlobalConfig:
    # 1. Cargar TOML
    try:
        print(f"Intentando cargar config.toml desde {os.getcwd()}")
        with open("config.toml", "r") as f:
            toml_data = toml.load(f)
            print(f"TOML cargado. Claves: {list(toml_data.keys())}")
    except FileNotFoundError:
        print("ERROR: config.toml no encontrado")
        raise RuntimeError("No se encontró config.toml")
    except Exception as e:
        print(f"ERROR cargando TOML: {e}")
        raise

    # 2. Construir URL de DB si no existe
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "chatwoot_production")
        host = "postgres" # Forzamos nombre del servicio docker si no está definido
        port = "5432"
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    
    print(f"DB URL: {db_url}")

    # 3. Fusionar
    return GlobalConfig(
        sistema=ConfigSistema(**toml_data["sistema"]),
        llm=ConfigLLM(**toml_data["llm"]),
        vectores=ConfigVectores(**toml_data["vectores"]),
        agentes=ConfigAgentes(**toml_data["agentes"]),
        DATABASE_URL=db_url,
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        GEMINI_API_KEY=os.getenv("GEMINI_API_KEY", "")
    )

settings = load_config()
