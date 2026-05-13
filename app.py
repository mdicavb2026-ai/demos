# ==============================================================================
# Archivo: app.py | Versión: 11.0 (Edición Geofencing CMPC)
# Proyecto: War Room C5I - Puesto de Mando Unificado
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

# --- 1. CONFIGURACIÓN UI (WAR ROOM DARK C5I) ---
st.set_page_config(page_title="C5I WAR ROOM | CMPC", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #05080f; color: #e0e6ed; }
    .stMetric { background-color: #0d121d; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; }
    .card { background-color: #0d121d; padding: 15px; border-radius: 8px; border: 1px solid #1e293b; margin-bottom: 10px; border-left: 5px solid; }
    h1, h2, h3 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- 2. CONEXIÓN SUPABASE ---
URL_SUPABASE = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY_SUPABASE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL_SUPABASE, API_KEY_SUPABASE)

# --- 3. MOTORES DE CARGA (NOTICIAS Y PREDIOS) ---
@st.cache_data(ttl=300)
def cargar_noticias():
    try:
        res = supabase.table("inteligencia_tactica").select("*").order("fecha", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce')
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=600)
def cargar_predios():
    try:
        res = supabase.table("predios_cmpc").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
            df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        return df
    except: return pd.DataFrame()

# Carga inicial
df_main = cargar_noticias()
df_predios = cargar_predios()

# --- 4. PANEL LATERAL ---
st.sidebar.markdown("<h3 style='color: #ff4b4b; text-align: center;'>● CMPC C5I</h3>", unsafe_allow_html=True)
modo_analisis = st.sidebar.radio("COMPUERTA DE MANDO:", 
    ["📍 SITREP Actual", "🗺️ Visor GEOINT (Mapa)", "🕸️ Análisis SNA", "🔮 Prospectiva IA", "📄 Reportes Radar"])

st.sidebar.divider()
f_inicio = st.sidebar.date_input("Desde:", datetime.now() - timedelta(days=30))
f_fin = st.sidebar.date_input("Hasta:", datetime.now())

# --- 5. FILTRADO Y MÉTRICAS ---
df_filtrado = pd.DataFrame()
if not df_main.empty and 'fecha_dt' in df_main.columns:
    df_filtrado = df_main[(df_main['fecha_dt'].dt.date >= f_inicio) & (df_main['fecha_dt'].dt.date <= f_fin)].copy()

st.title("WAR ROOM C5I ❯ Puesto de Mando")

# Métricas rápidas
m1, m2, m3, m4 = st.columns(4)
m1.metric("ALERTAS TOTALES", len(df_filtrado))
m2.metric("PREDIOS PROTEGIDOS", len(df_predios))
m3.metric("RIESGO CRÍTICO", len(df_filtrado[df_filtrado['nivel_alerta'] == 'CRÍTICO']) if not df_filtrado.empty else 0)
m4.metric("SISTEMA", "ACTIVO", delta="GEOINT")

# --- 6. VISUALIZACIONES ---

if modo_analisis == "📍 SITREP Actual":
    st.subheader("📋 Feed de Inteligencia en Tiempo Real")
    if df_filtrado.empty:
        st.warning("⚠️ Sin datos detectados. Verifica las políticas RLS en Supabase.")
    else:
        for _, row in df_filtrado.head(15).iterrows():
            color = "#ff4b4b" if row['nivel_alerta'] == 'CRÍTICO' else "#f6a821"
            st.markdown(f"""<div class="card" style="border-left-color: {color};">
                <small>{row['fecha']} | {row['ubicacion']}</small><br>
                <b>{row['titular']}</b><br>
                <p style='font-size: 0.9rem;'>{row['resumen_ia']}</p>
                </div>""", unsafe_allow_html=True)

elif modo_analisis == "🗺️ Visor GEOINT (Mapa)":
    st.subheader("🗺️ Inteligencia Geoespacial Cruzada")
    
    # Crear Mapa Base
    fig = go.Figure()

    # Capa 1: Predios CMPC (Círculos Verdes)
    if not df_predios.empty:
        fig.add_trace(go.Scattermapbox(
            lat=df_predios['latitud'], lon=df_predios['longitud'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=8, color='rgb(0, 255, 100)', opacity=0.6),
            text=df_predios['nombre_predio'],
            name='Predios CMPC'
        ))

    # Capa 2: Incidentes Recientes (Círculos Rojos/Naranjas)
    if not df_filtrado.empty:
        df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud']).copy()
        df_mapa['latitud'] = pd.to_numeric(df_mapa['latitud'], errors='coerce')
        df_mapa['longitud'] = pd.to_numeric(df_mapa['longitud'], errors='coerce')
        
        fig.add_trace(go.Scattermapbox(
            lat=df_mapa['latitud'], lon=df_mapa['longitud'],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=12, 
                color=df_mapa['nivel_alerta'].map({'CRÍTICO':'red', 'ALTO':'orange', 'MEDIO':'yellow'}),
                opacity=0.9
            ),
            text=df_mapa['titular'],
            name='Incidentes'
        ))

    fig.update_layout(
        mapbox_style="carto-darkmatter",
        mapbox_center={"lat": -38.5, "lon": -72.5},
        mapbox_zoom=7,
        margin={"r":0,"t":0,"l":0,"b":0},
        height=700,
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.5)")
    )
    st.plotly_chart(fig, use_container_width=True)

elif modo_analisis == "🕸️ Análisis SNA":
    st.info("Visualización de redes relacionales basada en datos fácticos.")
    # (Lógica de Pyvis similar a la anterior)

elif modo_analisis == "🔮 Prospectiva IA":
    st.subheader("🔮 Inferencia Neuronal sobre Predios")
    # (Lógica de consulta a Ollama o dictámenes pre-guardados)

elif modo_analisis == "📄 Reportes Radar":
    st.subheader("📄 Generador de Radar de Crisis")
    # (Lógica de descarga de Word)
