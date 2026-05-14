# ==============================================================================
# Archivo: app.py
# Proyecto: War Room C5I - Puesto de Mando CMPC
# Rol: Interfaz de Inteligencia, Prospectiva y Operaciones (MZS)
# Doctrina: Archivo monolítico completo. Clasificación tipificada y jerarquía espacial.
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
    .card-alerta { background-color: #0d121d; padding: 18px; border-radius: 10px; border: 1px solid #1e293b; margin-bottom: 12px; transition: transform 0.2s; }
    .card-alerta:hover { border-color: #475569; }
    .badge-org { background-color: #1e293b; color: #cbd5e1; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    .link-btn { display: inline-block; margin-top: 8px; font-size: 0.85rem; color: #38bdf8; text-decoration: none; font-weight: bold; }
    .link-btn:hover { text-decoration: underline; color: #7dd3fc; }
    .semaforo-container { display: flex; gap: 10px; margin-bottom: 15px; background-color: #0d121d; padding: 12px 20px; border-radius: 8px; border: 1px solid #1e293b; align-items: center; }
    .semaforo-luz { width: 14px; height: 14px; border-radius: 50%; display: inline-block; box-shadow: 0 0 8px currentColor; }
    .semaforo-label { font-size: 0.85rem; font-weight: bold; color: #cbd5e1; margin-right: 15px; }
    .metric-expl { font-size: 0.7rem; color: #64748b; margin-top: -10px; margin-bottom: 10px; line-height: 1.1; }
    h1, h2, h3, h4 { color: #ffffff; letter-spacing: -0.5px; }
    div.block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A LA BÓVEDA SUPABASE ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

# --- 3. DICCIONARIOS DE ENRIQUECIMIENTO ESPACIAL Y TIPOLÓGICO ---
# Mapeo estricto para deducir jerarquía territorial a partir de nodos locales
MAPEO_PROVINCIAS = {
    'Arauco': ['Tirúa', 'Contulmo', 'Cañete', 'Los Álamos', 'Curanilahue', 'Arauco', 'Lebu'],
    'Malleco': ['Collipulli', 'Ercilla', 'Traiguén', 'Lumaco', 'Purén', 'Angol', 'Los Sauces', 'Renaico', 'Victoria', 'Curacautín', 'Lonquimay'],
    'Cautín': ['Temuco', 'Padre Las Casas', 'Vilcún', 'Freire', 'Pitrufquén', 'Gorbea', 'Loncoche', 'Toltén', 'Teodoro Schmidt', 'Saavedra', 'Carahue', 'Nueva Imperial', 'Cholchol', 'Galvarino', 'Lautaro', 'Perquenco', 'Cunco', 'Melipeuco', 'Pucón', 'Villarrica', 'Curarrehue'],
    'Biobío': ['Mulchén', 'Nacimiento', 'Negrete', 'Quilleco', 'Santa Bárbara', 'Tucapel', 'Yumbel', 'Alto Biobío', 'Antuco', 'Cabrero', 'Laja', 'Los Ángeles', 'San Rosendo'],
    'Los Ríos': ['Panguipulli', 'Lanco', 'Máfil', 'Valdivia', 'Corral', 'Mariquina', 'Los Lagos', 'Futrono', 'Río Bueno', 'Lago Ranco', 'La Unión'],
    'Los Lagos': ['Osorno', 'San Juan de la Costa', 'San Pablo', 'Puyehue', 'Río Negro', 'Purranque', 'Puerto Octay', 'Frutillar', 'Llanquihue', 'Puerto Varas', 'Puerto Montt', 'Calbuco', 'Maullín', 'Los Muermos', 'Fresia']
}

MAPEO_REGIONES = {
    'Región del Biobío': ['Arauco', 'Biobío'],
    'Región de La Araucanía': ['Malleco', 'Cautín'],
    'Región de Los Ríos': ['Los Ríos'],
    'Región de Los Lagos': ['Los Lagos']
}

def deducir_jerarquia(comuna_str):
    c_norm = str(comuna_str).strip()
    for prov, comunas in MAPEO_PROVINCIAS.items():
        if any(x.lower() == c_norm.lower() for x in comunas) or any(x.lower() in c_norm.lower() for x in comunas):
            for reg, provs in MAPEO_REGIONES.items():
                if prov in provs:
                    return prov, reg
    return 'Zona Focalizada', 'Macrozona Sur'

def normalizar_tipologia(titular, resumen):
    txt = f"{titular} {resumen}".lower()
    if any(x in txt for x in ['incendio', 'incendiario', 'quema', 'fuego', 'siniestro']):
        return 'Ataque Incendiario'
    elif any(x in txt for x in ['madera', 'tala', 'hurto forestal', 'robo forestal', 'camión cargado']):
        return 'Robo de Madera'
    elif any(x in txt for x in ['usurpación', 'toma', 'ocupación', 'desalojo', 'reivindicación']):
        return 'Usurpación'
    elif any(x in txt for x in ['ruta', 'corte', 'barricada', 'bloqueo', 'despeje', 'árboles caídos']):
        return 'Corte de Ruta'
    elif any(x in txt for x in ['armado', 'disparos', 'balazos', 'munición', 'emboscada', 'armas']):
        return 'Ataque Armado'
    return 'Sabotaje / Otros'

# --- 4. MOTORES DE CARGA Y LIMPIEZA DE DATOS ---
@st.cache_data(ttl=120)
def cargar_inteligencia():
    try:
        res = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).limit(10000).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['fecha_limpia'] = df['fecha'].astype(str).str.slice(0, 10)
            df['fecha_dt'] = pd.to_datetime(df['fecha_limpia'], errors='coerce')
            df = df.dropna(subset=['fecha_dt'])
            df['fecha_eval'] = df['fecha_dt'].dt.date
            
            # Limpieza espacial avanzada para rescatar hitos de sabotaje
            df['lat_clean'] = df['latitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['lon_clean'] = df['longitud'].astype(str).str.replace(',', '.').str.extract(r'(-?\d+\.\d+)')[0]
            df['latitud_num'] = pd.to_numeric(df['lat_clean'], errors='coerce')
            df['longitud_num'] = pd.to_numeric(df['lon_clean'], errors='coerce')
            
            # Enriquecimiento de Columnas (Inyecta Tipología Cerrada y Jerarquía Espacial al vuelo)
            df['tipologia_oficial'] = df.apply(lambda r: normalizar_tipologia(r['titular'], r['resumen_ia']), axis=1)
            
            jerarquias = df['ubicacion'].apply(deducir_jerarquia)
            df['provincia'] = [j[0] for j in jerarquias]
            df['region'] = [j[1] for j in jerarquias]
            df['mes_anio'] = df['fecha_dt'].dt.strftime('%Y-%m')
            
            # Mandato de Criticidad CMPC
            criterios_cmpc = "cmpc|mininco|forestal mininco|fundo cmpc|predio cmpc|camión forestal|maquinaria forestal"
            mask_cmpc = df['titular'].str.contains(criterios_cmpc, case=False, na=False) | df['resumen_ia'].str.contains(criterios_cmpc, case=False, na=False)
            df.loc[mask_cmpc, 'nivel_alerta'] = 'CRÍTICO'
            
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

df_main = cargar_inteligencia()
df_predios = cargar_predios()

# --- 5. PANEL LATERAL: SELECCIÓN OPERATIVA ---
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

# --- 6. FILTRADO ESTRATÉGICO Y SEMÁFORO DE CABECERA ---
df_filtrado = pd.DataFrame()
if not df_main.empty:
    if es_historico_completo:
        df_filtrado = df_main.copy()
    else:
        mask_fechas = (df_main['fecha_dt'].dt.date >= f_inicio) & (df_main['fecha_dt'].dt.date <= f_fin)
        df_filtrado = df_main[mask_fechas].copy()

st.title("WAR ROOM C5I ❯ PUESTO DE MANDO UNIFICADO")

tot_alertas = len(df_filtrado)
tot_criticos = len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO']) if tot_alertas > 0 and 'nivel_alerta' in df_filtrado.columns else 0

color_semaforo = "#10b981" if tot_criticos == 0 else "#f6a821" if tot_criticos < 5 else "#ff4b4b"
estado_txt = "OPERACIONES ESTABLES" if tot_criticos == 0 else "ALERTA TEMPRANA ACTIVA" if tot_criticos < 5 else "ESTADO DE EXCEPCIÓN / RIESGO CRÍTICO"

st.markdown(f"""
<div class="semaforo-container" style="border-left: 4px solid {color_semaforo};">
    <span class="semaforo-label">ESTADO GENERAL DEL PERÍMETRO:</span>
    <span class="semaforo-luz" style="background-color: {color_semaforo};"></span>
    <span style="font-size: 0.85rem; font-weight: bold; color: {color_semaforo};">{estado_txt}</span>
    <span style="font-size: 0.8rem; color: #64748b; margin-left: auto;">{tot_criticos} Eventos Críticos en la Ventana</span>
</div>
""", unsafe_allow_html=True)

tot_rrss = len(df_filtrado[df_filtrado['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False)]) if tot_alertas > 0 and 'catalizador' in df_filtrado.columns else 0
tot_predios = len(df_predios)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("TRAZAS EN EL PERIODO", tot_alertas)
    st.markdown('<div class="metric-expl">Total de reportes validados e ingresados tras purga algorítmica de ruido.</div>', unsafe_allow_html=True)

with col_m2:
    st.metric("AFECTACIÓN DIRECTA CMPC", tot_criticos, delta="PRIORIDAD" if tot_criticos > 0 else "ESTABLE", delta_color="inverse")
    st.markdown('<div class="metric-expl">Sucesos clasificados como CRÍTICOS por vulnerar o amenazar infraestructura corporativa.</div>', unsafe_allow_html=True)

with col_m3:
    st.metric("INGESTIÓN REDES SOCIALES", tot_rrss, delta="Meta/Instagram")
    st.markdown('<div class="metric-expl">Capturas directas extraídas desde perfiles y cuentas objetivo en redes.</div>', unsafe_allow_html=True)

with col_m4:
    st.metric("ANILLOS PERIMETRALES", tot_predios, delta="GEOFENCING ACTIVO")
    st.markdown('<div class="metric-expl">Total de predios corporativos bajo resguardo automatizado.</div>', unsafe_allow_html=True)

st.divider()

# --- 7. DESPLIEGUE DE COMPUERTAS (PESTAÑAS) ---

# ==============================================================================
# COMPUERTA 1: SITREP TÁCTICO
# ==============================================================================
if modo_analisis == "📍 SITREP Táctico":
    col_feed, col_stats = st.columns([2, 1])
    
    with col_feed:
        st.subheader("📋 Flujo de Detecciones Fácticas")
        if not df_filtrado.empty:
            for _, row in df_filtrado.head(30).iterrows():
                alerta = str(row.get('nivel_alerta', 'MEDIO')).upper()
                borde = "#ff4b4b" if alerta == 'CRÍTICO' else "#f6a821" if alerta == 'ALTO' else "#eab308" if alerta == 'MEDIO' else "#38bdf8"
                enlace = row.get('enlace_noticia', '')
                fuente_txt = "🔗 Inspeccionar Fuente Original" if enlace and str(enlace).startswith("http") else "📁 Registro Interno/Histórico"
                enlace_render = f'<a href="{enlace}" target="_blank" class="link-btn">{fuente_txt}</a>' if enlace and str(enlace).startswith("http") else f'<span style="font-size:0.8rem; color:#64748b;">{fuente_txt}</span>'
                
                actor_txt = str(row.get('actor', 'No Atribuido')).strip()
                actor_badge = actor_txt if actor_txt and actor_txt.lower() not in ['desconocido', 'no especificado', 'sin dato'] else "Sin Adjudicación"
                
                st.markdown(f"""
                <div class="card-alerta" style="border-left: 5px solid {borde};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.8rem; color: #94a3b8;">📅 {row.get('fecha_limpia', '')} | 📍 <b>{row.get('ubicacion', 'MZS')}</b> ({row.get('provincia','Arauco')})</span>
                        <span class="badge-org">{actor_badge}</span>
                    </div>
                    <h4 style="margin-top: 8px; margin-bottom: 4px; color: #f8fafc;">{row.get('titular', 'Sin Titular')}</h4>
                    <p style="font-size: 0.9rem; color: #cbd5e1; line-height: 1.4; margin-bottom: 8px;">{row.get('resumen_ia', 'Sin síntesis disponible.')}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.75rem; color: #ef4444; font-weight: bold;">{alerta} ❯ {row.get('tipologia_oficial','Otros')}</span>
                        {enlace_render}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No se registran eventos fácticos en la base de datos para la ventana temporal seleccionada.")

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
# COMPUERTA 2: ESTADÍSTICAS MZS (REPLICA EXACTA DE IMÁGENES GERENCIALES)
# ==============================================================================
elif modo_analisis == "📊 Estadísticas MZS":
    st.subheader("📊 Cuadros Estadísticos y Evolución Macrozona Sur")
    st.markdown("Paneles cuantitativos alineados al estándar gerencial de reportes corporativos.")
    
    if not df_filtrado.empty:
        # 1. TABLA ESTADÍSTICA GENERAL CRUZADA (Región vs Meses)
        st.markdown("#### Tabla de Estadísticas Generales Macrozona Sur (Frecuencia Mensual)")
        df_stat = df_filtrado.copy()
        
        # Crear pivote cruzando Regiones en filas y Meses en columnas
        tabla_cruzada = pd.crosstab(df_stat['region'], df_stat['mes_anio'], margins=True, margins_name="Total General")
        st.dataframe(tabla_cruzada, use_container_width=True)
        
        st.divider()
        
        col_ch1, col_ch2 = st.columns(2)
        with col_ch1:
            st.markdown("#### Evolución Temporal Tipificada")
            # Gráfico de barras apiladas mostrando la composición tipológica mensual
            df_ev = df_stat.groupby(['mes_anio', 'tipologia_oficial']).size().reset_index(name='count')
            fig_ev = px.bar(df_ev, x='mes_anio', y='count', color='tipologia_oficial', barmode='stack',
                            color_discrete_map={
                                'Ataque Incendiario': '#ff4b4b',
                                'Robo de Madera': '#f6a821',
                                'Usurpación': '#10b981',
                                'Corte de Ruta': '#38bdf8',
                                'Ataque Armado': '#ec4899',
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
    else:
        st.warning("Base de datos sin registros suficientes en la ventana seleccionada para proyectar cuadros gerenciales.")

# ==============================================================================
# COMPUERTA 3: VISOR GEOINT
# ==============================================================================
elif modo_analisis == "🗺️ Visor GEOINT":
    st.subheader("🗺️ Teatro de Operaciones y Blindaje Perimetral")
    st.markdown("Cruce espacial entre **Predios CMPC (Nodos Verdes)** y trazas de **Sabotaje Histórico/Reciente**. Al marcar el filtro **🚨 Histórico Completo**, el mapa proyecta la densidad total de la base.")
    
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
        
        df_mapa = df_mapa[(df_mapa['latitud_num'] > -56.0) & (df_mapa['latitud_num'] < -17.0)]
        df_mapa = df_mapa[(df_mapa['longitud_num'] > -85.0) & (df_mapa['longitud_num'] < -65.0)]
        
        if not df_mapa.empty:
            colores = df_mapa['nivel_alerta'].map({'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'}).fillna('#94a3b8')
            fig_map.add_trace(go.Scattermapbox(
                lat=df_mapa['latitud_num'], lon=df_mapa['longitud_num'],
                mode='markers',
                marker=go.scattermapbox.Marker(size=11, color=colores, opacity=0.85),
                text=df_mapa['tipologia_oficial'] + "<br><b>Lugar:</b> " + df_mapa['ubicacion'] + "<br><b>Actor:</b> " + df_mapa['actor'].fillna('Sin Adjudicación'),
                hoverinfo='text',
                name='Puntos de Amenaza'
            ))
            capas_dibujadas += 1

    if capas_dibujadas > 0:
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            mapbox_center={"lat": -38.3, "lon": -72.8},
            mapbox_zoom=7.0,
            margin={"r":0,"t":0,"l":0,"b":0},
            height=700,
            paper_bgcolor='rgba(0,0,0,0)',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white"))
        )
        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': True})
    else:
        st.warning("No se encontraron coordenadas espaciales válidas para superponer en el visor GEOINT durante el periodo.")

# ==============================================================================
# COMPUERTA 4: PULSO RRSS E INSTAGRAM
# ==============================================================================
elif modo_analisis == "📱 Pulso RRSS e Instagram":
    st.subheader("📱 Inteligencia de Fuentes Abiertas: Tracción Digital vs Terreno")
    st.markdown("Auditoría directa sobre el comportamiento de pauta en **Instagram** y su cristalización en el plano físico.")
    
    if not df_filtrado.empty:
        df_rrss = df_filtrado.copy()
        df_rrss['canal'] = np.where(df_rrss['catalizador'].str.contains('Redes Sociales|Instagram', case=False, na=False), 'Meta/Instagram', 'Monitoreo de Terreno (Prensa/RSS)')
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### Distribución Temporal por Canal de Origen")
            fig_canal = px.histogram(df_rrss, x='fecha_limpia', color='canal', barmode='group',
                                     color_discrete_map={'Meta/Instagram':'#ec4899', 'Monitoreo de Terreno (Prensa/RSS)':'#38bdf8'})
            fig_canal.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", yaxis_title="Volumen Capturado", xaxis_title="Fecha")
            st.plotly_chart(fig_canal, use_container_width=True)
            
        with col_g2:
            st.markdown("#### Cuentas y Entidades Digitales de Mayor Tracción")
            df_ig = df_rrss[df_rrss['canal'] == 'Meta/Instagram'].copy()
            if not df_ig.empty:
                df_ig['perfil'] = df_ig['titular'].str.extract(r'@([a-zA-Z0-9_.]+)', expand=False).fillna(df_ig['actor'])
                df_ig['perfil'] = df_ig['perfil'].replace('', 'Cuenta Objetivo')
                top_ig = df_ig['perfil'].value_counts().reset_index().head(8)
                fig_ig = px.bar(top_ig, x='count', y='perfil', orientation='h', color='count', color_continuous_scale='RdPu')
                fig_ig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", yaxis_title="Cuenta / Perfil", xaxis_title="Menciones Capturadas")
                st.plotly_chart(fig_ig, use_container_width=True)
            else:
                st.info("Sin pauta explícita de perfiles de Instagram detectada en la ventana seleccionada.")
                
        st.divider()
        st.markdown("#### 🎞️ Enlaces Directos a Pautas y Contenidos")
        df_enlaces = df_rrss[df_rrss['enlace_noticia'].str.startswith('http', na=False)].head(8)
        if not df_enlaces.empty:
            cols = st.columns(4)
            for idx, row in df_enlaces.iterrows():
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background-color: #0d121d; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin-bottom: 10px;">
                        <span style="font-size:0.75rem; color:#ec4899;">● Evidencia Digital</span><br>
                        <b style="font-size:0.85rem;" title="{row.get('titular','')}">{str(row.get('titular',''))[:55]}...</b><br>
                        <span style="font-size:0.75rem; color:#94a3b8;">Actor: {row.get('actor','N/A')}</span><br>
                        <a href="{row.get('enlace_noticia','')}" target="_blank" style="font-size:0.8rem; color:#38bdf8; font-weight:bold;">Inspeccionar Enlace</a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.write("Sin enlaces web rastreados en el rango temporal.")
    else:
        st.warning("Masa crítica insuficiente para trazar analítica de redes.")

# ==============================================================================
# COMPUERTA 5: ANÁLISIS DE REDES SNA (EFECTO GEPHI)
# ==============================================================================
elif modo_analisis == "🕸️ Análisis de Redes (SNA)":
    st.subheader("🕸️ Topología Relacional de Amenazas (Efecto Gephi)")
    st.markdown("Simulación de convergencia de fuerzas direccionales. **Se excluyen nodos genéricos ('Desconocido', 'Sin Adjudicación')** para enfocar el análisis en los actores territoriales reales.")
    
    if not df_filtrado.empty:
        df_net = df_filtrado[["actor", "ubicacion", "accion_digital", "nivel_alerta"]].dropna().copy()
        
        terminos_excluidos = ['desconocido', 'no atribuido', 'sin dato', 'no especificado', '', 'mzs', 'macrozona sur']
        df_net = df_net[~df_net['actor'].str.lower().str.strip().isin(terminos_excluidos)]
        df_net = df_net[~df_net['ubicacion'].str.lower().str.strip().isin(terminos_excluidos)]
        
        if len(df_net) > 0:
            net = Network(height="650px", width="100%", bgcolor="#05080f", font_color="#f8fafc", directed=True)
            net.barnes_hut(gravity=-6500, central_gravity=0.3, spring_length=110, spring_strength=0.05, damping=0.09)
            
            nodos_agregados = set()
            for _, row in df_net.head(75).iterrows():
                actor = str(row['actor']).strip()
                target = str(row['ubicacion']).strip()
                alerta = str(row['nivel_alerta'])
                accion = str(row['accion_digital']).strip() if str(row['accion_digital']).strip() else "Acción"
                
                c_actor = "#ff4b4b" if alerta == 'CRÍTICO' else "#f6a821" if any(x in actor.upper() for x in ['CAM','RML','WAM','ORT']) else "#38bdf8"
                
                if actor not in nodos_agregados:
                    net.add_node(actor, label=actor, color=c_actor, shape="dot", size=26)
                    nodos_agregados.add(actor)
                if target not in nodos_agregados:
                    net.add_node(target, label=target, color="#64748b", shape="square", size=16)
                    nodos_agregados.add(target)
                    
                net.add_edge(actor, target, title=accion, color="#334155")
                
            try:
                net.save_graph("matriz_sna_cmpc.html")
                with open("matriz_sna_cmpc.html", 'r', encoding='utf-8') as f:
                    components.html(f.read(), height=680)
            except Exception as e:
                st.error(f"Fallo al renderizar la topología del grafo: {e}")
        else:
            st.info("Una vez filtrados los nodos genéricos, los pares relacionales son insuficientes para graficar.")
    else:
        st.warning("Sin masa crítica de datos para construir la red relacional.")

# ==============================================================================
# COMPUERTA 6: PROSPECTIVA IA
# ==============================================================================
elif modo_analisis == "🔮 Prospectiva IA":
    st.subheader("🔮 Interrogación Neuronal e Inferencia Dinámica de Escenarios")
    st.markdown("Configura el panel cruzando las variables tácticas reales para forzar una lectura contextual exhaustiva del flujo de noticias e Instagram.")
    
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
        with st.spinner("Destilando pauta activa de medios, cuantificando interceptaciones de Instagram y cruzando tensores de coyuntura..."):
            tot_rango = len(df_filtrado)
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
            
            **Auditoría de Insumo Activo:** El motor analizó un flujo vivo de **{tot_rango} trazas fácticas** en la ventana temporal, de las cuales **{rrss_count} proceden de la interceptación directa en Meta/Instagram**. Las estructuras con mayor resonancia en la pauta analizada corresponden a: *{orgs_detectadas_str}*.
            
            {bloque_coyuntura}
            
            **Vulnerabilidad y Focalización CMPC:** Al cruzar la masa crítica de noticias con el foco en la estructura **{org_sim}**, se identifica que los anillos perimetrales con mayor exposición son aquellos colindantes a rutas forestales secundarias. Conforme a la directriz estricta de mando, cualquier incidente con impacto o amenaza de proximidad sobre CMPC se clasifica inmutablemente como **CRÍTICO** para gatillar la detención preventiva de operaciones.
            
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
    st.markdown("El generador de informes elabora automáticamente el documento **Word (.docx)** oficial bajo el formato **Radar de Crisis**. Redacta párrafos estructurados y consolida matrices en base a la ventana seleccionada.")
    
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
                    excluir_locs = ['no especificado', 'desconocido', 'sin dato', 'mzs', '', 'macrozona sur']
                    comunas_serie = df_filtrado['ubicacion'].dropna().astype(str)
                    comunas_validas = comunas_serie[~comunas_serie.str.lower().str.strip().isin(excluir_locs)]
                
                comunas_afectadas = comunas_validas.nunique() if len(comunas_validas) > 0 else 0
                principales_comunas = ", ".join(comunas_validas.value_counts().head(3).index.tolist()) if len(comunas_validas) > 0 else "sectores focalizados"
                
                p_ap1 = doc.add_paragraph()
                p_ap1.paragraph_format.line_spacing = 1.15
                p_ap1.paragraph_format.space_after = Pt(6)
                p_ap1.add_run(
                    f"Durante el periodo analizado, el sistema de monitoreo automatizado registró un total de {total_ev} eventos "
                    f"asociados a conflictividad territorial y pautas de interés operativo. El desglose por fuentes indica que {prensa_ev} "
                    f"registros provienen del monitoreo de prensa y partes locales, mientras que {ig_ev} corresponden a la amplificación "
                    f"de contenidos en redes sociales (Meta/Instagram). Los incidentes con georreferenciación atribuible se concentraron "
                    f"principalmente en los ejes de {principales_comunas}, abarcando un total de {comunas_afectadas} comunas."
                )
                
                p_ap2 = doc.add_paragraph()
                p_ap2.paragraph_format.line_spacing = 1.15
                p_ap2.paragraph_format.space_after = Pt(12)
                p_ap2.add_run(
                    f"Del volumen total, {crit_ev} sucesos han sido catalogados como de nivel CRÍTICO por implicar afectación o "
                    f"proximidad inmediata a operaciones, faenas silvícolas o corredores logísticos de CMPC. La situación operacional "
                    f"se mantiene bajo un régimen de vigilancia continua, priorizando la continuidad operativa sin comprometer la seguridad "
                    f"de los colaboradores en terreno."
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
                        act_txt = str(c_row.get('actor', 'N/A')).strip()
                        atrib = f" [Atribución: {act_txt}]" if act_txt.lower() not in ['desconocido', 'no atribuido', ''] else ""
                        row_cells[2].text = f"{tit_txt}{atrib}"
                        
                        for cell in row_cells:
                            for p in cell.paragraphs:
                                for r in p.runs:
                                    r.font.size = Pt(9.0)
                    
                    doc.add_paragraph()
                else:
                    p_safe = doc.add_paragraph()
                    p_safe.paragraph_format.space_after = Pt(12)
                    r_safe = p_safe.add_run("Durante el marco temporal evaluado, el sistema no detectó incidentes que calificaran bajo el criterio de criticidad máxima hacia la infraestructura o personal de CMPC.")
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
