# ==============================================================================
# Archivo: cazador_ig.py
# Rol C5I: Scraper Autónomo de Inteligencia en Redes Sociales (Instagram)
# Descripción: Infiltra cuentas objetivo, descarga historias/posts con palabras 
#              tácticas, guarda evidencia física local, analiza el nivel de riesgo 
#              con IA local (gemma2:9b), inyecta a Supabase y alerta por Telegram.
# Intervalo: Ajustado a 4 HORAS de patrullaje continuo.
# ==============================================================================

import time
import requests
import json
import re
import html
import os
import sys
import instaloader
from supabase import create_client, Client
from datetime import timezone

# --- 1. ENRUTADOR MULTI-SO (CARPETA MAESTRA DOCKER) ---
RUTA_WINDOWS_OFICINA = r"C:\PROGRAMA\Evidencias_IG"
RUTA_MAC = "/Users/cris/Desktop/proyectos docker/Monitoreo y Scrapping/Evidencias_IG"
RUTA_DOCKER = "/app/Evidencias_IG"

def obtener_ruta_base():
    """Detecta el OS y asigna la ruta de la carpeta maestra automáticamente."""
    if os.path.exists('/.dockerenv'): 
        return RUTA_DOCKER
    elif sys.platform == 'darwin':    
        return RUTA_MAC
    else:                             
        return RUTA_WINDOWS_OFICINA

# --- 2. CREDENCIALES SUPABASE Y TELEGRAM ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

TELEGRAM_BOT_TOKEN = "8306463935:AAHa0W852sTG4vrpjApSzsF-2ToDlekJq8w"
TELEGRAM_CHAT_ID = "6799027326"

# --- 3. CREDENCIALES DE INSTAGRAM (LA MÁSCARA CLONADA) ---
USER_IG = "areralgo"

# --- 4. DICCIONARIOS TÁCTICOS Y ALIAS ---
OBJETIVOS_IG = [
    "riopilmaiquen", "lof.llamunao.autonomo", "werken_noticias", "mawizako", "pegundugun",
    "kutral_weychan", "justiciaxpablomarchant", "red_apoyo_puyewe_pilmayken", "hogarlawenmapu",
    "victor.llanquileo.pilquiman", "we.kimun", "radiotamara", "libredeterminacionmapuche",
    "itrofilmongen_ev", "envivoaquiyahoraofficial", "parqueparapenco", "lof_temulemu",
    "resistenciawallmapu", "lapincoyalucha", "movimientosdelfiofio", "keuleresiste",
    "globalpilmaiken", "redmujeresmapuche", "itrofilmongenev", "territorionativo.cl",
    "kelluwun_ka_yamuwun", "por_juliachunil_valdivia", "redmujerespencolirquen", "lafkenche.kimun",
    "corte_rebelderevolucionario", "mapuexpress", "liberacionmapuchelafkenche",
    "coordinadora.territorial.tome", "wallmapu_riot", "brotes.del.despojo", "wallmapu__libre2",
    "trepemulen", "resistencia.araucanialx", "millarayhuichalaf", "pelontuwetemuko", "wechekekawin",
    "hogar_relmulikan", "editorialpetunewenmuley", "libertad_ppmcam", "redsuperacionalmodeloforestal",
    "mapuche_warriache", "kpl__difusion", "mapuguapas", "memoriasenresistenciatemuko", "no.ticias_sur",
    "ppm_casoquilleco", "radioainil", "mediolibre_lazarzamora", "ppm_cam_a_su_mapu", "radiokurruf",
    "reconstruccionnacionalmapuche", "mision_permanente_mapuche_onu"
]

PALABRAS_RUIDO = [
    "cuba", "chernobil", "irán", "polonia", "rusia", "ucrania", "españa", 
    "sabadell", "bolivia", "colombia", "gaza", "maratón", "básquet", "fútbol", 
    "itaú", "farándula", "romance", "salud mental", "créditos", "ballet", 
    "danza", "netflix", "aeropuerto", "exhibicionismo", "lenteja", "salmón", 
    "biocultural"
]

LISTA_PPM_CMPC = [
    "claudia nahuelan", "héctor llaitul", "hector llaitul", "elías cona", "elias cona", 
    "fredy marileo", "pelentaro llaitul", "emilio berkhoff", "luis tranamil", "daniel canio", "grollmus"
]

LISTA_PPM_GENERAL = [
    "juan huenupil", "césar millanao", "orlando sáez", "esteban carrera", "bernardo camus", "matías leviqueo", 
    "alexis manríquez", "yerko maril", "francisco huichacura", "esteban huichacura", "carlos huichacura", 
    "manuel huichacura", "víctor llanquileo", "oscar pilquimán", "eliseo raiman", "domingo mariñan", 
    "manuel alonso llempi", "miguel llanquileo", "erick montoya", "pablo cayuhan", "juan mariñan", 
    "camilo astete", "josé luis marilao", "josé melgarejo", "guillermo camus", "miguel torres", "juan cortés", 
    "alejandro liguen", "anthony torres", "pedro palacios", "juan huenchullán", "joaquín millanao", "marco tori", 
    "christopher tori", "juan patricio queipul", "danilo nahuelpi", "luis david morales", "rubén cheuquepan", 
    "leandro catrileo", "josé lienqueo", "axel campos", "luis melinao", "benjamín coñopan", "rodrigo calabrano", 
    "luis fuenzalida", "matías ancalaf", "moroni ancalaf", "jorge caniupil", "oscar cañupan", "rafael pichun", 
    "luis menares", "juan carlos mardones", "roberto garling", "carlos fierro", "luis marileo", "patricio queipul", 
    "raúl caniullan", "nelson queupil", "rodrigo cáceres", "fabian llanca", "josé pichunhuala", "eduardo fuica", 
    "guillermo ñiripil", "celestino córdova"
]

DICCIONARIO_TACTICO = [
    "cam", "coordinadora arauco malleco", "wam", "weichan auka mapu", "rml", "resistencia mapuche", "ort", 
    "incendiario", "atentado", "sabotaje", "emboscada", "usurpación", "robo de madera", "armado", "disparos", 
    "barricadas", "cmpc", "mininco", "forestal", "fundo", "predio", "maquinaria", "skidder", "camión", "faena", 
    "presos políticos mapuche", "ppm", "huelga de hambre", "temucuicui", "peñi", "lamgen", "lamuen", "lof", "weichan"
]
DICCIONARIO_TACTICO.extend(LISTA_PPM_CMPC)
DICCIONARIO_TACTICO.extend(LISTA_PPM_GENERAL)

ALIAS_ORGANICAS = {
    "coordinadora arauco malleco": "CAM", 
    "ort": "CAM", 
    "resistencia mapuche lafquenche": "RML", 
    "resistencia mapuche lavkenche": "RML", 
    "resistencia mapuche": "RML", 
    "weichan auka mapu": "WAM"
}

def unificar_actor(texto):
    texto = str(texto).lower()
    for clave, valor in ALIAS_ORGANICAS.items():
        if re.search(r'\b' + re.escape(clave) + r'\b', texto): return valor
    if re.search(r'\bcam\b', texto): return "CAM"
    if re.search(r'\bwam\b', texto): return "WAM"
    if re.search(r'\brml\b', texto): return "RML"
    return "Desconocido"

def enviar_alerta_telegram(mensaje):
    # --- 1. GATEKEEPER TÁCTICO ANTI-RUIDO ---
    # Convertimos todo a minúsculas para que el filtro no falle por mayúsculas
    mensaje_lower = str(mensaje).lower()
    
    # Condición A: La IA catalogó explícitamente que no hay tipología de riesgo
    es_nulo = "tipología: ninguno" in mensaje_lower or "tipología: no especificado" in mensaje_lower or "tipología: none" in mensaje_lower
    
    # Condición B: El texto contiene jerga de eventos inofensivos
    palabras_ruido = ['ceremonia', 'festival', 'taller', 'teatro', 'poesía', 'música', 'palín', 'agradecimiento', 'cultural', 'aniversario', 'platería']
    es_ruido = any(palabra in mensaje_lower for palabra in palabras_ruido)
    
    # Condición C: BYPASS CRÍTICO MACROZONA SUR (Ignora el filtro de ruido si hay jerga de combate)
    palabras_criticas = ['eluwün', 'weichafe', 'marchant', 'catrillanca', 'lemún', 'armado', 'usurpación', 'fundo', 'cmpc', 'mininco', 'sabotaje']
    es_critico = any(palabra in mensaje_lower for palabra in palabras_criticas)
    
    # --- 2. TOMA DE DECISIÓN ---
    # Si es ruido o nulo, Y ADEMÁS no contiene palabras críticas, abortamos el envío.
    if (es_ruido or es_nulo) and not es_critico:
        print(f"🛑 [GATEKEEPER TELEGRAM] Alerta descartada. Motivo: Ruido de fondo o falta de tipología.")
        return # El 'return' hace que la función muera aquí y no envíe nada.

    # --- 3. EJECUCIÓN DEL DISPARO ---
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try: 
        requests.post(url, json=payload, timeout=10)
    except Exception as e: 
        print(f"[-] Error de conexión con Telegram: {e}")

def guardar_evidencia_fisica(url_media, perfil, es_video):
    try:
        carpeta = obtener_ruta_base()
        
        if not os.path.exists(carpeta):
            try: os.makedirs(carpeta)
            except Exception as e: return "Error de Carpeta"
        
        r = requests.get(url_media, timeout=15)
        if r.status_code == 200:
            ext = ".mp4" if es_video else ".jpg"
            nombre_archivo = os.path.join(carpeta, f"{perfil}_{int(time.time())}{ext}")
            try:
                with open(nombre_archivo, 'wb') as f: f.write(r.content)
                return nombre_archivo
            except Exception as write_error: return "Error de Escritura"
    except Exception as e: pass
    return "Error al descargar"

# --- 5. CEREBRO LOCAL (ACTUALIZADO A GEMMA 2) ---
def analizar_con_ia_local(titular, contenido):
    prompt = f"""
    Eres un Analista C5I militar evaluando inteligencia de Redes Sociales. Lee el texto extraído y extrae JSON estricto.
    SI NO ENCUENTRAS EL DATO, ESCRIBE "Ninguno". JAMÁS DEJES UN CAMPO VACÍO ("").

    REGLAS ESTRICTAS:
    1. "actor": Identifica al protagonista real del hecho (Ej: CAM, RML, WAM, o Nombre del Grupo Civil/Político).
    2. "ubicacion": Comuna. Si sale el fundo o sector, inclúyelo. 
    3. "tipologia_oficial": Elige UNA de estas opciones exactas: [Ataque Incendiario, Ataque Armado, Sabotaje / Otros, Procedimiento Policial, Robo de Madera, Usurpación, Manifestación / Alteración del Orden].
    4. "accion_digital": ELIGE SOLO UNA DE ESTA LISTA: [Ataque Incendiario, Robo de Madera, Procedimiento Policial, Hito Judicial, Declaración Política, Denuncia Ambiental/Social, Comunicado].
    5. "catalizador": Determina el origen del hecho. Elige UNA: [Reivindicación Territorial, Conflicto Forestal, Proceso Judicial, Violencia Rural, Redes Sociales].
    6. "modificadores": LAS VÍCTIMAS DEL HECHO (Ej: CMPC, Carabineros, Contratista). NUNCA pongas a la CAM, WAM o RML como víctimas, ellos son los atacantes.
    7. "palabra_clave": EXACTAMENTE DOS (2) conceptos compuestos. OBLIGATORIO: Deben ser BIGRAMAS (2 palabras) o TRIGRAMAS (3 palabras). PROHIBIDO usar palabras únicas o sueltas.
    8. "analisis_ia": Telegráfico, neutral. MÁXIMO 20 PALABRAS. Sin predicciones.
    9. REGLA ANTI-FALSO POSITIVO: Si el texto trata sobre un político condenando un ataque pasado, la acción DEBE SER "Declaración Política" y la alerta "BAJO".
    10. "latitud" y "longitud": Estima las coordenadas geográficas de la comuna identificada de forma dinámica.
    11. No agregar noticias del "Tren de Aragua"
    
    REGLAS DE CONTEXTO TERRITORIAL (CRÍTICO):
    - DICCIONARIO MAPUDUNGUN: "Eluwün" significa funeral. "Weichafe" significa combatiente/guerrero. "Lof" significa comunidad. "Weichan" significa lucha/guerra. 
    - EVENTOS DE RIESGO: Si una publicación menciona el "Eluwün" (funeral) de un "weichafe" (combatiente) o conmemoraciones a caídos (ej. Pablo Marchant, Lemún, Catrillanca, etc.), ES INTELIGENCIA CRÍTICA. 
    - PROHIBIDO MINIMIZAR: NUNCA clasifiques el funeral de un combatiente como una simple "ceremonia" comunitaria, cultural o de agradecimiento. 
    - TIPOLOGÍA OBLIGATORIA: Para estos casos, la 'Tipología' DEBE SER "Hito Político / Conmemoración" o "Funeral de Riesgo", y el 'Análisis IA' debe advertir explícitamente que es la conmemoración de un combatiente.

    FORMATO DE RESPUESTA:
    {{
      "actor": "",
      "ubicacion": "",
      "latitud": "",
      "longitud": "",
      "catalizador": "",
      "accion_digital": "",
      "tipologia_oficial": "",
      "modificadores": "",
      "palabra_clave": "",
      "analisis_ia": ""
    }}

    NOTICIA/POST:
    Titular: {titular}
    Contenido: {contenido}
    """
    
    # --- ENRUTADOR DINÁMICO MAC / WINDOWS DOCKER ---
    if os.path.exists('/.dockerenv'):
        url_local = "http://host.docker.internal:11434/api/generate"
    else:
        url_local = "http://localhost:11434/api/generate"
        
    payload = {
        "model": "gemma2:9b", 
        "prompt": prompt, 
        "format": "json", 
        "stream": False, 
        "options": {"temperature": 0.0}
    }
    
    try:
        response = requests.post(url_local, json=payload, timeout=120)
        
        # Bloque de auditoría
        if response.status_code != 200:
            print(f"[-] Alerta IA en IG: Ollama respondió con código de error {response.status_code}")
            return None
            
        texto_ia = response.json().get('response', '{}')
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        if match: 
            return json.loads(match.group(0))
        return None
    except Exception as e: 
        print(f"[-] Falla crítica de conexión con IA local (Ollama) en IG: {e}")
        return None

# --- 6. MOTOR DE INFILTRACIÓN INSTAGRAM ---
def iniciar_cazador():
    print("🕵️ Iniciando infiltración en Meta (Instagram)...")
    L = instaloader.Instaloader(sleep=True, download_pictures=False, download_videos=False, download_video_thumbnails=False)
    
    try:
        L.load_session_from_file(USER_IG)
        print("[+] Autenticación exitosa. Máscara de sesión inyectada.")
    except Exception as e:
        print(f"[-] Fallo crítico al cargar sesión. Verifica la cookie. Error: {e}")
        return

    objetivos_patrullaje = []
    print("📡 Extrayendo tu lista de 'Seguidos' (Followees)...")
    try:
        mi_perfil = instaloader.Profile.from_username(L.context, USER_IG)
        objetivos_patrullaje = [followee.username for followee in mi_perfil.get_followees()]
        print(f"[+] Radar calibrado. Se detectaron {len(objetivos_patrullaje)} perfiles dinámicos.")
    except Exception as e:
        print(f"[-] Extracción dinámica bloqueada por Meta. Error: {e}")
        print("[!] ACTIVANDO PROTOCOLO DE RESPALDO: Usando matriz estática.")
        objetivos_patrullaje = OBJETIVOS_IG

    try:
        res = supabase.table("inteligencia_tactica").select("enlace_noticia").execute()
        if res.data:
            procesadas = set(r['enlace_noticia'] for r in res.data)
        else:
            procesadas = set()
    except Exception as e_supa:
        print(f"⚠️ Advertencia al sincronizar boveda en IG: {e_supa}")
        procesadas = set()

    # ==============================================================================
    # BLOQUE CENTRAL DE PATRULLAJE: HISTORIAS Y POSTS
    # ==============================================================================
    for perfil in objetivos_patrullaje:
        print(f"\n🔍 Patrullando: @{perfil}")
        try:
            profile = instaloader.Profile.from_username(L.context, perfil)
            
            # --- A. CAZA DE HISTORIAS ---
            if profile.has_public_story or (profile.is_private == False) or L.context.is_logged_in:
                for story in L.get_stories(userids=[profile.userid]):
                    for item in story.get_items():
                        enlace_historia = f"https://instagram.com/stories/{perfil}/{item.mediaid}/"
                        if enlace_historia in procesadas:
                            print(f"   [≈] Historia omitida (Ya está en Supabase)")
                            continue
                        
                        texto_historia = f"Historia Multimedia: {item.caption if item.caption else ''}"
                        tiene_tactica = any(re.search(r'\b' + re.escape(t) + r'\b', texto_historia.lower()) for t in DICCIONARIO_TACTICO)
                        
                        if not tiene_tactica:
                            print(f"   [-] Historia descartada (No contiene palabras tácticas)")
                            continue
                            
                        print(f"⚡ [Story] Información táctica detectada en @{perfil}")
                        url_evidencia = item.video_url if item.is_video else item.url
                        ruta_local = guardar_evidencia_fisica(url_evidencia, perfil, item.is_video)
                        print(f"[+] Evidencia local: {ruta_local}")

                        registro_story = {
                            "fecha": item.date_utc.isoformat(),
                            "titular": f"Historia de @{perfil}",
                            "actor": unificar_actor(texto_historia.lower()),
                            "ubicacion": "Macrozona Sur",
                            "catalizador": "Redes Sociales",
                            "accion_digital": "Comunicado",
                            "tipologia_oficial": "Sabotaje / Otros",
                            "modificadores": "Ninguno",
                            "puntaje_riesgo": 4.5,
                            "nivel_alerta": "MEDIO",
                            "enlace_noticia": enlace_historia,
                            "url_foto": url_evidencia,
                            "ruta_evidencia_local": ruta_local,
                            "latitud": "-38.73",
                            "longitud": "-72.59",
                            "palabra_clave": "Historia IG, Análisis Táctico",
                            "analisis_ia": texto_historia[:100],
                            "fuentes_adicionales": ""
                        }
                        supabase.table("inteligencia_tactica").insert(registro_story).execute()
                        procesadas.add(enlace_historia)
            
            # --- B. CAZA DE POSTS PERMANENTES ---
            posts = profile.get_posts()
            contador = 0
            for post in posts:
                if contador >= 2: break 
                contador += 1
                
                enlace_post = f"https://www.instagram.com/p/{post.shortcode}/"
                if enlace_post in procesadas:
                    print(f"   [≈] Post omitido (Ya procesado anteriormente)")
                    continue
                
                texto_post = post.caption if post.caption else ""
                texto_lower = texto_post.lower()
                
                if any(r in texto_lower for r in PALABRAS_RUIDO):
                    print(f"   [-] Post descartado (Ruido detectado)")
                    continue

                if not any(re.search(r'\b' + re.escape(t) + r'\b', texto_lower) for t in DICCIONARIO_TACTICO):
                    print(f"   [-] Post descartado (Ruido / Sin palabras de interés)")
                    continue
                
                print(f"⚙️ [IA Local] Analizando amenaza en post de @{perfil}...")
                ia = analizar_con_ia_local(f"Post de @{perfil}", texto_post)
                
                if ia:
                    for key in ["actor", "ubicacion", "accion_digital", "tipologia_oficial", "catalizador", "modificadores", "palabra_clave", "analisis_ia"]:
                        if not ia.get(key) or str(ia.get(key)).strip() == "" or str(ia.get(key)).lower() == "null": ia[key] = "No especificado"
                else:
                    ia = {}

                actor_final = unificar_actor(f"@{perfil} " + texto_lower)
                if actor_final != "Desconocido": ia['actor'] = actor_final
                
                ia_accion = str(ia.get('accion_digital', 'Comunicado')).title()
                modificadores_ia = str(ia.get('modificadores', 'Ninguno')).strip("[]\"'")
                
                es_cmpc = any(x in texto_lower for x in ["cmpc", "mininco"])
                if not es_cmpc: modificadores_ia = re.sub(r'(?i)CMPC|Mininco', '', modificadores_ia).strip(', ')
                modificadores_ia = re.sub(r'(?i)\bCAM\b|\bWAM\b|\bRML\b', '', modificadores_ia).strip(', ')
                if not modificadores_ia or modificadores_ia.lower() == "ninguno" or modificadores_ia == "": modificadores_ia = "Ninguno"

                ia_accion_upper = ia_accion.upper()
                riesgo, alerta = 2.0, "BAJO"

                if es_cmpc and any(x in ia_accion_upper for x in ["ATAQUE", "ROBO", "INCENDIO", "USURPACIÓN"]): riesgo, alerta = 9.5, "CRÍTICO"
                elif any(x in ia_accion_upper for x in ["ATAQUE", "ROBO", "INCENDIO", "USURPACIÓN"]): riesgo, alerta = 7.5, "ALTO"
                elif "COMUNICADO" in ia_accion_upper:
                    if actor_final in ["CAM", "WAM", "RML"]: riesgo, alerta = 7.5, "ALTO"
                    else: riesgo, alerta = 4.5, "MEDIO"
                elif "POLICIAL" in ia_accion_upper or "JUDICIAL" in ia_accion_upper: riesgo, alerta = 7.5, "ALTO"
                elif "DENUNCIA" in ia_accion_upper: riesgo, alerta = 3.5, "BAJO"

                url_evidencia = post.video_url if post.is_video else post.url
                ruta_local = guardar_evidencia_fisica(url_evidencia, perfil, post.is_video)
                print(f"[+] Evidencia local: {ruta_local}")

                # --- SANITIZACIÓN DE COORDENADAS PARA SUPABASE ---
                try:
                    lat_segura = float(str(ia.get('latitud', '-38.73')).replace(',', '.'))
                except:
                    lat_segura = -38.73
                    
                try:
                    lon_segura = float(str(ia.get('longitud', '-72.59')).replace(',', '.'))
                except:
                    lon_segura = -72.59
            
                registro = {
                    "fecha": post.date_utc.replace(tzinfo=timezone.utc).isoformat(),
                    "titular": f"Comunicación de @{perfil} vía Instagram",
                    "actor": actor_final,
                    "ubicacion": str(ia.get('ubicacion', 'Macrozona Sur')),
                    "catalizador": str(ia.get('catalizador', 'Redes Sociales')),
                    "accion_digital": ia_accion,
                    "tipologia_oficial": str(ia.get('tipologia_oficial', 'Sabotaje / Otros')),
                    "modificadores": modificadores_ia,
                    "puntaje_riesgo": riesgo,
                    "nivel_alerta": alerta,
                    "enlace_noticia": enlace_post,
                    "url_foto": url_evidencia,
                    "ruta_evidencia_local": ruta_local,
                    "latitud": lat_segura,
                    "longitud": lon_segura,
                    "palabra_clave": str(ia.get('palabra_clave', '')).strip("[]\"'"),
                    "analisis_ia": str(ia.get('analisis_ia', '')).strip("[]\"'"),
                    "fuentes_adicionales": ""
                }
                supabase.table("inteligencia_tactica").insert(registro).execute()
                procesadas.add(enlace_post)
                
                if alerta in ["CRÍTICO", "ALTO", "MEDIO", "BAJO"]:
                    emoji = "🔴" if alerta == "CRÍTICO" else "🟠" if alerta == "ALTO" else "🟡" if alerta == "MEDIO" else "🔵"
                    t_accion = html.escape(ia_accion.upper())
                    t_fecha = html.escape(post.date_utc.strftime('%d/%m/%Y %H:%M'))
                    t_ubicacion = html.escape(str(ia.get('ubicacion', 'Macrozona Sur')))
                    t_actor = html.escape(actor_final)
                    t_obj = html.escape(modificadores_ia)
                    t_resumen = html.escape(str(ia.get('analisis_ia', '')))
                    t_tipo = html.escape(str(ia.get('tipologia_oficial', 'Sabotaje / Otros')))

                    mensaje_tg = f"<b>{emoji} ALERTA RRSS: {t_accion}</b>\n\n<b>Tipología:</b> {t_tipo}\n<b>Fecha:</b> {t_fecha}\n<b>Perfil:</b> @{perfil}\n<b>Ubicación:</b> {t_ubicacion}\n<b>Actor:</b> {t_actor}\n<b>Objetivo:</b> {t_obj}\n\n<b>Análisis IA:</b> <i>{t_resumen}</i>\n<b>📂 Evidencia Local:</b> <code>{ruta_local}</code>\n\n<a href='{enlace_post}'>📸 Ver publicación original</a>"
                    enviar_alerta_telegram(mensaje_tg)
                    
                time.sleep(15)
            time.sleep(45)
            
        except instaloader.exceptions.ProfileNotExistsException:
            print(f"[-] El perfil @{perfil} no existe o Meta bloqueó la lectura. Saltando...")
            time.sleep(10)
        except instaloader.exceptions.ConnectionException as e:
            print(f"[-] Meta está bloqueando activamente las peticiones: {e}. Abortando ciclo temporalmente.")
            break
        except Exception as e:
            print(f"[-] Error crítico en @{perfil}: {e}. Protegiendo cuenta y saltando...")
            time.sleep(60)

if __name__ == "__main__":
    while True:
        print(f"🛡️ Iniciando Escaneo Táctico Rápido con IA Local (gemma2:9b)...")
        iniciar_cazador()
        print("⏳ Ronda completada. Durmiendo 4 HORAS para patrullaje intensivo.")
        time.sleep(14400)