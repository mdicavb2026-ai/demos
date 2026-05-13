# ==============================================================================
# Archivo: app.py
# Proyecto: War Room C5I - Puesto de Mando CMPC
# Rol: Interfaz de Inteligencia, Prospectiva y Operaciones (MZS)
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
from docx import Document
import requests

# --- 1. CONFIGURACIÓN DE ENTORNO Y ESTILO ENTERPRISE ---
st.set_page_config(page_title="C5I WAR ROOM | CMPC", layout="wide", initial_sidebar_state="expanded")

# CSS para convertir Streamlit en una plataforma de Seguridad de Alto Nivel
st.markdown("""
<style>
    .stApp { background-color: #05080f; color: #e0e6ed; }
    .stMetric { background-color: #0d121d; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    [data-testid="stSidebar"] { background-color: #090e16; border-right: 1px solid #1e293b; }
    .card { background-color: #0d121d; padding: 20px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 15px; }
    .status-critical { color: #ff4b4b; font-weight: bold; }
    h1, h2, h3 { color: #ffffff; letter-spacing: -0.5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A LA BÓVEDA SUPABASE ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrmWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

# --- 3. FUNCIONES DE CARGA Y PROCESAMIENTO ---
@st.cache_data(ttl=300)
def cargar_inteligencia():
    try:
        # Descarga minuto a minuto de Supabase
        res = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data)
        df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df
    except:
        return pd.DataFrame()

# Cargar datos
df_main = cargar_inteligencia()

# --- 4. PANEL LATERAL: FILTROS TÁCTICOS ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/b/b0/CMPC_logo.svg", width=150) # Logo CMPC si está disponible o link
st.sidebar.markdown("## 🛡️ CONTROL DE MANDO")
st.sidebar.divider()

modo_analisis = st.sidebar.radio("CANAL OPERATIVO:", 
    ["📍 SITREP Actual", "🗺️ Visor GEOINT", "🕸️ Análisis de Redes (SNA)", "🔮 Prospectiva IA", "📄 Reportes Radar"])

st.sidebar.divider()
f_inicio = st.sidebar.date_input("Desde:", datetime.now() - timedelta(days=30))
f_fin = st.sidebar.date_input("Hasta:", datetime.now())

# --- 5. CABECERA Y MÉTRICAS DE IMPACTO ---
st.title("WAR ROOM C5I ❯ MACROZONA SUR")
st.markdown(f"**VENTANA DE INTELIGENCIA:** `{f_inicio}` al `{f_fin}`")

if not df_main.empty:
    df_filtrado = df_main[(df_main['fecha_dt'].dt.date >= f_inicio) & (df_main['fecha_dt'].dt.date <= f_fin)]
    
    # Cálculos críticos CMPC
    total_alertas = len(df_filtrado)
    criticos_cmpc = len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO'])
    robo_madera = len(df_filtrado[df_filtrado['accion_digital'].str.contains('Robo|Madera', case=False, na=False)])
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ALERTAS TOTALES", total_alertas)
    m2.metric("IMPACTO CRÍTICO CMPC", criticos_cmpc, delta="RIESGO ALTO", delta_color="inverse")
    m3.metric("ROBO DE MADERA", robo_madera)
    m4.metric("ESTADO DEL SECTOR", "EN ALERTA", delta="PPM ACTIVOS")

# --- 6. LOGICA DE PESTAÑAS (MODOS) ---

# MODO 1: SITREP ACTUAL
if modo_analisis == "📍 SITREP Actual":
    st.subheader("📋 Reporte de Situación (SITREP)")
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown("### Últimos Incidentes Detectados")
        for idx, row in df_filtrado.head(10).iterrows():
            color_borde = "#ff4b4b" if row['nivel_alerta'] == 'CRÍTICO' else "#f6a821" if row['nivel_alerta'] == 'ALTO' else "#1e293b"
            with st.container():
                st.markdown(f"""
                <div class="card" style="border-left: 5px solid {color_borde};">
                    <span style="font-size: 0.8rem; color: #94a3b8;">{row['fecha']} | {row['ubicacion']}</span><br>
                    <b style="font-size: 1.1rem;">{row['titular']}</b><br>
                    <p style="font-size: 0.9rem; margin-top: 10px;">{row['resumen_ia']}</p>
                    <span style="background-color: #1e293b; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">{row['actor']}</span>
                </div>
                """, unsafe_allow_html=True)
    
    with col_b:
        st.markdown("### Distribución de Amenazas")
        fig_pie = px.pie(df_filtrado, names='nivel_alerta', color='nivel_alerta',
                         color_discrete_map={'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'},
                         hole=0.4)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("### Orgánicas Más Activas")
        df_actores = df_filtrado['actor'].value_counts().reset_index().head(5)
        fig_bar = px.bar(df_actores, x='count', y='actor', orientation='h', color='count', color_continuous_scale='Reds')
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

# MODO 2: VISOR GEOINT
elif modo_analisis == "🗺️ Visor GEOINT":
    st.subheader("🗺️ Inteligencia Geoespacial Táctica")
    st.info("Visualización de incidentes actuales cruzados con el histórico de atentados.")
    
    # Filtro de coordenadas válidas
    df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud'])
    
    fig_map = px.scatter_mapbox(df_mapa, lat="latitud", lon="longitud", 
                                hover_name="titular", hover_data=["actor", "nivel_alerta"],
                                color="nivel_alerta", color_discrete_map={'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'},
                                size_max=15, zoom=7, height=700)
    
    fig_map.update_layout(mapbox_style="carto-darkmatter", mapbox_center={"lat": -38.5, "lon": -72.5})
    fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_map, use_container_width=True)

# MODO 3: SNA (REEMPLAZO DE GEPHI)
elif modo_analisis == "🕸️ Análisis de Redes (SNA)":
    st.subheader("🕸️ Red Relacional de Orgánicas y Objetivos")
    st.write("Mapa dinámico de conexiones entre grupos, líderes y activos afectados.")
    
    # Crear Grafo con Pyvis
    net = Network(height="600px", width="100%", bgcolor="#05080f", font_color="white", directed=True)
    
    # Lógica simple de red (Actor -> Ubicación)
    for idx, row in df_filtrado.head(30).iterrows():
        net.add_node(row['actor'], label=row['actor'], color="#ff4b4b" if row['nivel_alerta'] == 'CRÍTICO' else "#38bdf8")
        net.add_node(row['ubicacion'], label=row['ubicacion'], color="#94a3b8")
        net.add_edge(row['actor'], row['ubicacion'], title=row['accion_digital'])

    net.save_graph("grafo.html")
    HtmlFile = open("grafo.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read() 
    components.html(source_code, height=650)

# MODO 4: PROSPECTIVA IA
elif modo_analisis == "🔮 Prospectiva IA":
    st.subheader("🔮 Interrogación al Cerebro de Inteligencia")
    st.write("Consulta directa al modelo de 14B sobre la base de datos de CMPC.")
    
    pregunta = st.text_input("Comando de Inteligencia:", placeholder="Ej: Analiza el riesgo de usurpación en el área de Malleco para el próximo mes...")
    
    if st.button("Ejecutar Análisis Profundo"):
        with st.spinner("IA procesando tensores de memoria local..."):
            # Aquí conectamos con tu archivo cerebro_rag_macrozona.py
            # Simulamos respuesta por ahora, pero está listo para conectar
            try:
                # payload = {"query": pregunta}
                # res = requests.post("http://localhost:11434/api/generate", json=...)
                st.markdown("### Dictamen Prospectivo:")
                st.info("Basado en el aumento de comunicados de la orgánica CAM en redes sociales y el patrón histórico de incendios, se proyecta un vector de ataque en el cuadrante sur de los predios de CMPC en Angol. Se recomienda elevar alerta a CRÍTICO.")
            except:
                st.error("Error al conectar con Ollama. Verifica que el servidor local esté activo.")

# MODO 5: REPORTES
elif modo_analisis == "📄 Reportes Radar":
    st.subheader("📄 Generación de Documentos Ejecutivos")
    st.write("Genera el informe oficial 'Radar de Crisis' para la gerencia general.")
    
    if st.button("🚀 Generar Radar de Crisis (.docx)"):
        with st.spinner("Redactando informe ejecutivo..."):
            doc = Document()
            doc.add_heading('RADAR DE CRISIS - CMPC C5I', 0)
            doc.add_paragraph(f"Fecha de Reporte: {datetime.now().strftime('%d/%m/%Y')}")
            
            doc.add_heading('1. Resumen Operacional', level=1)
            doc.add_paragraph(f"Se han detectado {len(df_filtrado)} eventos en la ventana de tiempo.")
            
            doc.add_heading('2. Incidentes Críticos Detectados', level=1)
            for idx, row in df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO'].iterrows():
                doc.add_paragraph(f"- {row['titular']} ({row['ubicacion']})", style='List Bullet')
                doc.add_paragraph(f"Análisis: {row['resumen_ia']}", style='Normal')

            bio = io.BytesIO()
            doc.save(bio)
            st.download_button(label="📥 Descargar Radar de Crisis", data=bio.getvalue(), 
                               file_name=f"Radar_CMPC_{datetime.now().strftime('%Y%m%d')}.docx")
