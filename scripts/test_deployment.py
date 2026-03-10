import requests
import sys
import time

def check_health(url, retries=5, delay=2):
    print(f"Verificando salud de {url}...")
    for i in range(retries):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✅ {url} está respondiendo correctamente.")
                return True
            else:
                print(f"⚠️ {url} respondió con código {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"⏳ Intento {i+1}/{retries}: No se pudo conectar a {url}")
        
        time.sleep(delay)
    
    print(f"❌ Falló la conexión a {url} después de {retries} intentos.")
    return False

if __name__ == "__main__":
    # URLs asumiendo ejecución desde host (localhost)
    # Si se ejecuta dentro de docker network, usar nombres de servicio
    api_url = "http://localhost:8000/health"
    
    print("--- INICIANDO VERIFICACIÓN DE DESPLIEGUE ---")
    
    if check_health(api_url):
        print("\n✅ El sistema parece estar operativo.")
        sys.exit(0)
    else:
        print("\n❌ El sistema presenta fallos.")
        sys.exit(1)
