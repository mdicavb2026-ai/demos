import instaloader

# 1. Configuración de tu cuenta
USERNAME = "areralgo"
# REEMPLAZA EL TEXTO DE ABAJO CON EL VALOR QUE COPIASTE EN EL PASO 1 (Manten las comillas)
SESSIONID = "74642721433%3AR9TCOJ2n2HflvZ%3A15%3AAYiM46bUVO70eO4kTL1KhVH9jccU93nI_S9CsgUe8g" 

print(f"Iniciando bypass para {USERNAME}...")

# 2. Inyección de la llave
L = instaloader.Instaloader()
L.context._session.cookies.set("sessionid", SESSIONID, domain=".instagram.com")
L.context.username = USERNAME
L.context.is_valid = True

# 3. Guardado directo en la bóveda
L.save_session_to_file("/tmp/.instaloader-root/session-areralgo")
print("¡Inyección completada! Tu robot ya tiene acceso total.")