import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:1001/api/v1"
ADMIN_API_KEY = "zxc12345" # Clave maestra por defecto

def test_jwt_flow():
    print("--- LOGIN: Iniciando Pruebas de JWT ---")
    
    # 1. Login
    print("\n1. Intentando login con clave maestra...")
    login_payload = {"api_key": ADMIN_API_KEY}
    response = requests.post(f"{BASE_URL}/auth/login", json=login_payload)
    
    if response.status_code != 200:
        print(f"❌ Error en login: {response.text}")
        return
    
    auth_data = response.json()
    access_token = auth_data.get("access_token")
    refresh_token = auth_data.get("refresh_token")
    
    if access_token and refresh_token:
        print("v Login exitoso. Tokens recibidos.")
    else:
        print("x Error: No se recibieron tokens.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Acceder a ruta protegida
    print("\n2. Accediendo a ruta protegida (/admin/queue/state)...")
    response = requests.get(f"{BASE_URL}/admin/queue/state", headers=headers)
    
    if response.status_code == 200:
        print("v Acceso concedido con JWT.")
    else:
        print(f"x Error al acceder a ruta protegida: {response.status_code} - {response.text}")

    # 3. Acceder sin token
    print("\n3. Accediendo sin token...")
    response = requests.get(f"{BASE_URL}/admin/queue/state")
    if response.status_code == 403:
        print("v Acceso denegado sin token (esperado).")
    else:
        print(f"x Error: Se permitió el acceso sin token o código de error incorrecto: {response.status_code}")

    # 4. Refresh token
    print("\n4. Probando Refresh Token...")
    refresh_payload = {"refresh_token": refresh_token}
    response = requests.post(f"{BASE_URL}/auth/refresh", json=refresh_payload)
    
    if response.status_code == 200:
        new_access_token = response.json().get("access_token")
        if new_access_token:
            print("v Token de acceso refrescado correctamente.")
            # Verificar el nuevo token
            new_headers = {"Authorization": f"Bearer {new_access_token}"}
            response = requests.get(f"{BASE_URL}/admin/queue/state", headers=new_headers)
            if response.status_code == 200:
                 print("v El nuevo token de acceso funciona.")
        else:
            print("x Error: No se recibió nuevo token de acceso.")
    else:
        print(f"x Error en refresh: {response.status_code} - {response.text}")

    # 5. Verificar logs (manual o chequeando si hay errores en consola)
    print("\n5. Verificación de Auditoría:")
    print("   Note: Revisa la consola del servidor (uvicorn) para ver los logs de ADMIN:master")

    print("\n--- 🏁 Pruebas Completadas ---")

if __name__ == "__main__":
    test_jwt_flow()
