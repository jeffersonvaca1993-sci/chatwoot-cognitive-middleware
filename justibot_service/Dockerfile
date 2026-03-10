FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código backend (privado) y frontend (público)
# Copiar código backend (privado) y frontend (público)
COPY justibot_service/private /app/private
COPY justibot_service/public /app/public

# Copiar módulo de base de datos compartido
COPY src/database /app/shared_database

# Exponer puerto
EXPOSE 8001

# Ejecutar uvicorn apuntando al módulo dentro de 'private'
CMD ["uvicorn", "private.main:app", "--host", "0.0.0.0", "--port", "8001"]
