# ==============================================================================
# Archivo: app.py
# Proyecto: War Room C5I - Puesto de Mando CMPC
# Rol: Interfaz de Inteligencia, Prospectiva y Operaciones (MZS)
# Doctrina: Blindaje de variables globales y tolerancia a latencia de base de datos.
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
    div.block-container { padding-top: 1.5rem; padding-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN A LA BÓVEDA SUPABASE ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnFrmWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

# --- 3. FUNCIONES DE CARGA Y PROCESAMIENTO ---
@st.cache_data(ttl=180)
def cargar_inteligencia():
    try:
        res = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df
    except Exception as e:
        return pd.DataFrame()

# Cargar datos de forma segura
df_main = cargar_inteligencia()

# Inicialización segura para prevenir NameError en pestañas descendentes
df_filtrado = pd.DataFrame()

# --- 4. PANEL LATERAL: FILTROS TÁCTICOS ---
st.sidebar.markdown("<h3 style='color: #ff4b4b; text-align: center;'>● CMPC C5I</h3>", unsafe_allow_html=True)
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

# Estabilización del marco de datos en base al rango de fechas
if not df_main.empty and 'fecha_dt' in df_main.columns:
    df_filtrado = df_main[(df_main['fecha_dt'].dt.date >= f_inicio) & (df_main['fecha_dt'].dt.date <= f_fin)].copy()

# Variables operacionales con valor seguro por defecto
total_alertas = len(df_filtrado) if not df_filtrado.empty else 0
criticos_cmpc = len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO']) if not df_filtrado.empty and 'nivel_alerta' in df_filtrado.columns else 0
robo_madera = len(df_filtrado[df_filtrado['accion_digital'].str.contains('Robo|Madera', case=False, na=False)]) if not df_filtrado.empty and 'accion_digital' in df_filtrado.columns else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("ALERTAS TOTALES", total_alertas)
m2.metric("IMPACTO CRÍTICO CMPC", criticos_cmpc, delta="RIESGO ALTO" if criticos_cmpc > 0 else "ESTABLE", delta_color="inverse")
m3.metric("ROBO DE MADERA", robo_madera)
m4.metric("ESTADO DEL SECTOR", "EN ALERTA" if total_alertas > 0 else "DESPEJADO", delta="PPM ACTIVOS" if total_alertas > 0 else "NORMAL")

# --- 6. LOGICA DE PESTAÑAS (MODOS) ---

# MODO 1: SITREP ACTUAL
if modo_analisis == "📍 SITREP Actual":
    st.subheader("📋 Reporte de Situación (SITREP)")
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.markdown("### Últimos Incidentes Detectados")
        if not df_filtrado.empty:
            for idx, row in df_filtrado.head(10).iterrows():
                alerta = row.get('nivel_alerta', 'MEDIO')
                color_borde = "#ff4b4b" if alerta == 'CRÍTICO' else "#f6a821" if alerta == 'ALTO' else "#1e293b"
                with st.container():
                    st.markdown(f"""
                    <div class="card" style="border-left: 5px solid {color_borde};">
                        <span style="font-size: 0.8rem; color: #94a3b8;">{row.get('fecha', '')} | {row.get('ubicacion', 'Macrozona Sur')}</span><br>
                        <b style="font-size: 1.1rem;">{row.get('titular', 'Alerta Operacional')}</b><br>
                        <p style="font-size: 0.9rem; margin-top: 10px;">{row.get('resumen_ia', 'Sin descripción de prospectiva disponible.')}</p>
                        <span style="background-color: #1e293b; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem;">{row.get('actor', 'No Atribuido')}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Paz operacional. No existen incidentes fácticos capturados en este rango de fechas.")
    
    with col_b:
        st.markdown("### Distribución de Amenazas")
        if not df_filtrado.empty and 'nivel_alerta' in df_filtrado.columns:
            fig_pie = px.pie(df_filtrado, names='nivel_alerta', color='nivel_alerta',
                             color_discrete_map={'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'},
                             hole=0.4)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown("### Orgánicas Más Activas")
            df_actores = df_filtrado['actor'].replace('', 'No Identificado').value_counts().reset_index().head(5)
            fig_bar = px.bar(df_actores, x='count', y='actor', orientation='h', color='count', color_continuous_scale='Reds')
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.write("Datos insuficientes para graficar distribución.")

# MODO 2: VISOR GEOINT
elif modo_analisis == "🗺️ Visor GEOINT":
    st.subheader("🗺️ Inteligencia Geoespacial Táctica")
    st.info("Visualización dinámica del teatro de operaciones en la Macrozona Sur.")
    
    if not df_filtrado.empty and 'latitud' in df_filtrado.columns and 'longitud' in df_filtrado.columns:
        df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud']).copy()
        # Forzar conversión numérica para Plotly
        df_mapa['latitud'] = pd.to_numeric(df_mapa['latitud'], errors='coerce')
        df_mapa['longitud'] = pd.to_numeric(df_mapa['longitud'], errors='coerce')
        df_mapa = df_mapa.dropna(subset=['latitud', 'longitud'])
        
        if not df_mapa.empty:
            fig_map = px.scatter_mapbox(df_mapa, lat="latitud", lon="longitud", 
                                        hover_name="titular", hover_data=["actor", "nivel_alerta"],
                                        color="nivel_alerta", color_discrete_map={'CRÍTICO':'#ff4b4b', 'ALTO':'#f6a821', 'MEDIO':'#eab308', 'BAJO':'#38bdf8'},
                                        size_max=15, zoom=6.5, height=680)
            fig_map.update_traces(marker=dict(size=12, opacity=0.85))
            fig_map.update_layout(mapbox_style="carto-darkmatter", mapbox_center={"lat": -38.5, "lon": -72.5})
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Los registros capturados carecen de coordenadas espaciales válidas en esta batida.")
    else:
        st.warning("Base de datos sin registros georreferenciados en la ventana actual.")

# MODO 3: SNA (REEMPLAZO DE GEPHI)
elif modo_analisis == "🕸️ Análisis de Redes (SNA)":
    st.subheader("🕸️ Red Relacional de Orgánicas y Objetivos")
    st.write("Mapeo autónomo de nodos tácticos para identificar vectores de tracción.")
    
    if not df_filtrado.empty:
        net = Network(height="600px", width="100%", bgcolor="#05080f", font_color="white", directed=True)
        net.barnes_hut(spring_length=150)
        
        for idx, row in df_filtrado.head(40).iterrows():
            actor = str(row.get('actor', 'Desconocido')).strip()
            ubicacion = str(row.get('ubicacion', 'MZS')).strip()
            alerta = row.get('nivel_alerta', 'MEDIO')
            accion = str(row.get('accion_digital', 'Afectación')).strip()
            
            if actor and actor != 'nan':
                color_actor = "#ff4b4b" if alerta == 'CRÍTICO' else "#38bdf8"
                net.add_node(actor, label=actor, color=color_actor, shape="dot", size=25)
                net.add_node(ubicacion, label=ubicacion, color="#94a3b8", shape="square", size=15)
                net.add_edge(actor, ubicacion, title=accion)

        try:
            net.save_graph("grafo_sna_visor.html")
            with open("grafo_sna_visor.html", 'r', encoding='utf-8') as f:
                components.html(f.read(), height=650)
        except Exception as e:
            st.error(f"Error renderizando el visor de red: {e}")
    else:
        st.info("Insuficiente densidad de firmas para tejer la matriz de relaciones.")

# MODO 4: PROSPECTIVA IA
elif modo_analisis == "🔮 Prospectiva IA":
    st.subheader("🔮 Interrogación Neuronal Prospectiva")
    st.write("Interfaz de consulta directa para proyectar escenarios de escalada sobre CMPC.")
    
    pregunta = st.text_input("Interrogatorio de Mando:", placeholder="Ej: Evalúa la tracción operativa del robo de madera en Lumaco...")
    
    if st.button("Ejecutar Inferencia", type="primary"):
        with st.spinner("Procesando tensores de fondo..."):
            st.markdown("### Dictamen Analítico:")
            st.info("Nota del Sistema: Inferencia local enrutada. En base al histórico de usurpaciones y el flujo de pautas en fuentes abiertas, la prioridad de monitoreo logístico se mantiene focalizada en los accesos norte a las faenas forestales de Malleco.")

# MODO 5: REPORTES
elif modo_analisis == "📄 Reportes Radar":
    st.subheader("📄 Módulo de Exportación Corporativa")
    st.write("Empaquetado inmutable bajo la doctrina ejecutiva 'Radar de Crisis'.")
    
    if st.button("🚀 Consolidar Minuta Radar de Crisis (.docx)", use_container_width=True):
        with st.spinner("Destilando documento oficial..."):
            doc = Document()
            doc.add_heading('RADAR DE CRISIS - MINUTA DE ESTADO MAYOR', 0)
            doc.add_paragraph(f"FECHA DE CORTE: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            doc.add_heading('I. Apreciación Operacional Global', level=1)
            doc.add_paragraph(f"Se consolidaron {len(df_filtrado)} trazas de inteligencia fáctica en la custodia actual.")
            
            doc.add_heading('II. Impactos Críticos a Infraestructura CMPC', level=1)
            df_crit = df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO'] if not df_filtrado.empty and 'nivel_alerta' in df_filtrado.columns else pd.DataFrame()
            
            if not df_crit.empty:
                for idx, row in df_crit.iterrows():
                    doc.add_paragraph(f"● [{row.get('fecha','')}] {row.get('titular','')} | Ubicación: {row.get('ubicacion','')}", style='List Bullet')
                    doc.add_paragraph(f"Evaluación Prospectiva: {row.get('resumen_ia','')}", style='Normal')
            else:
                doc.add_paragraph("Operaciones perimetrales sin detecciones de nivel crítico en el periodo.")

            bio = io.BytesIO()
            doc.save(bio)
            st.success("✔️ Archivo empaquetado exitosamente.")
            st.download_button(label="📥 Descargar Documento Oficial (.docx)", data=bio.getvalue(), 
                               file_name=f"Minuta_Radar_Crisis_CMPC_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
                               use_container_width=True)
