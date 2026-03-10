import os
import toml
from pydantic import BaseModel

class ChatwootConfig(BaseModel):
    base_url: str
    public_url: str
    account_id: int
    inbox_id: str
    api_token: str

class Config(BaseModel):
    chatwoot: ChatwootConfig

def load_config() -> Config:
    # 1. Cargar TOML
    try:
        with open("config.toml", "r") as f:
            toml_data = toml.load(f)
    except FileNotFoundError:
        toml_data = {}

    # 2. Obtener Token de ENV
    api_token = os.getenv("CHATWOOT_API_TOKEN")
    if not api_token:
        print("ADVERTENCIA: CHATWOOT_API_TOKEN no está definido.")
        api_token = "dummy_token"

    # 3. Construir Config
    return Config(
        chatwoot=ChatwootConfig(
            base_url=os.getenv("CHATWOOT_BASE_URL") or toml_data.get("chatwoot", {}).get("base_url") or "http://moe_chatwoot_web:3000",
            public_url=os.getenv("CHATWOOT_PUBLIC_URL") or "wss://chat.sci-vacasantana.org", # Default hardcoded para este caso
            account_id=int(os.getenv("CHATWOOT_ACCOUNT_ID") or toml_data.get("chatwoot", {}).get("account_id") or 1),
            inbox_id=str(os.getenv("CHATWOOT_INBOX_ID") or toml_data.get("chatwoot", {}).get("inbox_id") or "1"),
            api_token=api_token
        )
    )

settings = load_config()
