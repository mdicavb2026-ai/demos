# ==============================================================================
# Archivo: motor_24_7.py
# Rol C5I: Scraper Autónomo de Noticias y Fuentes Abiertas (RSS / Google News)
# Descripción: Rastrea feeds tácticos, decodifica enlaces nativos, extrae texto 
#              profundo, aplica clustering semántico (deduplicación 12h con parseo
#              estricto de timestamp UTC) y clasifica amenazas.
# Compuerta 24h: Bloquea inserciones reiteradas del mismo suceso mediante firmas
#                normalizadas y silencia alertas de pauta política en Telegram.
# ==============================================================================

import os
import sys
import ssl
import urllib3
import feedparser
import time
import requests
import json
import re
import html
from supabase import create_client, Client
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from googlenewsdecoder import new_decoderv1

# --- NUEVO: PARCHE SSL PARA MAC Y ENRUTADOR DOCKER/WINDOWS/MAC ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

RUTA_WINDOWS_OFICINA = r"C:\PROGRAMA\Evidencias_IG"
RUTA_MAC_FIN_DE_SEMANA = "/Users/cris/Desktop/proyectos docker/Monitoreo y Scrapping/Evidencias_IG"
RUTA_DOCKER_CONTAINER = "/app/evidencias"

def obtener_ruta_base():
    """Detecta el OS y asigna la ruta correcta de evidencias automáticamente."""
    if os.path.exists('/.dockerenv'): 
        return RUTA_DOCKER_CONTAINER
    elif sys.platform == 'darwin':    
        return RUTA_MAC_FIN_DE_SEMANA
    else:                             
        return RUTA_WINDOWS_OFICINA

# --- 1. CREDENCIALES SUPABASE (LA BÓVEDA) Y TELEGRAM ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

TELEGRAM_BOT_TOKEN = "8306463935:AAHa0W852sTG4vrpjApSzsF-2ToDlekJq8w"
TELEGRAM_CHAT_ID = "6799027326"

# --- 2. CONFIGURACIÓN TÁCTICA (MATRIZ COMPLETA Y DESPLEGADA) ---
RADARES_RSS = [
    # QUERIES GOOGLE NEWS
    "https://news.google.com/news/rss/search?q=%28%22CAM%22%20OR%20%22Coordinadora%20Arauco%20Malleco%22%20OR%20%22WAM%22%20OR%20%22Weichan%20Auka%20Mapu%22%20OR%20%22RML%22%20OR%20%22Resistencia%20Mapuche%22%20OR%20%22ORT%22%29%20AND%20%28adjudica%20OR%20reivindica%20OR%20lienzo%20OR%20panfleto%20OR%20atentado%20OR%20sabotaje%29%20AND%20%28Chile%20OR%20Araucan%C3%ADa%20OR%20Biob%C3%ADo%20OR%20Macrozona%20OR%20Mapuche%20OR%20Wallmapu%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28%22CMPC%22%20OR%20%22Mininco%22%20OR%20%22faena%20forestal%22%20OR%20%22predio%20agr%C3%ADcola%22%20OR%20%22contratista%20forestal%22%29%20AND%20%28%22ataque%20incendiario%22%20OR%20%22atentado%20incendiario%22%20OR%20%20%22maquinaria%20quemada%22%20OR%20%22skidder%22%20OR%20%22trineum%C3%A1tico%22%20OR%20%22usurpaci%C3%B3n%22%29%20AND%20%28%22Regi%C3%B3n%20de%20La%20Araucan%C3%ADa%22%20OR%20%22Regi%C3%B3n%20del%20Biob%C3%ADo%22%20OR%20%22Macrozona%20Sur%22%20OR%20%22Provincia%20de%20Malleco%22%20OR%20%22Provincia%20de%20Arauco%22%20OR%20Ercilla%20OR%20Tir%C3%BAa%20OR%20Ca%C3%B1ete%20OR%20Contulmo%20OR%20Lumaco%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28Carabineros%20OR%20COP%20OR%20Ej%C3%A9rcito%20OR%20militar%20OR%20%22Control%20de%20Orden%20P%C3%BAblico%22%29%20AND%20%28emboscada%20OR%20%22ataque%20armado%20OR%20r%C3%A1fagas%20OR%20%22munici%C3%B3n%20de%20guerra%22%20OR%20blindado%20OR%20allanamiento%29%20AND%20%28Araucan%C3%ADa%20OR%20Biob%C3%ADo%20OR%20Macrozona%20OR%20Ercilla%20OR%20Tir%C3%BAa%20OR%20Ca%C3%B1ete%20OR%20Contulmo%20OR%20Lumaco%20OR%20Traigu%C3%A9n%20OR%20Collipulli%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28torre%20OR%20antena%20OR%20puente%20OR%20tren%20OR%20descarrilamiento%20OR%20%22ruta%205%22%20OR%20%22ruta%20160%22%29%20AND%20%28explosivo%20OR%20dinamita%20OR%20sabotaje%20OR%20barricada%20OR%20%22derribo%20de%20%C3%A1rboles%22%29%20AND%20%28Chile%20OR%20Araucan%C3%ADa%20OR%20Biob%C3%ADo%20OR%20Macrozona%20OR%20Malleco%20OR%20Caut%C3%ADn%20OR%20Arauco%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28%22PPM%22%20OR%20%22Presos%20Pol%C3%ADticos%20Mapuche%22%20OR%20%22M%C3%B3dulo%20comunero%22%29%20AND%20%28huelga%20OR%20traslado%20OR%20Gendarmer%C3%ADa%20OR%20mot%C3%ADn%20OR%20descompensado%20OR%20%22medida%20de%20presi%C3%B3n%22%29%20AND%20%28Chile%20OR%20Araucan%C3%ADa%20OR%20Biob%C3%ADo%20OR%20Macrozona%20OR%20Temuco%20OR%20Angol%20OR%20Concepci%C3%B3n%20OR%20Lebu%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28%22robo%20de%20madera%22%20OR%20narcotr%C3%A1fico%20OR%20%22tr%C3%A1fico%20de%20armas%22%20OR%20%22crimen%20organizado%22%20OR%20%22tala%20ilegal%22%29%20AND%20%28%22Araucan%C3%ADa%22%20OR%20%22Biob%C3%ADo%22%20OR%20%22Macrozona%20Sur%22%20OR%20Malleco%20OR%20Ercilla%20OR%20Tir%C3%BAa%20OR%20Ca%C3%B1ete%20OR%20Contulmo%20OR%20Lumaco%20OR%20Traigu%C3%A9n%20OR%20Collipulli%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    "https://news.google.com/news/rss/search?q=%28%22causa%20mapuche%22%20OR%20%22conflicto%20medioambiental%22%20OR%20%22estado%20de%20excepci%C3%B3n%22%20OR%20%22desmilitarizaci%C3%B3n%22%20OR%20%22extractivismo%22%29%20AND%20%28Araucan%C3%ADa%20OR%20Biob%C3%ADo%20OR%20Macrozona%20OR%20Malleco%20OR%20Wallmapu%29%20when%3A1d&hl=es-419-CL&gl=CL&ceid=CL:es-419",
    
    # MEDIOS WEB DIRECTOS Y BLOGS
    "https://www.mapuexpress.org/feed/",
    "https://radiokurruf.org/feed/",
    "https://radionewen.cl/feed/",
    "https://www.mapuchediario.cl/feed/",
    "https://www.elpuelche.cl/feed/",
    "https://piensachile.com/feed/",
    "https://lazarzamora.cl/feed/",
    "https://futatrawun.blogspot.com/feeds/posts/default",
    "https://sites.google.com/feeds/content/site/superacionmodeloforestal",
    "https://mapuche.info/feed/",
    "https://resumen.cl/feed",
    "https://interferencia.cl/feed",
    "https://araucaniadiario.cl/feed/",
    "https://www.malleco7.cl/feed/",
    "https://www.clave9.cl/feed/",
    
    # --- REDES SOCIALES (Vía RSSHub) ---
    "https://rsshub.app/instagram/user/riopilmaiquen",
    "https://rsshub.app/instagram/user/lof.llamunao.autonomo",
    "https://rsshub.app/instagram/user/werken_noticias",
    "https://rsshub.app/instagram/user/mawizako",
    "https://rsshub.app/instagram/user/pegundugun",
    "https://rsshub.app/instagram/user/kutral_weychan",
    "https://rsshub.app/instagram/user/justiciaxpablomarchant",
    "https://rsshub.app/instagram/user/red_apoyo_puyewe_pilmayken",
    "https://rsshub.app/instagram/user/hogarlawenmapu",
    "https://rsshub.app/instagram/user/victor.llanquileo.pilquiman",
    "https://rsshub.app/instagram/user/we.kimun",
    "https://rsshub.app/instagram/user/radiotamara",
    "https://rsshub.app/instagram/user/libredeterminacionmapuche",
    "https://rsshub.app/instagram/user/itrofilmongen_ev",
    "https://rsshub.app/instagram/user/envivoaquiyahoraofficial",
    "https://rsshub.app/instagram/user/parqueparapenco",
    "https://rsshub.app/instagram/user/lof_temulemu",
    "https://rsshub.app/instagram/user/resistenciawallmapu",
    "https://rsshub.app/instagram/user/lapincoyalucha",
    "https://rsshub.app/instagram/user/movimientosdelfiofio",
    "https://rsshub.app/instagram/user/keuleresiste",
    "https://rsshub.app/instagram/user/globalpilmaiken",
    "https://rsshub.app/instagram/user/redmujeresmapuche",
    "https://rsshub.app/instagram/user/itrofilmongenev",
    "https://rsshub.app/instagram/user/territorionativo.cl",
    "https://rsshub.app/instagram/user/kelluwun_ka_yamuwun",
    "https://rsshub.app/instagram/user/por_juliachunil_valdivia",
    "https://rsshub.app/instagram/user/redmujerespencolirquen",
    "https://rsshub.app/instagram/user/lafkenche.kimun",
    "https://rsshub.app/instagram/user/corte_rebelderevolucionario",
    "https://rsshub.app/instagram/user/mapuexpress",
    "https://rsshub.app/instagram/user/liberacionmapuchelafkenche",
    "https://rsshub.app/instagram/user/coordinadora.territorial.tome",
    "https://rsshub.app/instagram/user/wallmapu_riot",
    "https://rsshub.app/instagram/user/brotes.del.despojo",
    "https://rsshub.app/instagram/user/wallmapu__libre2",
    "https://rsshub.app/instagram/user/trepemulen",
    "https://rsshub.app/instagram/user/resistencia.araucanialx",
    "https://rsshub.app/instagram/user/millarayhuichalaf",
    "https://rsshub.app/instagram/user/pelontuwetemuko",
    "https://rsshub.app/instagram/user/wechekekawin",
    "https://rsshub.app/instagram/user/hogar_relmulikan",
    "https://rsshub.app/instagram/user/editorialpetunewenmuley",
    "https://rsshub.app/instagram/user/libertad_ppmcam",
    "https://rsshub.app/instagram/user/redsuperacionalmodeloforestal",
    "https://rsshub.app/instagram/user/mapuche_warriache",
    "https://rsshub.app/instagram/user/kpl__difusion",
    "https://rsshub.app/instagram/user/mapuguapas",
    "https://rsshub.app/instagram/user/memoriasenresistenciatemuko",
    "https://rsshub.app/instagram/user/no.ticias_sur",
    "https://rsshub.app/instagram/user/ppm_casoquilleco",
    "https://rsshub.app/instagram/user/radioainil",
    "https://rsshub.app/instagram/user/mediolibre_lazarzamora",
    "https://rsshub.app/instagram/user/ppm_cam_a_su_mapu",
    "https://rsshub.app/instagram/user/radiokurruf",
    "https://rsshub.app/instagram/user/reconstruccionnacionalmapuche",
    "https://rsshub.app/instagram/user/mision_permanente_mapuche_onu",
    "https://rsshub.app/twitter/user/info_werken",
    "https://rsshub.app/twitter/user/mapuexpress",
    "https://rsshub.app/twitter/user/RadioKurruf",
    "https://rsshub.app/youtube/custom/@itrofilmongenev",
    "https://rsshub.app/youtube/custom/@ColectivoMapuexpress",
    "https://rsshub.app/youtube/custom/@konahuel",
    "https://rsshub.app/youtube/custom/@TREPEMULEN",
    "https://rsshub.app/youtube/custom/@radiokurruf1601",
    "https://rsshub.app/facebook/page/riopilmaiquen",
    "https://rsshub.app/facebook/page/werken.cl",
    "https://rsshub.app/facebook/page/mawizako",
    "https://rsshub.app/facebook/page/pegundugun",
    "https://rsshub.app/facebook/page/itrofilmongen.envivo",
    "https://rsshub.app/facebook/page/lafken.kimun",
    "https://rsshub.app/facebook/page/Mapuexpress.org",
    "https://rsshub.app/facebook/page/coordinadoraterritorialtome",
    "https://rsshub.app/facebook/page/pilmaiken.qeviva",
    "https://rsshub.app/facebook/page/colectiva.lazarzamora",
    "https://rsshub.app/facebook/page/radiokurruf",
    "https://rsshub.app/facebook/page/CDNukeMapu"
]

PALABRAS_RUIDO = [
    "cuba", 
    "chernobil", 
    "irán", 
    "polonia", 
    "rusia", 
    "ucrania", 
    "españa", 
    "sabadell", 
    "bolivia", 
    "colombia", 
    "gaza", 
    "maratón", 
    "básquet", 
    "fútbol", 
    "itaú", 
    "farándula", 
    "romance", 
    "salud mental", 
    "créditos", 
    "ballet", 
    "danza", 
    "netflix", 
    "aeropuerto", 
    "exhibicionismo", 
    "lenteja", 
    "salmón", 
    "biocultural"
]

LISTA_PPM_CMPC = [
    "claudia nahuelan", 
    "héctor llaitul", 
    "hector llaitul", 
    "elías cona", 
    "elias cona", 
    "fredy marileo", 
    "pelentaro llaitul", 
    "emilio berkhoff", 
    "luis tranamil", 
    "daniel canio", 
    "grollmus"
]

LISTA_PPM_GENERAL = [
    "juan huenupil", 
    "césar millanao", 
    "orlando sáez", 
    "esteban carrera", 
    "bernardo camus", 
    "matías leviqueo", 
    "alexis manríquez", 
    "yerko maril", 
    "francisco huichacura", 
    "esteban huichacura", 
    "carlos huichacura", 
    "manuel huichacura", 
    "víctor llanquileo", 
    "oscar pilquimán", 
    "eliseo raiman", 
    "domingo mariñan", 
    "manuel alonso llempi", 
    "miguel llanquileo", 
    "erick montoya", 
    "pablo cayuhan", 
    "juan mariñan", 
    "camilo astete", 
    "josé luis marilao", 
    "josé melgarejo", 
    "guillermo camus", 
    "miguel torres", 
    "juan cortés", 
    "alejandro liguen", 
    "anthony torres", 
    "pedro palacios", 
    "juan huenchullán", 
    "joaquín millanao", 
    "marco tori", 
    "christopher tori", 
    "juan patricio queipul", 
    "danilo nahuelpi", 
    "luis david morales", 
    "rubén cheuquepan", 
    "leandro catrileo", 
    "josé lienqueo", 
    "axel campos", 
    "luis melinao", 
    "benjamín coñopan", 
    "rodrigo calabrano", 
    "luis fuenzalida", 
    "matías ancalaf", 
    "moroni ancalaf", 
    "jorge caniupil", 
    "oscar cañupan", 
    "rafael pichun", 
    "luis menares", 
    "juan carlos mardones", 
    "roberto garling", 
    "carlos fierro", 
    "luis marileo", 
    "patricio queipul", 
    "raúl caniullan", 
    "nelson queupil", 
    "rodrigo cáceres", 
    "fabian llanca", 
    "josé pichunhuala", 
    "eduardo fuica", 
    "guillermo ñiripil", 
    "celestino córdova"
]

DICCIONARIO_TACTICO = [
    "cam", 
    "coordinadora arauco malleco", 
    "wam", 
    "weichan auka mapu", 
    "rml", 
    "resistencia mapuche", 
    "ort", 
    "incendiario", 
    "atentado", 
    "sabotaje", 
    "emboscada", 
    "usurpación", 
    "robo de madera", 
    "armado", 
    "disparos", 
    "barricadas", 
    "cmpc", 
    "mininco", 
    "forestal", 
    "fundo", 
    "predio", 
    "maquinaria", 
    "skidder", 
    "camión", 
    "faena", 
    "presos políticos mapuche", 
    "ppm", 
    "huelga de hambre", 
    "temucuicui", 
    "peñi", 
    "lamgen", 
    "lamuen", 
    "lof", 
    "weichan"
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

def normalizar_cadena(texto):
    """Compuerta de normalización: purga signos de puntuación y espacios redundantes."""
    t = re.sub(r'[^\w\s]', '', str(texto).lower())
    return re.sub(r'\s+', ' ', t).strip()

def unificar_actor(texto):
    texto = str(texto).lower()
    for clave, valor in ALIAS_ORGANICAS.items():
        if re.search(r'\b' + re.escape(clave) + r'\b', texto): return valor
    if re.search(r'\bcam\b', texto): return "CAM"
    if re.search(r'\bwam\b', texto): return "WAM"
    if re.search(r'\brml\b', texto): return "RML"
    return "Desconocido"

def enviar_alerta_telegram(mensaje):
    if not TELEGRAM_BOT_TOKEN or "TU_TOKEN" in TELEGRAM_BOT_TOKEN:
        print("⚠️ [SISTEMA] Telegram desactivado. Faltan credenciales.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "HTML"}
    try: 
        requests.post(url, json=payload, timeout=10)
    except Exception as e: 
        print(f"[-] Error de conexión con Telegram: {e}")

def decodificar_google_news(url):
    if "news.google.com" in url:
        try:
            decoded_info = new_decoderv1(url)
            if decoded_info and decoded_info.get("decoded_url"): return decoded_info["decoded_url"]
        except: pass
    return url

def extraer_cuerpo_profundo(url_original, fallback_html):
    texto_full = ""
    url_foto = ""
    real_url = decodificar_google_news(url_original)
    
    if "instagram.com" not in real_url and "facebook.com" not in real_url and "rsshub" not in real_url:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            # verify=False permite bypassear problemas de certificados SSL en macOS
            r = requests.get(real_url, headers=headers, timeout=12, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscador visual de la foto oficial de la noticia
            meta_og = soup.find('meta', property='og:image')
            meta_tw = soup.find('meta', attrs={'name': 'twitter:image'})
            
            if meta_og and meta_og.get('content'):
                url_foto = meta_og['content']
            elif meta_tw and meta_tw.get('content'):
                url_foto = meta_tw['content']
            else:
                img = soup.find('article').find('img') if soup.find('article') else soup.find('img')
                if img and img.get('src'):
                    url_foto = img['src']
                    if not url_foto.startswith('http'):
                        url_foto = ""

            parrafos = soup.find_all('p')
            if parrafos: texto_full = " ".join([p.get_text(strip=True) for p in parrafos])
        except: pass
    
    contenido_final = texto_full if len(texto_full) > 100 else BeautifulSoup(fallback_html, "html.parser").get_text()
    return contenido_final[:3500], url_foto, real_url
# --- 3. CEREBRO LOCAL (ACTUALIZADO A GEMMA 2 CON REGLAS DE ETIQUETADO ESTRICTO) ---
def analizar_con_ia_local(titular, contenido):
    prompt = f"""
    Eres un Analista C5I militar evaluando inteligencia. Lee el texto y extrae JSON estricto.
    SI NO ENCUENTRAS EL DATO, ESCRIBE "Ninguno". JAMÁS DEJES UN CAMPO VACÍO ("").

    REGLAS ESTRICTAS:
    1. "actor": Identifica al protagonista real del hecho. Busca siglas u orgánicas (Ej: CAM, RML, WAM, ORT). Usa "Desconocido" ÚNICAMENTE si es un ataque anónimo sin adjudicación.
    2. "ubicacion": Comuna. Si sale el fundo o sector, inclúyelo. 
    3. "accion_digital": ELIGE SOLO UNA: [Ataque Incendiario, Robo de Madera, Procedimiento Policial, Hito Judicial, Declaración Política, Comunicado, Sabotaje / Daños, Hito de Alta Fricción, Ruido / Irrelevante].
    4. "tipologia_oficial": Elige UNA: [Ataque Incendiario, Ataque Armado, Sabotaje / Otros, Procedimiento Policial, Robo de Madera, Usurpación, Manifestación / Alteración del Orden, Evento Cultural Estratégico, Noticia Descartada].
    5. "modificadores": LAS VÍCTIMAS DEL HECHO (Ej: CMPC, Carabineros, Contratista). NUNCA pongas a la CAM, WAM o RML como afectados.
    6. "palabra_clave": EXACTAMENTE DOS (2) conceptos. Las palabras deben ser bigramas o trigramas, no palabras sueltas. PROHIBIDO palabras geográficas. OBLIGATORIO: Si se menciona a CAM, WAM, RMM, ORT o CMPC, DEBES incluirlo.
    7. "analisis_ia": Telegráfico, neutral. MÁXIMO 20 PALABRAS.
    8. "catalizador": Determina el origen. Elige UNA: [Reivindicación Territorial, Conflicto Forestal, Proceso Judicial, Violencia Rural, Accionar Policial, Ninguno].
    
    REGLAS DE GATEKEEPER Y CONTEXTO CULTURAL:
    9. ANTI-FALSO POSITIVO (GATEKEEPER): Si la noticia es sobre delincuencia común urbana, accidentes de tránsito, incendios por ola de calor térmico o farándula, DEBES clasificar la "accion_digital" como "Ruido / Irrelevante".
    10. CONTEXTO CULTURAL ESTRICTO: Eventos como funerales (eluwün), conmemoraciones o ceremonias de miembros de orgánicas (ej. weichafes) NO son eventos inofensivos. Clasifícalos OBLIGATORIAMENTE bajo "accion_digital" como "Hito de Alta Fricción" y su nivel de riesgo no debe ser diluido.
    11. No agregar noticias del "Tren de Aragua".
    12. "latitud" y "longitud": Estima coordenadas aproximadas de la "ubicacion". Si no encuentras, usa "-38.73" y "-72.59".

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

    NOTICIA:
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
        
        if response.status_code != 200:
            print(f"[-] Alerta IA: Ollama respondió con código de error {response.status_code}")
            return None
            
        texto_ia = response.json().get('response', '{}')
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        if match: 
            return json.loads(match.group(0))
        return None
    except Exception as e:
        print(f"[-] Falla crítica de conexión con IA local (Ollama): {e}")
        return None

# --- 4. MOTOR DE PATRULLAJE ---
def patrullaje():
    print(f"🛡️ Iniciando Escaneo Táctico Rápido con IA Local (gemma2:9b)...")
    
    procesadas = set()
    titulares_recientes_24h = set()
    limite_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    try:
        inicio = 0
        fin = 999
        while True:
            res = supabase.table("inteligencia_tactica").select("enlace_noticia, titular, fecha").range(inicio, fin).execute()
            if not res.data: break
            for r in res.data:
                if r.get('enlace_noticia'): procesadas.add(r['enlace_noticia'])
                if r.get('titular') and r.get('fecha'):
                    try:
                        dt_t = datetime.fromisoformat(r['fecha'].replace('Z', '+00:00'))
                        if dt_t.tzinfo is None: dt_t = dt_t.replace(tzinfo=timezone.utc)
                        if dt_t >= limite_24h:
                            titulares_recientes_24h.add(normalizar_cadena(r['titular']))
                    except: pass
            if len(res.data) < 1000: break
            inicio += 1000
            fin += 1000
        print(f"🗄️ Bóveda sincronizada: {len(procesadas)} enlaces históricos y {len(titulares_recientes_24h)} firmas semánticas activas (24h).")
    except Exception as e:
        print(f"⚠️ Error al cargar historial de Supabase: {e}")

    for url_rss in RADARES_RSS:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            respuesta_feed = requests.get(url_rss, headers=headers, timeout=15, verify=False)
            
            if respuesta_feed.status_code != 200: continue
            feed = feedparser.parse(respuesta_feed.content)
            
            for e in feed.entries:
                if e.link in procesadas: continue
                
                titular_norm = normalizar_cadena(e.title)
                
                if titular_norm in titulares_recientes_24h:
                    procesadas.add(e.link)
                    continue

                titular_lower = e.title.lower()
                if any(x in titular_lower for x in ["kast", "parlamentarios", "bancada", "schubert", "aedo"]):
                    titulares_recientes_24h.add(titular_norm)
                    procesadas.add(e.link)
                    continue

                try: 
                    dt_pub = parsedate_to_datetime(e.published) if hasattr(e, 'published') else datetime.now(timezone.utc)
                    if dt_pub.tzinfo is None:
                        dt_pub = dt_pub.replace(tzinfo=timezone.utc)
                    fecha_real = dt_pub.isoformat()
                except: 
                    dt_pub = datetime.now(timezone.utc)
                    fecha_real = dt_pub.isoformat()

                if dt_pub < limite_24h: continue

                html_rss = getattr(e, 'description', '')
                
                texto_profundo, foto_og, enlace_real = extraer_cuerpo_profundo(e.link, html_rss)
                texto_full_eval = (e.title + " " + texto_profundo).lower()
                
                if any(r in texto_full_eval for r in PALABRAS_RUIDO): continue
                
                tiene_tactica = False
                for t in DICCIONARIO_TACTICO:
                    if re.search(r'\b' + re.escape(t) + r'\b', texto_full_eval):
                        tiene_tactica = True
                        break
                        
                if not tiene_tactica: continue

                print(f"⚙️ [IA Local] Analizando NUEVO: {e.title[:40]}...")
                
                es_duplicado = False
                id_evento_original = None
                fuentes_previas = ""

                try:
                    limite_12h = datetime.now(timezone.utc) - timedelta(hours=12)
                    res_recientes = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).limit(50).execute()
                    
                    if res_recientes.data:
                        for ev_db in res_recientes.data:
                            try:
                                dt_ev = datetime.fromisoformat(ev_db['fecha'].replace('Z', '+00:00'))
                                if dt_ev.tzinfo is None:
                                    dt_ev = dt_ev.replace(tzinfo=timezone.utc)
                            except:
                                continue
                                
                            if dt_ev < limite_12h: continue
                                
                            ev_texto = f"Titular: {ev_db.get('titular', '')}. Resumen: {ev_db.get('analisis_ia', '')}. Actor: {ev_db.get('actor', '')}."
                            nueva_noticia_texto = f"Titular: {e.title}. Contenido: {texto_profundo[:500]}"
                            
                            prompt_dedup = f"""
                            Eres un Analista de Inteligencia C5I.
                            Compara el evento registrado en la base de datos con la noticia nueva entrante.
                            
                            Evento Registrado en BBDD: "{ev_texto}"
                            Noticia Nueva Entrante: "{nueva_noticia_texto}"
                            
                            Instrucción: Analista: ¿La noticia nueva reporta el MISMO incidente que el evento registrado? Responde solo SI o NO.
                            """
                            
                            payload_dedup = {
                                "model": "gemma2:9b", 
                                "prompt": prompt_dedup.strip(), 
                                "stream": False, 
                                "options": {"temperature": 0.0}
                            }
                            resp_d = requests.post("http://localhost:11434/api/generate", json=payload_dedup, timeout=30)
                            resp_texto = resp_d.json().get('response', '').strip().upper()
                            
                            if "SI" in resp_texto or "SÍ" in resp_texto:
                                es_duplicado = True
                                id_evento_original = ev_db['id']
                                fuentes_previas = str(ev_db.get('fuentes_adicionales', ''))
                                break
                except Exception as ex_dedup:
                    print(f"⚠️ Advertencia en verificación de ventanal semántico: {ex_dedup}")

                if es_duplicado and id_evento_original:
                    if fuentes_previas and fuentes_previas.strip() != "" and fuentes_previas != "None":
                        if enlace_real not in fuentes_previas:
                            fuentes_actualizadas = f"{fuentes_previas}\n{enlace_real}"
                        else:
                            fuentes_actualizadas = fuentes_previas
                    else:
                        fuentes_actualizadas = enlace_real
                        
                    try:
                        supabase.table("inteligencia_tactica").update({"fuentes_adicionales": fuentes_actualizadas}).eq("id", id_evento_original).execute()
                        print(f"🔗 [Clustering C5I] Impacto mediático sumado. Enlace fusionado al evento ID: {id_evento_original}")
                    except: pass
                    procesadas.add(e.link)
                    titulares_recientes_24h.add(titular_norm)
                    continue  

                ia = analizar_con_ia_local(e.title, texto_profundo)
                
                if ia:
                    for key in ["actor", "ubicacion", "accion_digital", "tipologia_oficial", "catalizador", "modificadores", "palabra_clave", "analisis_ia"]:
                        if not ia.get(key) or str(ia.get(key)).strip() == "" or str(ia.get(key)).lower() == "null":
                            ia[key] = "No especificado"
                else: ia = {}

                actor_final = unificar_actor(titular_lower + " " + texto_profundo)
                if actor_final != "Desconocido": ia['actor'] = actor_final
                
                ia_accion = str(ia.get('accion_digital', 'Comunicado')).title()
                modificadores_ia = str(ia.get('modificadores', 'Ninguno')).strip("[]\"'")
                
                es_cmpc = any(x in texto_full_eval for x in ["cmpc", "mininco"])
                if not es_cmpc:
                    modificadores_ia = re.sub(r'(?i)CMPC|Mininco|Forestal Mininco|CMPC Celulosa|CMPC Maderas|CMPC Tissue', '', modificadores_ia).strip(', ')
                
                modificadores_ia = re.sub(r'(?i)\bCAM\b|\bWAM\b|\bRML\b', '', modificadores_ia).strip(', ')
                if not modificadores_ia or modificadores_ia.lower() == "ninguno" or modificadores_ia == "": 
                    modificadores_ia = "Ninguno"

                if any(x in titular_lower for x in ["detiene", "pdi", "carabineros", "prisión", "formaliza", "condena", "captura"]):
                    ia_accion = "Procedimiento Policial"
                    ia['tipologia_oficial'] = "Procedimiento Policial"
                if "condena" in titular_lower and any(x in titular_lower for x in ["diputado", "gobierno", "ministro", "alcalde", "senador", "kast"]):
                    ia_accion = "Declaración Política"

                ia_accion_upper = ia_accion.upper()
                riesgo, alerta = 2.0, "BAJO"

                if es_cmpc and any(x in ia_accion_upper for x in ["ATAQUE", "ROBO", "INCENDIO", "USURPACIÓN"]):
                    riesgo, alerta = 9.5, "CRÍTICO"
                elif any(x in ia_accion_upper for x in ["ATAQUE", "ROBO", "INCENDIO", "USURPACIÓN"]):
                    riesgo, alerta = 7.5, "ALTO"
                elif "COMUNICADO" in ia_accion_upper:
                    if actor_final in ["CAM", "WAM", "RML"]: riesgo, alerta = 7.5, "ALTO"
                    else: riesgo, alerta = 4.5, "MEDIO"
                elif "POLICIAL" in ia_accion_upper or "JUDICIAL" in ia_accion_upper:
                     riesgo, alerta = 7.5, "ALTO"

                try: str_lat = str(ia.get('latitud', '-38.73'))
                except: str_lat = "-38.73"
                try: str_lon = str(ia.get('longitud', '-72.59'))
                except: str_lon = "-72.59"

                registro = {
                    "fecha": fecha_real,
                    "titular": e.title,
                    "actor": actor_final,
                    "ubicacion": str(ia.get('ubicacion', 'Macrozona Sur')),
                    "catalizador": str(ia.get('catalizador', 'Violencia Rural')),
                    "accion_digital": ia_accion,
                    "tipologia_oficial": str(ia.get('tipologia_oficial', 'Sabotaje / Otros')),
                    "modificadores": modificadores_ia,
                    "puntaje_riesgo": riesgo,
                    "nivel_alerta": alerta,
                    "enlace_noticia": enlace_real,
                    "url_foto": foto_og,
                    "ruta_evidencia_local": obtener_ruta_base(),
                    "latitud": str_lat,
                    "longitud": str_lon,
                    "palabra_clave": str(ia.get('palabra_clave', '')).strip("[]\"'"),
                    "analisis_ia": str(ia.get('analisis_ia', '')).strip("[]\"'"),
                    "fuentes_adicionales": ""  
                }
                supabase.table("inteligencia_tactica").insert(registro).execute()
                procesadas.add(e.link)
                titulares_recientes_24h.add(titular_norm)
                print(f"[+] Inyectado NUEVO EVENTO [{alerta}] a la Bóveda")
                
                # --- INICIO NUEVO GATEKEEPER TELEGRAM ---
                ia_accion_upper = ia_accion.upper()
                
                # 1. Compuerta de bloqueo absoluto (Gatekeeper)
                if "RUIDO" in ia_accion_upper or "IRRELEVANTE" in ia_accion_upper:
                    debe_notificar = False
                    print("🚫 [GATEKEEPER] Noticia detectada como ruido o irrelevante. Descartando envío a Telegram.")
                else:
                    # 2. Evaluación de amenazas reales
                    es_ataque_incendiario = "INCENDIARIO" in ia_accion_upper or "SABOTAJE" in ia_accion_upper
                    es_hito_friccion = "FRICCIÓN" in ia_accion_upper
                    
                    afecta_terceros_forestal = any(x in texto_full_eval for x in ["forestal", "predio", "maquinaria", "skidder", "camión", "arauco", "cmpc"])
                    afecta_trenes = any(x in texto_full_eval for x in ["tren", "línea férrea", "ferroviari", "descarrilamiento"])
                    afecta_infraestructura = any(x in texto_full_eval for x in ["antena", "torre", "puente", "explosivo", "dinamita", "eléctric"])
                    
                    es_baja_relevancia = ia_accion == "Declaración Política" or alerta == "BAJO"
                    
                    debe_notificar = (
                        alerta == "CRÍTICO" or
                        es_hito_friccion or
                        (not es_baja_relevancia and (
                            (es_ataque_incendiario and afecta_terceros_forestal) or
                            afecta_trenes or
                            afecta_infraestructura
                        ))
                    )
                # --- FIN NUEVO GATEKEEPER TELEGRAM ---

                if debe_notificar:
                    try:
                        dt_obj = datetime.fromisoformat(fecha_real.replace('Z', '+00:00'))
                        fecha_str = dt_obj.strftime('%d/%m/%Y %H:%M')
                    except: fecha_str = "Fecha Reciente"

                    emoji = "🔴" if alerta == "CRÍTICO" else "🟠" if alerta == "ALTO" else "🟡" if alerta == "MEDIO" else "🔵"
                    
                    t_accion = html.escape(ia_accion.upper())
                    t_fecha = html.escape(fecha_str)
                    t_ubicacion = html.escape(str(ia.get('ubicacion', 'Macrozona Sur')))
                    t_actor = html.escape(actor_final)
                    t_obj = html.escape(modificadores_ia)
                    t_titular = html.escape(e.title)
                    t_resumen = html.escape(str(ia.get('analisis_ia', '')))
                    t_tipo = html.escape(str(ia.get('tipologia_oficial', 'Sabotaje / Otros')))

                    mensaje_tg = f"<b>{emoji} ALERTA DE INTELIGENCIA: {t_accion}</b>\n\n<b>Tipología:</b> {t_tipo}\n<b>Fecha:</b> {t_fecha}\n<b>Ubicación:</b> {t_ubicacion}\n<b>Actor:</b> {t_actor}\n<b>Objetivo/Afectación:</b> {t_obj}\n<b>Titular:</b> {t_titular}\n\n<b>Análisis IA:</b> <i>{t_resumen}</i>\n\n<a href='{enlace_real}'>🔗 Enlace a la fuente</a>"
                    enviar_alerta_telegram(mensaje_tg)
                    print(f"📲 [NOTIFICACIÓN ENVIADA] Alerta despachada a Telegram.")
                        
        except: pass

if __name__ == "__main__":
    while True:
        patrullaje()
        print("⏳ Enfriamiento motor: 15 min...")
        time.sleep(900)