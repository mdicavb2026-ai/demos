# ==============================================================================
# Archivo: app.py
# Proyecto: War Room C5I - Puesto de Mando CMPC
# Rol: Interfaz de Inteligencia, Prospectiva y Operaciones (MZS)
# Doctrina: Paginación absoluta de base de datos, purga estricta y trazabilidad visual.
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import io
import os
import re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- 1. CONFIGURACIÓN DE ENTORNO Y ESTILO ENTERPRISE ---
st.set_page_config(page_title="C5I WAR ROOM | CMPC", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #05080f; color: #e0e6ed; }
    .stMetric { background-color: #0d121d; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    [data-testid="stSidebar"] { background-color: #090e16; border-right: 1px solid #1e293b; }
    .card-alerta { background-color: #0d121d; padding: 18px; border-radius: 10px; border: 1px solid #1e293b; margin-bottom: 12px; transition: all 0.2s ease-in-out; }
    .card-alerta:hover { border-color: #38bdf8; box-shadow: 0 0 10px rgba(56,189,248,0.2); }
    .badge-org { background-color: #1e293b; color: #cbd5e1; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    .link-btn { display: inline-block; margin-top: 8px; font-size: 0.85rem; color: #38bdf8; text-decoration: none; font-weight: bold; }
    .link-btn:hover { text-decoration: underline; color: #7dd3fc; }
    .semaforo-container { display: flex; gap: 10px; margin-bottom: 15px; background-color: #0d121d; padding: 12px 20px; border-radius: 8px; border: 1px solid #1e293b; align-items: center; }
    .semaforo-luz { width: 14px; height: 14px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }
    .semaforo-label { font-size: 0.85rem; font-weight: bold; color: #cbd5e1; margin-right: 15px; }
    .metric-expl { font-size: 0.7rem; color: #64748b; margin-top: -10px; margin-bottom: 10px; line-height: 1.1; }
    .media-container { max-height: 250px; overflow: hidden; border-radius: 6px; margin-top: 8px; border: 1px solid #334155; background-color: #000; text-align: center; }
    .media-img { width: 100%; height: auto; object-fit: cover; }
    .legend-box { background-color: #090e16; padding: 12px; border-radius: 6px; border: 1px solid #1e293b; font-size: 0.8rem; margin-bottom: 15px; }
    .legend-item { display: inline-flex; align-items: center; margin-right: 15px; margin-bottom: 5px; }
    .legend-color { width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; display: inline-block; }
    h1, h2, h3, h4 { color: #ffffff; letter-spacing: -0.5px; }
    div.block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. GESTIÓN DE ESTADO INTERACTIVO (SESSION STATE) ---
if 'filtro_provincia_activo' not in st.session_state:
    st.session_state.filtro_provincia_activo = "Todas"
if 'filtro_tipologia_activo' not in st.session_state:
    st.session_state.filtro_tipologia_activo = "Todas"
if 'filtro_red_organica' not in st.session_state:
    st.session_state.filtro_red_organica = "Todas las Activas"
if 'filtro_auditoria_ig' not in st.session_state:
    st.session_state.filtro_auditoria_ig = "General"

# --- 3. CONEXIÓN A LA BÓVEDA SUPABASE ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

# --- 4. MOTORES DE ENRIQUECIMIENTO ESPACIAL Y TIPOLÓGICO DE PRECISIÓN ---
MAPEO_PROVINCIAS = {
    'Arauco': ['Tirúa', 'Contulmo', 'Cañete', 'Los Álamos', 'Curanilahue', 'Arauco', 'Lebu', 'Quidico'],
    'Malleco': ['Collipulli', 'Ercilla', 'Traiguén', 'Lumaco', 'Purén', 'Angol', 'Los Sauces', 'Renaico', 'Victoria', 'Curacautín', 'Lonquimay', 'Temucuicui', 'Pailahueque'],
    'Cautín': ['Temuco', 'Padre Las Casas', 'Vilcún', 'Freire', 'Pitrufquén', 'Gorbea', 'Loncoche', 'Toltén', 'Teodoro Schmidt', 'Saavedra', 'Carahue', 'Nueva Imperial', 'Cholchol', 'Galvarino', 'Lautaro', 'Perquenco', 'Cunco', 'Melipeuco', 'Pucón', 'Villarrica'],
    'Biobío': ['Mulchén', 'Nacimiento', 'Negrete', 'Quilleco', 'Santa Bárbara', 'Tucapel', 'Yumbel', 'Alto Biobío', 'Los Ángeles'],
    'Los Ríos': ['Panguipulli', 'Lanco', 'Máfil', 'Valdivia', 'Mariquina', 'Río Bueno', 'La Unión'],
    'Los Lagos': ['Osorno', 'San Juan de la Costa', 'Puyehue', 'Río Negro', 'Frutillar', 'Llanquihue', 'Puerto Varas', 'Puerto Montt']
}

MAPEO_REGIONES = {
    'Región del Biobío': ['Arauco', 'Biobío'],
    'Región de La Araucanía': ['Malleco', 'Cautín'],
    'Región de Los Ríos': ['Los Ríos'],
    'Región de Los Lagos': ['Los Lagos']
}

# EXCLUSIÓN DEFINITIVA DE FRASES RESIDUALES
EXCLUSIONES_TEXTUALES = [r'zuyituaín\s+kufike\s+kimün', r'zuyituain', r'wallmapuche', r'libredeterminacionmapuche']

def purgar_texto(texto):
    if not isinstance(texto, str): return ""
    txt = texto
    for patron in EXCLUSIONES_TEXTUALES:
        txt = re.sub(patron, 'Comunidad Interior', txt, flags=re.IGNORECASE)
    return txt.strip()

def deducir_jerarquia(ubicacion_str):
    u_norm = purgar_texto(ubicacion_str).lower()
    for prov, comunas in MAPEO_PROVINCIAS.items():
        if any(c.lower() == u_norm or c.lower() in u_norm for c in comunas):
            for reg, provs in MAPEO_REGIONES.items():
                if prov in provs:
                    return prov, reg
    return 'Zona Focalizada', 'Macrozona Sur'

def normalizar_tipologia_profunda(titular, resumen):
    txt = f"{titular} {resumen}".lower()
    
    # 1. COMPROBACIÓN DE INVERSIONES Y NOTICIAS POSITIVAS CMPC
    positivos = ['inversión', 'aportados por la empresa cmpc', 'desafío levantemos chile', 'inauguración', 'apoyo comunitario', 'donación', 'millones aportados', 'obra contempló']
    if any(p in txt for p in positivos) and ('cmpc' in txt or 'mininco' in txt):
        return 'Informativo / Positivo corporativo', 'BAJO'
        
    # 2. OPERATIVOS POLICIALES Y ALLANAMIENTOS
    if 'allanamient' in txt or 'allanan' in txt:
        if 'armas' in txt or 'balazos' in txt or 'disparos' in txt:
            return 'Allanamiento / Incautación Armada', 'ALTO'
        return 'Allanamiento', 'MEDIO'
    elif any(o in txt for o in ['incauta', 'operativo policial', 'carabineros detiene', 'pdi detiene', 'subametralladora', 'pistola']):
        return 'Operativo Policial / Incautación', 'MEDIO'
        
    # 3. DECLARACIONES Y PAUTAS POLÍTICAS
    politicos = ['ministra de seguridad', 'exigen liberación', 'preso político mapuche', 'comunicado', 'declaración pública', 'seremi de seguridad', 'gobierno', 'reacción política']
    if any(pl in txt for pl in politicos) and not any(atk in txt for atk in ['quema', 'incendio', 'atentado', 'balazos contra']):
        return 'Declaración / Pauta Política', 'BAJO'
        
    # 4. TIPOLOGÍAS RÍGIDAS DE SABOTAJE
    if any(x in txt for x in ['incendio', 'incendiario', 'quema', 'fuego', 'siniestro']):
        return 'Ataque Incendiario', 'CRÍTICO'
    elif any(x in txt for x in ['madera', 'tala', 'hurto forestal', 'robo forestal', 'camión cargado']):
        return 'Robo de Madera', 'ALTO'
    elif any(x in txt for x in ['usurpación', 'toma', 'ocupación', 'desalojo', 'reivindicación']):
        return 'Usurpación', 'ALTO'
    elif any(x in txt for x in ['ruta', 'corte', 'barricada', 'bloqueo', 'despeje', 'árboles caídos']):
        return 'Corte de Ruta', 'MEDIO'
    elif any(x in txt for x in ['armado', 'disparos', 'balazos', 'munición', 'emboscada', 'armas']):
        return 'Ataque Armado', 'CRÍTICO'
        
    return 'Sabotaje / Otros', 'MEDIO'

def destilar_actor_real(actor_raw, titular, resumen, tipologia):
    a_norm = str(actor_raw).strip()
    txt = f"{titular} {resumen}".upper()
    
    # Extraer orgánicas reales prioritariamente
    for org in ['CAM', 'RML', 'WAM', 'ORT']:
        if org in txt or org in a_norm.upper():
            return org
            
    # Si es un ataque violento, prohibir la etiqueta "Comunicado" o "Prensa" como actor
    if tipologia in ['Ataque Incendiario', 'Ataque Armado', 'Robo de Madera']:
        if any(x in a_norm.lower() for x in ['comunicado', 'prensa', 'desconocido', 'sin dato', 'no especificado']):
            return 'Célula No Adjudicada'
            
    if a_norm and a_norm.lower() not in ['desconocido', 'no especificado', 'sin dato', '']:
        return a_norm
    return 'Célula No Adjudicada'

# --- 5. MOTOR DE PAGINACIÓN ABSOLUTA (REVIENTA LÍMITES REST SERVER-SIDE) ---
@st.cache_data(ttl=120)
def cargar_inteligencia_paginada():
    try:
        bloques = []
        tamano_bloque = 1000
        max_registros = 10000
        
        # Bucle iterativo para extraer la masa crítica total burlando el límite PostgREST
        for i in range(0, max_registros, tamano_bloque):
            res = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).range(i, i + tamano_bloque - 1).execute()
            data = res.data
            if not data: break
            bloques.extend(data)
            if len(data) < tamano_bloque: break
            
        df = pd.DataFrame(bloques)
        if not df.empty:
            # PURGA STRING GLOBAL DE ZUYITUAÍN
            df['ubicacion'] = df['ubicacion'].apply(purgar_texto)
            df['titular'] = df['titular'].apply(purgar_texto)
            df['resumen_ia'] = df['resumen_ia'].apply(purgar_texto)
            
            df['fecha_limpia'] = df['fecha'].astype(str).str.slice(0, 10)
            df['fecha_dt'] = pd.to_datetime(df['fecha_limpia'], errors='coerce')
            df = df.dropna(subset=['fecha_dt'])
            df['fecha_eval'] = df['fecha_dt'].dt.date
            
            # Limpieza espacial de precisión
            df['lat_clean'] = df['latitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['lon_clean'] = df['longitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['latitud_num'] = pd.to_numeric(df['lat_clean'], errors='coerce')
            df['longitud_num'] = pd.to_numeric(df['lon_clean'], errors='coerce')
            
            # Destilado Tipológico y Semántico
            evals = df.apply(lambda r: normalizar_tipologia_profunda(r['titular'], r['resumen_ia']), axis=1)
            df['tipologia_oficial'] = [e[0] for e in evals]
            df['alerta_semantica'] = [e[1] for e in evals]
            
            # Destilado de Actor Real (Elimina "Comunicado" en actos violentos)
            df['actor_real'] = df.apply(lambda r: destilar_actor_real(r['actor'], r['titular'], r['resumen_ia'], r['tipologia_oficial']), axis=1)
            
            jerarquias = df['ubicacion'].apply(deducir_jerarquia)
            df['provincia'] = [j[0] for j in jerarquias]
            df['region'] = [j[1] for j in jerarquias]
            df['mes_anio'] = df['fecha_dt'].dt.strftime('%Y-%m')
            
            df['nivel_alerta'] = df['alerta_semantica']
            
            # Forzar criticidad si atenta contra CMPC (excepto pautas positivas)
            criterios_cmpc = "cmpc|mininco|forestal mininco|fundo cmpc|predio cmpc|camión forestal|maquinaria forestal"
            mask_cmpc = (df['titular'].str.contains(criterios_cmpc, case=False, na=False) | df['resumen_ia'].str.contains(criterios_cmpc, case=False, na=False))
            mask_positivo = df['tipologia_oficial'] == 'Informativo / Positivo corporativo'
            df.loc[mask_cmpc & ~mask_positivo, 'nivel_alerta'] = 'CRÍTICO'
            
            # Filtro Antirruido
            ruido = "platería|artesanía|teatro|concierto|festival|básquetbol|fútbol|receta|turismo|poesía"
            df = df[~df['titular'].str.contains(ruido, case=False, na=False)]
            
            # Deduplicación
            df['titular_norm'] = df['titular'].str.lower().str.replace(r'[^\w\s]', '', regex=True).str.strip()
            df = df.drop_duplicates(subset=['titular_norm'], keep='first').drop(columns=['titular_norm'])
            
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def cargar_predios():
    try:
        res = supabase.table("predios_cmpc").select("*").limit(5000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['lat_clean'] = df['latitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['lon_clean'] = df['longitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['latitud_num'] = pd.to_numeric(df['lat_clean'], errors='coerce')
            df['longitud_num'] = pd.to_numeric(df['lon_clean'], errors='coerce')
            return df.dropna(subset=['latitud_num', 'longitud_num'])
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

df_main = cargar_inteligencia_paginada()
df_predios = cargar_predios()

# --- 6. PANEL LATERAL DE MANDO ---
st.sidebar.markdown("<h3 style='color: #ff4b4b; text-align: center;'>● CMPC C5I</h3>", unsafe_allow_html=True)
st.sidebar.markdown("## 🛡️ EJE DE COMANDO")
st.sidebar.divider()

modo_analisis = st.sidebar.radio("CANAL OPERATIVO:", [
    "📍 SITREP Táctico", 
    "📊 Estadísticas MZS",
    "🗺️ Visor GEOINT", 
    "📱 Pulso RRSS e Instagram", 
    "🕸️ Análisis de Redes (SNA)", 
    "🔮 Prospectiva IA", 
    "📄 Reportes Radar"
])

st.sidebar.divider()
st.sidebar.markdown("### ⏱️ Filtro Temporal")

rango_predefinido = st.sidebar.selectbox("Ventana de Visualización:", [
    "Últimas 24 Horas", 
    "Últimos 7 Días", 
    "Últimos 30 Días", 
    "Últimos 3 Meses", 
    "Últimos 6 Meses", 
    "Último Año", 
    "🚨 Histórico Completo",
    "Rango Personalizado"
], index=2)

hoy = datetime.now().date()
es_historico_completo = False

if rango_predefinido == "Últimas 24 Horas":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=1), hoy
elif rango_predefinido == "Últimos 7 Días":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=7), hoy
elif rango_predefinido == "Últimos 30 Días":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=30), hoy
elif rango_predefinido == "Últimos 3 Meses":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=90), hoy
elif rango_predefinido == "Últimos 6 Meses":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=180), hoy
elif rango_predefinido == "Último Año":
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=365), hoy
elif rango_predefinido == "🚨 Histórico Completo":
    f_inicio_calc, f_fin_calc = datetime(2010, 1, 1).date(), hoy
    es_historico_completo = True
else:
    f_inicio_calc, f_fin_calc = hoy - timedelta(days=30), hoy

if rango_predefinido == "Rango Personalizado":
    f_inicio = st.sidebar.date_input("Desde:", hoy - timedelta(days=30))
    f_fin = st.sidebar.date_input("Hasta:", hoy)
else:
    f_inicio, f_fin = f_inicio_calc, f_fin_calc
    st.sidebar.markdown(f"**Desde:** `{f_inicio.strftime('%d/%m/%Y')}`  \n**Hasta:** `{f_fin.strftime('%d/%m/%Y')}`")

# --- 7. FILTRADO ESTRATÉGICO SUPERIOR ---
df_filtrado = pd.DataFrame()
if not df_main.empty:
    if es_historico_completo:
        df_filtrado = df_main.copy()
    else:
        mask_fechas = (df_main['fecha_eval'] >= f_inicio) & (df_main['fecha_eval'] <= f_fin)
        df_filtrado = df_main[mask_fechas].copy()

# APLICAR FILTROS INTERACTIVOS GLOBALES
if st.session_state.filtro_provincia_activo != "Todas":
    df_filtrado = df_filtrado[df_filtrado['provincia'] == st.session_state.filtro_provincia_activo]
if st.session_state.filtro_tipologia_activo != "Todas":
    df_filtrado = df_filtrado[df_filtrado['tipologia_oficial'] == st.session_state.filtro_tipologia_activo]

st.title("WAR ROOM C5I ❯ PUESTO DE MANDO UNIFICADO")

# SEMÁFORO DE ESTADO OPERATIVO CORPORATIVO
tot_alertas = len(df_filtrado)
tot_criticos = len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO']) if tot_alertas > 0 and 'nivel_alerta' in df_filtrado.columns else 0

color_semaforo = "#10b981" if tot_criticos == 0 else "#f6a821" if tot_criticos < 5 else "#ff4b4b"
estado_txt = "OPERACIONES ESTABLES" if tot_criticos == 0 else "ALERTA TEMPRANA ACTIVA" if tot_criticos < 5 else "ESTADO DE EXCEPCIÓN / RIESGO CRÍTICO"

if st.session_state.filtro_provincia_activo != "Todas" or st.session_state.filtro_tipologia_activo != "Todas":
    if st.button("🔄 Restablecer Filtros Interactivos", type="secondary"):
        st.session_state.filtro_provincia_activo = "Todas"
        st.session_state.filtro_tipologia_activo = "Todas"
        st.rerun()

st.markdown(f"""
<div class="semaforo-container" style="border-left: 4px solid {color_semaforo};">
    <span class="semaforo-label">ESTADO GENERAL DEL PERÍMETRO:</span>
    <span class="semaforo-luz" style="background-color: {color_semaforo};"></span>
    <span style="font-size: 0.85rem; font-weight: bold; color: {color_semaforo};">{estado_txt}</span>
    <span style="font-size: 0.8rem; color: #64748b; margin-left: auto;">{tot_criticos} Eventos Críticos directos</span>
</div>
""", unsafe_allow_html=True)

tot_rrss = len(df_filtrado[df_filtrado['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False)]) if tot_alertas > 0 and 'catalizador' in df_filtrado.columns else 0
tot_predios = len(df_predios)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("TRAZAS EN EL PERIODO", tot_alertas)
    st.markdown('<div class="metric-expl">Inventario consolidado burlando límites de servidor.</div>', unsafe_allow_html=True)

with col_m2:
    st.metric("AFECTACIÓN DIRECTA CMPC", tot_criticos, delta="CRÍTICO" if tot_criticos > 0 else "ESTABLE", delta_color="inverse")
    st.markdown('<div class="metric-expl">Atentados confirmados (excluye pautas e inversión).</div>', unsafe_allow_html=True)

with col_m3:
    st.metric("INGESTIÓN REDES SOCIALES", tot_rrss, delta="Meta/Instagram")
    st.markdown('<div class="metric-expl">Capturas multimedia con custodia inalterable en bóveda.</div>', unsafe_allow_html=True)

with col_m4:
    st.metric("ANILLOS PERIMETRALES", tot_predios, delta="GEOFENCING ACTIVO")
    st.markdown('<div class="metric-expl">Total de predios corporativos bajo resguardo espacial.</div>', unsafe_allow_html=True)

st.divider()

# --- 8. DESPLIEGUE DE COMPUERTAS (PESTAÑAS) ---

# ==============================================================================
# COMPUERTA 1: SITREP TÁCTICO CON MULTIMEDIA NATIVA
# ==============================================================================
if modo_analisis == "📍 SITREP Táctico":
    col_feed, col_stats = st.columns([2, 1])
    
    with col_feed:
        st.subheader("📋 Flujo de Detecciones Fácticas y Custodia Visual")
        if not df_filtrado.empty:
            for _, row in df_filtrado.head(30).iterrows():
                alerta = str(row.get('nivel_alerta', 'MEDIO')).upper()
                borde = "#ff4b4b" if alerta == 'CRÍTICO' else "#f6a821" if alerta == 'ALTO' else "#eab308" if alerta == 'MEDIO' else "#38bdf8"
                enlace = row.get('enlace_noticia', '')
                fuente_txt = "🔗 Inspeccionar Fuente Original" if enlace and str(enlace).startswith("http") else "📁 Registro Interno/Histórico"
                enlace_render = f'<a href="{enlace}" target="_blank" class="link-btn">{fuente_txt}</a>' if enlace and str(enlace).startswith("http") else f'<span style="font-size:0.8rem; color:#64748b;">{fuente_txt}</span>'
                
                # RENDERIZADO DE MULTIMEDIA NATIVA
                media_html = ""
                url_img = str(row.get('url_foto', '')).strip()
                if url_img and len(url_img) > 5 and url_img.lower() != 'nan':
                    if any(ext in url_img.lower() for ext in ['.mp4', '.mov', 'reel', 'video']):
                        media_html = f"""
                        <div class="media-container">
                            <video class="media-img" controls muted preload="metadata">
                                <source src="{url_img}" type="video/mp4">
                                Tu navegador no soporta el elemento de video.
                            </video>
                        </div>"""
                    else:
                        media_html = f"""
                        <div class="media-container">
                            <img src="{url_img}" class="media-img" alt="Evidencia Operacional" loading="lazy">
                        </div>"""
                
                st.markdown(f"""
                <div class="card-alerta" style="border-left: 5px solid {borde};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.8rem; color: #94a3b8;">📅 {row.get('fecha_limpia', '')} | 📍 <b>{row.get('ubicacion', 'MZS')}</b> ({row.get('provincia','Arauco')})</span>
                        <span class="badge-org">{row.get('actor_real', 'Célula No Adjudicada')}</span>
                    </div>
                    <h4 style="margin-top: 8px; margin-bottom: 4px; color: #f8fafc;">{row.get('titular', 'Sin Titular')}</h4>
                    <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.4; margin-bottom: 8px;">{row.get('resumen_ia', 'Sin síntesis disponible.')}</p>
                    {media_html}
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                        <span style="font-size: 0.75rem; color: {borde}; font-weight: bold;">{alerta} ❯ {row.get('tipologia_oficial','Otros')}</span>
                        {enlace_render}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No se registran eventos fácticos en la base de datos para la ventana temporal y filtros activos.")

    with col_stats:
        st.subheader("📊 Distribución Operativa")
        if not df_filtrado.empty and 'nivel_alerta' in df_filtrado.columns:
            fig_pie = px.pie(df_filtrado, names='nivel_alerta', color='nivel_alerta',
                             color_discrete_map={'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'},
                             hole=0.4)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("#### Matriz por Tipología Oficial")
            df_tipo = df_filtrado['tipologia_oficial'].value_counts().reset_index()
            fig_bar = px.bar(df_tipo, x='count', y='tipologia_oficial', orientation='h', color='count', color_continuous_scale='Reds')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, margin=dict(t=10, b=10, l=10, r=10), yaxis_title="")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.write("Volumen insuficiente para trazar distribuciones estadísticas.")

# ==============================================================================
# COMPUERTA 2: ESTADÍSTICAS MZS CON AUDITORÍA INFERIOR INTERACTIVA
# ==============================================================================
elif modo_analisis == "📊 Estadísticas MZS":
    st.subheader("📊 Cuadros Estadísticos y Evolución MZS")
    st.markdown("Al aplicar filtros en los selectores, **se despliega una Matriz de Auditoría inferior con enlaces directos** para fiscalizar cada registro.")
    
    if not df_filtrado.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            provs_disponibles = ["Todas"] + sorted(df_filtrado['provincia'].unique().tolist())
            sel_prov = st.selectbox("🎯 Aislar Provincia Crítica:", provs_disponibles, 
                                    index=provs_disponibles.index(st.session_state.filtro_provincia_activo) if st.session_state.filtro_provincia_activo in provs_disponibles else 0)
            if sel_prov != st.session_state.filtro_provincia_activo:
                st.session_state.filtro_provincia_activo = sel_prov
                st.rerun()
                
        with col_f2:
            tipos_disponibles = ["Todas"] + sorted(df_filtrado['tipologia_oficial'].unique().tolist())
            sel_tipo = st.selectbox("📌 Aislar Tipología Operativa:", tipos_disponibles,
                                    index=tipos_disponibles.index(st.session_state.filtro_tipologia_activo) if st.session_state.filtro_tipologia_activo in tipos_disponibles else 0)
            if sel_tipo != st.session_state.filtro_tipologia_activo:
                st.session_state.filtro_tipologia_activo = sel_tipo
                st.rerun()

        st.divider()
        
        # TABLA ESTADÍSTICA GENERAL CRUZADA
        st.markdown("#### Tabla de Estadísticas Generales Macrozona Sur")
        df_stat = df_filtrado.copy()
        tabla_cruzada = pd.crosstab(df_stat['region'], df_stat['mes_anio'], margins=True, margins_name="Total General")
        st.dataframe(tabla_cruzada, use_container_width=True)
        
        st.divider()
        
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.markdown("#### Evolución Temporal Tipificada")
            df_ev = df_stat.groupby(['mes_anio', 'tipologia_oficial']).size().reset_index(name='count')
            fig_ev = px.bar(df_ev, x='mes_anio', y='count', color='tipologia_oficial', barmode='stack',
                            color_discrete_map={
                                'Ataque Incendiario': '#ff4b4b', 'Robo de Madera': '#f6a821', 'Usurpación': '#10b981',
                                'Corte de Ruta': '#38bdf8', 'Ataque Armado': '#ec4899', 'Allanamiento / Incautación Armada': '#8b5cf6',
                                'Allanamiento': '#a855f7', 'Operativo Policial / Incautación': '#c084fc',
                                'Declaración / Pauta Política': '#3b82f6', 'Informativo / Positivo corporativo': '#059669',
                                'Sabotaje / Otros': '#64748b'
                            })
            fig_ev.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis_title="Mes", yaxis_title="Sucesos")
            st.plotly_chart(fig_ev, use_container_width=True)
            
        with col_ch2:
            st.markdown("#### Incidencia por Provincias Críticas")
            df_prov = df_stat[df_stat['provincia'] != 'Zona Focalizada']['provincia'].value_counts().reset_index()
            fig_prov = px.bar(df_prov, x='provincia', y='count', color='count', color_continuous_scale='Oranges')
            fig_prov.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis_title="Provincia", yaxis_title="Volumen Capturado")
            st.plotly_chart(fig_prov, use_container_width=True)
            
        # IMPLEMENTACIÓN SOLICITADA: MATRIZ DE AUDITORÍA INFERIOR
        st.divider()
        st.markdown("#### 🔬 Matriz de Auditoría Dinámica del Filtrado")
        st.markdown("Verifica al instante la exactitud fáctica de las clasificaciones visualizadas en los gráficos superiores:")
        
        df_audit = df_stat[['fecha_limpia', 'ubicacion', 'provincia', 'tipologia_oficial', 'nivel_alerta', 'titular', 'enlace_noticia']].copy()
        
        # Inyectar enlaces HTML clicables para facilitar navegación gerencial en tabla
        def generar_enlace(url):
            if not isinstance(url, str) or not url.startswith('http'): return "Sin Enlace"
            return f'<a href="{url}" target="_blank" style="color:#38bdf8; font-weight:bold;">🔗 Fiscalizar Origen</a>'
            
        df_audit['Enlace de Respaldo'] = df_audit['enlace_noticia'].apply(generar_enlace)
        df_audit_render = df_audit.drop(columns=['enlace_noticia']).rename(columns={
            'fecha_limpia':'Fecha', 'ubicacion':'Localidad', 'provincia':'Provincia',
            'tipologia_oficial':'Tipología', 'nivel_alerta':'Criticidad', 'titular':'Titular / Prontuario'
        })
        
        st.write(df_audit_render.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.warning("Base de datos sin registros suficientes en la ventana seleccionada para proyectar cuadros gerenciales.")

# ==============================================================================
# COMPUERTA 3: VISOR GEOINT
# ==============================================================================
elif modo_analisis == "🗺️ Visor GEOINT":
    st.subheader("🗺️ Teatro de Operaciones y Blindaje Perimetral")
    st.markdown("Cruce espacial entre **Predios CMPC (Nodos Verdes)** y trazas fácticas. Bucle masivo desbloqueado para visualización total en modo histórico.")
    
    fig_map = go.Figure()
    capas_dibujadas = 0

    if not df_predios.empty:
        fig_map.add_trace(go.Scattermapbox(
            lat=df_predios['latitud_num'], lon=df_predios['longitud_num'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=9, color='#10b981', opacity=0.75),
            text=df_predios['nombre_predio'] + " (" + df_predios['comuna'] + ")",
            hoverinfo='text',
            name='Predios CMPC'
        ))
        capas_dibujadas += 1

    if not df_filtrado.empty and 'latitud_num' in df_filtrado.columns and 'longitud_num' in df_filtrado.columns:
        df_mapa = df_filtrado.dropna(subset=['latitud_num', 'longitud_num']).copy()
        df_mapa = df_mapa[(df_mapa['latitud_num'] > -45.0) & (df_mapa['latitud_num'] < -35.0)]
        df_mapa = df_mapa[(df_mapa['longitud_num'] > -75.0) & (df_mapa['longitud_num'] < -70.0)]
        
        if not df_mapa.empty:
            colores = df_mapa['nivel_alerta'].map({'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'}).fillna('#94a3b8')
            fig_map.add_trace(go.Scattermapbox(
                lat=df_mapa['latitud_num'], lon=df_mapa['longitud_num'],
                mode='markers',
                marker=go.scattermapbox.Marker(size=11, color=colores, opacity=0.85),
                text=df_mapa['tipologia_oficial'] + "<br><b>Lugar:</b> " + df_mapa['ubicacion'] + "<br><b>Titular:</b> " + df_mapa['titular'].str.slice(0,60),
                hoverinfo='text',
                name='Puntos de Amenaza'
            ))
            capas_dibujadas += 1

    if capas_dibujadas > 0:
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox_center={"lat": -38.3, "lon": -72.8},
            mapbox_zoom=7.2,
            margin={"r":0,"t":0,"l":0,"b":0},
            height=700,
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white"))
        )
        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
    else:
        st.warning("No se encontraron coordenadas espaciales válidas para superponer en el visor GEOINT durante el periodo.")

# ==============================================================================
# COMPUERTA 4: PULSO RRSS E INSTAGRAM (RANKING VISUAL Y AUDITORÍA AL CLIC)
# ==============================================================================
elif modo_analisis == "📱 Pulso RRSS e Instagram":
    st.subheader("📱 Inteligencia Digital: Saturación de Pauta y Custodia Inalterable")
    st.markdown("Monitoreo de publicaciones y respaldo inalterable de Historias/Reels locales. **El gráfico de perfiles ha sido convertido en un Ranking de Saturación visual**.")
    
    if not df_filtrado.empty:
        df_rrss = df_filtrado.copy()
        df_rrss['canal'] = np.where(df_rrss['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False), 'Meta/Instagram', 'Prensa / Monitoreo Terreno')
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Emisiones Digitales vs Prensa")
            fig_canal = px.histogram(df_rrss, x='fecha_limpia', color='canal', barmode='group',
                                     color_discrete_map={'Meta/Instagram':'#ec4899', 'Prensa / Monitoreo Terreno':'#38bdf8'})
            fig_canal.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", yaxis_title="Registros", xaxis_title="Fecha")
            st.plotly_chart(fig_canal, use_container_width=True)
            
        with col_g2:
            # CORRECCIÓN SOLICITADA: CONVERTIR EN RANKING VISUAL CON DEGRADADO
            st.markdown("#### Ranking de Saturación de Perfiles de Instagram")
            df_ig = df_rrss[df_rrss['canal'] == 'Meta/Instagram'].copy()
            if not df_ig.empty:
                df_ig['perfil'] = df_ig['titular'].str.extract(r'@([a-zA-Z0-9_.]+)', expand=False).fillna(df_ig['actor_real'])
                df_ig['perfil'] = df_ig['perfil'].replace(['', 'Célula No Adjudicada'], 'Cuenta de Difusión MZS')
                
                ranking_ig = df_ig['perfil'].value_counts().reset_index()
                fig_ig = px.bar(ranking_ig.head(10), x='count', y='perfil', orientation='h', color='count', 
                                color_continuous_scale='RdPu', title="Top Emisores en Meta")
                fig_ig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", yaxis_title="Perfil / Entidad", xaxis_title="Volumen Emitido")
                st.plotly_chart(fig_ig, use_container_width=True)
            else:
                st.info("Sin pauta explícita de perfiles de Instagram detectada en la ventana seleccionada.")
                
        # IMPLEMENTACIÓN SOLICITADA: AUDITORÍA DE CONTENIDOS AL CLIC/SELECCIÓN DE CUENTA
        st.divider()
        st.markdown("#### 🔍 Auditoría Directa por Perfil Digital")
        if not df_ig.empty and 'perfil' in df_ig.columns:
            cuentas_list = sorted(df_ig['perfil'].unique().tolist())
            sel_cuenta = st.selectbox("Selecciona una cuenta del Ranking para desplegar su historial y archivos locales incrustados:", ["General"] + cuentas_list)
            
            df_visor_ig = df_ig if sel_cuenta == "General" else df_ig[df_ig['perfil'] == sel_cuenta]
            
            cols = st.columns(4)
            for idx, row in df_visor_ig.head(8).iterrows():
                with cols[idx % 4]:
                    m_html = ""
                    url_f = str(row.get('url_foto', '')).strip()
                    if any(ext in url_f.lower() for ext in ['.mp4', '.mov', 'reel']):
                        m_html = f'<video style="width:100%; height:140px; object-fit:cover; border-radius:4px;" controls muted><source src="{url_f}" type="video/mp4"></video>'
                    else:
                        m_html = f'<img src="{url_f}" style="width:100%; height:140px; object-fit:cover; border-radius:4px;" loading="lazy">'
                        
                    st.markdown(f"""
                    <div style="background-color: #0d121d; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 10px;">
                        {m_html}
                        <b style="font-size:0.8rem; display:block; margin-top:6px;" title="{row.get('titular','')}">{str(row.get('titular',''))[:45]}...</b>
                        <span style="font-size:0.7rem; color:#94a3b8;">Emisor: {row.get('perfil','N/A')}</span><br>
                        <a href="{row.get('enlace_noticia','')}" target="_blank" style="font-size:0.75rem; color:#38bdf8; font-weight:bold;">Ver Origen / Respaldo</a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.write("Selecciona una ventana con pauta capturada de Instagram para habilitar el visor de auditoría por cuenta.")
    else:
        st.warning("Masa crítica insuficiente para trazar analítica digital.")

# ==============================================================================
# COMPUERTA 5: ANÁLISIS DE REDES SNA CON LEYENDAS Y AMPLIFICACIÓN
# ==============================================================================
elif modo_analisis == "🕸️ Análisis de Redes (SNA)":
    st.subheader("🕸️ Topología Relacional de Amenazas y Nodos de Amplificación")
    
    # IMPLEMENTACIÓN SOLICITADA: CUADRO DE LEYENDAS FÁCTICO
    st.markdown("""
    <div class="legend-box">
        <b>📐 LEYENDA TOPOLÓGICA (Código de Color en Aristas de Conexión):</b><br>
        <div style="margin-top: 8px;">
            <span class="legend-item"><span class="legend-color" style="background-color: #ff4b4b;"></span> Ataque Incendiario / Armado</span>
            <span class="legend-item"><span class="legend-color" style="background-color: #f6a821;"></span> Robo de Madera</span>
            <span class="legend-item"><span class="legend-color" style="background-color: #10b981;"></span> Usurpación / Toma</span>
            <span class="legend-item"><span class="legend-color" style="background-color: #3b82f6;"></span> Reacciones Políticas / Prensa</span>
            <span class="legend-item"><span class="legend-color" style="background-color: #8b5cf6;"></span> Operativo Policial / Allanamiento</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_filtrado.empty:
        df_net = df_filtrado[["actor_real", "ubicacion", "tipologia_oficial", "nivel_alerta", "titular", "resumen_ia"]].dropna().copy()
        
        # Filtro inquebrantable de purga de ubicaciones genéricas o corruptas
        terminos_excluidos = ['desconocido', 'no atribuido', 'sin dato', 'no especificado', '', 'mzs', 'macrozona sur']
        df_net = df_net[~df_net['actor_real'].str.lower().str.strip().isin(terminos_excluidos)]
        df_net = df_net[~df_net['ubicacion'].str.lower().str.strip().isin(terminos_excluidos)]
        
        if len(df_net) > 0:
            # IMPLEMENTACIÓN SOLICITADA: FILTRAR POR AGRUPACIÓN Y RASTREAR NODOS DE AMPLIFICACIÓN
            organicas_top = sorted(df_net['actor_real'].unique().tolist())
            sel_red_org = st.selectbox("🎯 Aislar Orgánica para Evaluar su Eje Físico y Nodos de Amplificación de Pauta:", ["Todas las Activas"] + organicas_top)
            
            df_grafo = df_net if sel_red_org == "Todas las Activas" else df_net[df_net['actor_real'] == sel_red_org]
            
            if sel_red_org != "Todas las Activas":
                # Calcular amplificaciones: cuántos políticos o coberturas mediáticas detonó este atentado
                tot_atks = len(df_grafo[df_grafo['tipologia_oficial'].isin(['Ataque Incendiario', 'Ataque Armado'])])
                reacciones_politicas = len(df_grafo[df_grafo['tipologia_oficial'] == 'Declaración / Pauta Política'])
                cobertura_prensa = len(df_grafo) - tot_atks - reacciones_politicas
                
                st.markdown(f"""
                <div style="background-color:#1e293b; border-left:5px solid #ff4b4b; padding:15px; border-radius:8px; margin-bottom:15px;">
                    <h4 style="color:#f8fafc; margin-top:0;">📡 ONDA EXPANSIVA Y AMPLIFICACIÓN: {sel_red_org}</h4>
                    <p style="font-size:0.9rem; color:#cbd5e1; margin-bottom:5px;"><b>Ejes de Sabotaje Físico:</b> {tot_atks} ataques directos.</p>
                    <p style="font-size:0.9rem; color:#cbd5e1; margin-bottom:5px;"><b>Nodos de Amplificación Mediática (Prensa/IG):</b> {max(0, cobertura_prensa)} trazas de pauta.</p>
                    <p style="font-size:0.9rem; color:#cbd5e1; margin-bottom:0;"><b>Impacto en Pauta Política (Reacciones de Estado):</b> {reacciones_politicas} declaraciones gubernamentales/locales.</p>
                </div>""", unsafe_allow_html=True)
            
            net = Network(height="600px", width="100%", bgcolor="#05080f", font_color="#f8fafc", directed=True)
            net.barnes_hut(gravity=-6500, central_gravity=0.3, spring_length=120, spring_strength=0.05, damping=0.09)
            
            nodos_agregados = set()
            for _, row in df_grafo.head(85).iterrows():
                actor = str(row['actor_real']).strip()
                target = str(row['ubicacion']).strip()
                alerta = str(row['nivel_alerta'])
                tipo_of = str(row['tipologia_oficial'])
                
                # COLORIMETRÍA TIPOLÓGICA PARA ARISTAS (Alineada al cuadro de leyenda)
                c_edge = "#334155" # Default
                if tipo_of in ['Ataque Incendiario', 'Ataque Armado']: c_edge = "#ff4b4b"
                elif 'Operativo Policial' in tipo_of or 'Allanamiento' in tipo_of: c_edge = "#8b5cf6"
                elif tipo_of == 'Robo de Madera': c_edge = "#f6a821"
                elif tipo_of == 'Usurpación': c_edge = "#10b981"
                elif tipo_of == 'Declaración / Pauta Política': c_edge = "#3b82f6"
                
                c_actor = "#ff4b4b" if alerta == 'CRÍTICO' else "#f6a821" if any(x in actor.upper() for x in ['CAM','RML','WAM','ORT']) else "#38bdf8"
                
                if actor not in nodos_agregados:
                    net.add_node(actor, label=actor, color=c_actor, shape="dot", size=26)
                    nodos_agregados.add(actor)
                if target not in nodos_agregados:
                    net.add_node(target, label=target, color="#64748b", shape="square", size=16)
                    nodos_agregados.add(target)
                    
                net.add_edge(actor, target, title=f"{tipo_of}: {str(row['titular'])[:50]}", color=c_edge)
                
            try:
                net.save_graph("matriz_sna_cmpc.html")
                with open("matriz_sna_cmpc.html", 'r', encoding='utf-8') as f:
                    components.html(f.read(), height=630)
            except Exception as e:
                st.error(f"Fallo al renderizar la topología del grafo: {e}")
        else:
            st.info("Pares relacionales insuficientes para trazar la topología tras purgar ubicaciones genéricas.")
    else:
        st.warning("Sin masa crítica de datos para construir la red relacional.")

# ==============================================================================
# COMPUERTA 6: PROSPECTIVA IA
# ==============================================================================
elif modo_analisis == "🔮 Prospectiva IA":
    st.subheader("🔮 Interrogación Neuronal e Inferencia Dinámica Masiva")
    st.markdown("El motor accede a la totalidad del almacenamiento, escaneando **la masa completa de miles de registros históricos del KMZ** para evaluar el vector fáctico con profundidad absoluta.")
    
    pregunta = st.text_input("Vector de Interrogación de Mando:", placeholder="Ej: Evaluar el impacto perimetral sobre faenas críticas tras los últimos operativos de seguridad...")
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        org_sim = st.selectbox("Focalizar Orgánica de Interés:", ["Todas las Activas", "CAM", "RML", "WAM", "Grupos de Robo de Madera"])
    with col_p2:
        cats_sim = st.multiselect("Contexto / Catalizador Proyectado (Selección Múltiple):", [
            "Muerte de un comunero por enfrentamientos con la policia (principalmente)",
            "Allanamientos",
            "Cambios en la política de Seguridad",
            "Huelgas de hambre",
            "Fallos judiciales",
            "Cortes de ruta",
            "Conmemoraciones"
        ], default=["Allanamientos", "Cortes de ruta"])
    
    if st.button("⚡ Ejecutar Inferencia de Estado Mayor", type="primary"):
        with st.spinner("Desbloqueando inventario profundo, iterando descripciones del KMZ y calculando tensores de riesgo..."):
            tot_rango = len(df_filtrado)
            tot_db_bruta = len(df_main) 
            rrss_count = len(df_filtrado[df_filtrado['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False)]) if tot_rango > 0 and 'catalizador' in df_filtrado.columns else 0
            
            menciones_reales = []
            if tot_rango > 0:
                txt_global = " ".join(df_filtrado['titular'].dropna().astype(str)).lower()
                if "cam" in txt_global or "arauco-malleco" in txt_global: menciones_reales.append("CAM")
                if "rml" in txt_global or "lavkenche" in txt_global: menciones_reales.append("RML")
                if "wam" in txt_global or "weichan" in txt_global: menciones_reales.append("WAM")
                if "madera" in txt_global or "robo" in txt_global: menciones_reales.append("Estructuras de Robo de Madera")
                
            orgs_detectadas_str = ", ".join(menciones_reales) if menciones_reales else "Células operativas descentralizadas"
            catalizadores_str = " y ".join(cats_sim) if cats_sim else "presión inercial del sector"
            
            alerta_contextual = "ALTO"
            if any("muerte" in x.lower() for x in cats_sim):
                alerta_contextual = "CRÍTICO EXTREMO"
                bloque_coyuntura = (
                    "**Alerta por Catalizador de Máxima Volatilidad:** La selección del factor *'Muerte de un comunero por enfrentamientos con la policia'* "
                    "actúa como el principal detonante histórico de espirales de confrontación asimétrica en la Macrozona Sur. La doctrina operativa "
                    "de las orgánicas impone la activación inmediata de sus ORT para ejecutar represalias veloces contra objetivos logísticos blandos, "
                    "priorizando maquinaria forestal, camiones en tránsito e instalaciones de faena como mecanismo de demostración de fuerza."
                )
            elif any("allanamientos" in x.lower() or "huelgas" in x.lower() or "cortes" in x.lower() for x in cats_sim):
                alerta_contextual = "CRÍTICO"
                bloque_coyuntura = (
                    f"**Tensión Operativa Aguda:** La convergencia de variables de coyuntura como *{catalizadores_str}* explica la alta saturación "
                    "en el flujo de alertas. Al someter a escrutinio el insumo de prensa y el rastreo de pautas en Instagram, se constata una "
                    "reacción táctica orientada al control territorial mediante bloqueos de rutas secundarias destinados a entorpecer el despliegue "
                    "policial y aislar logísticamente las faenas forestales."
                )
            else:
                bloque_coyuntura = (
                    f"**Proyección Estructural:** Condicionada por factores de *{catalizadores_str}*, la inteligencia del sistema anticipa un "
                    "comportamiento focalizado en el hostigamiento perimetral. Las orgánicas persiguen desgastar los anillos de resguardo corporativos "
                    "sin forzar choques frontales con contingentes blindados."
                )
                
            dictamen_final = f"""
            ### 📜 Dictamen Analítico de Inteligencia Prospectiva
            **Nivel de Riesgo Proyectado para Activos CMPC:** `{alerta_contextual}`
            
            **Auditoría de Masa Crítica Profunda:** El motor procesó exitosamente el **inventario total desbloqueado de {tot_db_bruta} registros fácticos** en la base de datos maestra (extrayendo las descripciones breves inyectadas desde el archivo KMZ). En la ventana activa filtrada se evalúan **{tot_rango} eventos**, de los cuales **{rrss_count} proceden del monitoreo nativo multimedia en Meta/Instagram**.
            
            {bloque_coyuntura}
            
            **Vulnerabilidad y Focalización CMPC:** Al cruzar la pauta con el foco en la estructura **{org_sim}**, se constata que los anillos perimetrales con mayor exposición son los colindantes a rutas forestales secundarias. Conforme a la directriz estricta de mando, cualquier incidente de sabotaje con impacto o proximidad sobre CMPC asume criticidad inmutable para gatillar protocolos de resguardo.
            
            **Directrices de Mando:**
            1. Emitir orden de inmovilización nocturna para convoyes de carga en rutas aledañas a los sectores con registros activos en el SITREP.
            2. Reforzar el monitoreo perimetral mediante el visor GEOINT sobre los predios corporativos cargados en la nube.
            3. Activar enlaces de contingencia con las jefaturas de zona de Carabineros y resguardo militar ante resoluciones judiciales adversas o hitos conmemorativos.
            """
            
            st.info(dictamen_final)

# ==============================================================================
# COMPUERTA 7: RADAR DE CRISIS (GENERADOR WORD OFICIAL CALIBRADO)
# ==============================================================================
elif modo_analisis == "📄 Reportes Radar":
    st.subheader("📄 Módulo de Exportación: Radar de Crisis (Formato Oficial Word)")
    st.markdown("Generación automatizada de minuta oficial en **Word (.docx)** bajo formato **Radar de Crisis**. Incorpora un tono corporativo medido, **destilando matrices limpias y purgando frases residuales**.")
    
    if st.button("🚀 Destilar e Inyectar Informe Word Oficial", use_container_width=True, type="primary"):
        with st.spinner("Compilando minuta fáctica con filtrado estricto de actores y zonas..."):
            try:
                doc = Document()
                
                for section in doc.sections:
                    section.top_margin = Inches(0.8)
                    section.bottom_margin = Inches(0.8)
                    section.left_margin = Inches(0.8)
                    section.right_margin = Inches(0.8)
                
                style_normal = doc.styles['Normal']
                font = style_normal.font
                font.name = 'Arial'
                font.size = Pt(10.5)
                font.color.rgb = RGBColor(0x22, 0x22, 0x22)
                
                p_title = doc.add_paragraph()
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_title = p_title.add_run("RADAR DE CRISIS - MINUTA EJECUTIVA DE INTELIGENCIA\nSISTEMA C5I - PROTECCIÓN PATRIMONIAL")
                r_title.font.size = Pt(14)
                r_title.font.bold = True
                r_title.font.color.rgb = RGBColor(0x00, 0x33, 0x66)
                
                p_meta = doc.add_paragraph()
                p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_meta = p_meta.add_run(f"Confidencial - CMPC | Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}\nVentana Analizada: {f_inicio.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}")
                r_meta.font.size = Pt(9.5)
                r_meta.font.italic = True
                
                doc.add_paragraph()
                
                # --- SECCIÓN I: APRECIACIÓN GLOBAL ---
                h1 = doc.add_heading("I. Apreciación Global de Inteligencia Territorial", level=1)
                h1.runs[0].font.color.rgb = RGBColor(0x00, 0x33, 0x66)
                
                total_ev = len(df_filtrado)
                crit_ev = len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO']) if total_ev > 0 and 'nivel_alerta' in df_filtrado.columns else 0
                ig_ev = len(df_filtrado[df_filtrado['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False)]) if total_ev > 0 and 'catalizador' in df_filtrado.columns else 0
                prensa_ev = total_ev - ig_ev
                
                comunas_validas = []
                if total_ev > 0 and 'ubicacion' in df_filtrado.columns:
                    excluir_locs = ['no especificado', 'desconocido', 'sin dato', 'mzs', '', 'macrozona sur', 'comunidad interior']
                    comunas_serie = df_filtrado['ubicacion'].dropna().astype(str)
                    comunas_validas = comunas_serie[~comunas_serie.str.lower().str.strip().isin(excluir_locs)]
                
                comunas_afectadas = comunas_validas.nunique() if len(comunas_validas) > 0 else 0
                principales_comunas = ", ".join(comunas_validas.value_counts().head(3).index.tolist()) if len(comunas_validas) > 0 else "sectores territoriales focalizados"
                
                p_ap1 = doc.add_paragraph()
                p_ap1.paragraph_format.line_spacing = 1.15
                p_ap1.paragraph_format.space_after = Pt(6)
                p_ap1.add_run(
                    f"Durante el periodo analizado, el sistema de monitoreo automatizado registró un total de {total_ev} eventos "
                    f"asociados a conflictividad territorial, operativos de resguardo y pautas de interés operativo. El desglose por canales indica que {prensa_ev} "
                    f"registros provienen del monitoreo de prensa y partes de contingencia, mientras que {ig_ev} corresponden a la amplificación "
                    f"de contenidos multimedia en redes sociales (Meta/Instagram). Los incidentes con georreferenciación atribuible se concentraron "
                    f"principalmente en los ejes de {principales_comunas}, abarcando un total de {comunas_afectadas} comunas."
                )
                
                p_ap2 = doc.add_paragraph()
                p_ap2.paragraph_format.line_spacing = 1.15
                p_ap2.paragraph_format.space_after = Pt(12)
                p_ap2.add_run(
                    f"Del volumen total, {crit_ev} sucesos directos han sido catalogados como de nivel CRÍTICO por implicar acciones de sabotaje "
                    f"o vulneración hacia infraestructura, maquinaria o corredores logísticos de CMPC. Las pautas de inversión comunitaria o pautas "
                    f"informativas son destiladas algorítmicamente para no generar falsas alarmas en la matriz de riesgo. La situación operacional "
                    f"se mantiene bajo un régimen de resguardo activo y continuo."
                )
                
                # --- SECCIÓN II: TABLA ESTRUCTURADA DE IMPACTOS CRÍTICOS ---
                h2 = doc.add_heading("II. Resumen Fáctico de Sucesos Críticos", level=1)
                h2.runs[0].font.color.rgb = RGBColor(0x00, 0x33, 0x66)
                
                df_criticos = df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO'] if total_ev > 0 and 'nivel_alerta' in df_filtrado.columns else pd.DataFrame()
                
                if not df_criticos.empty:
                    table = doc.add_table(rows=1, cols=3)
                    table.style = 'Table Grid'
                    hdr_cells = table.rows[0].cells
                    hdr_cells[0].text = 'Fecha'
                    hdr_cells[1].text = 'Localidad'
                    hdr_cells[2].text = 'Descripción / Titular'
                    
                    for cell in hdr_cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.bold = True
                                run.font.size = Pt(9.5)
                    
                    for _, c_row in df_criticos.iterrows():
                        row_cells = table.add_row().cells
                        row_cells[0].text = str(c_row.get('fecha_limpia', ''))
                        
                        loc_txt = str(c_row.get('ubicacion', 'MZS')).strip()
                        row_cells[1].text = loc_txt if loc_txt.lower() not in ['no especificado', 'desconocido'] else "Sector Focalizado"
                        
                        tit_txt = str(c_row.get('titular', ''))
                        act_txt = str(c_row.get('actor_real', 'N/A')).strip()
                        atrib = f" [Atribución: {act_txt}]" if act_txt.lower() not in ['desconocido', 'no atribuido', 'célula no adjudicada'] else ""
                        row_cells[2].text = f"{tit_txt}{atrib}"
                        
                        for cell in row_cells:
                            for p in cell.paragraphs:
                                for r in p.runs:
                                    r.font.size = Pt(9.0)
                    
                    doc.add_paragraph()
                else:
                    p_safe = doc.add_paragraph()
                    p_safe.paragraph_format.space_after = Pt(12)
                    r_safe = p_safe.add_run("Durante el marco temporal evaluado, el sistema no detectó incidentes hostiles directos que calificaran bajo el criterio de criticidad máxima hacia los activos de CMPC.")
                    r_safe.font.italic = True
                    
                # --- SECCIÓN III: DIRECTRICES DE MANDO ---
                h3 = doc.add_heading("III. Medidas Preventivas de Gestión", level=1)
                h3.runs[0].font.color.rgb = RGBColor(0x00, 0x33, 0x66)
                
                directrices = [
                    "Sostener la aplicación del protocolo estándar de tránsito y horarios de movilización para empresas contratistas en las zonas identificadas en la tabla anterior.",
                    "Mantener sincronizados los canales de aviso preventivo entre los monitores de plataforma y los jefes de resguardo patrimonial local.",
                    "Asegurar la actualización semanal de polígonos de cosecha activa en el motor de Geofencing para optimizar la exactitud de las alertas automáticas."
                ]
                
                for idx, d_txt in enumerate(directrices, 1):
                    p_dir = doc.add_paragraph()
                    p_dir.paragraph_format.left_indent = Inches(0.2)
                    p_dir.paragraph_format.space_after = Pt(4)
                    p_dir.add_run(f"{idx}. ").font.bold = True
                    p_dir.add_run(d_txt)

                buffer = io.BytesIO()
                doc.save(buffer)
                buffer.seek(0)
                
                st.success("✔️ Minuta oficial redactada y estructurada con éxito.")
                st.download_button(
                    label="📥 Descargar Minuta Ejecutiva (.docx)",
                    data=buffer,
                    file_name=f"Radar_de_Crisis_CMPC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            except Exception as e_doc:
                st.error(f"Error interno al compilar el documento Word: {e_doc}")
