from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from private.database import connect_db, disconnect_db
from private.endpoints import auth, chat, websocket, webhook

app = FastAPI()

@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await disconnect_db()

# --- Routers ---
# Auth tiene prefix="/auth", al montarlo en "/api" queda "/api/auth"
app.include_router(auth.router, prefix="/api")
# Los siguientes ya tienen prefix completo "/api/..."
app.include_router(chat.router)
app.include_router(websocket.router)
app.include_router(webhook.router)

from fastapi.responses import FileResponse

# ... (imports)

@app.get("/")
async def serve_root():
    return FileResponse("public/index.html", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })

# Servir frontend estático (Debe ser lo último para assets)
app.mount("/", StaticFiles(directory="public", html=True), name="public")
