import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re
from datetime import datetime, timedelta
import io
from docx import Document
from docx.shared import Inches
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN UI ---
st.set_page_config(page_title="C5I WAR ROOM", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0b111e; color: #ffffff; }
    .card { background-color: #151b2b; padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .seccion-titulo { font-size: 14px; font-weight: bold; color: #4fc3f7; border-bottom: 1px solid #293145; padding-bottom: 5px; margin: 15px 0; }
    .desc-grafico { font-size: 11px; color: #8892b0; font-style: italic; margin-bottom: 10px; }
    .bigrama-tag { background: #1e2638; color: #4fc3f7; padding: 3px 10px; border-radius: 15px; cursor: pointer; font-size: 12px; border: 1px solid #4fc3f7; }
</style>
""", unsafe_allow_html=True)

URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

@st.cache_data(ttl=300)
def get_data():
    client = create_client(URL, API_KEY)
    data = client.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(data.data)
    df['fecha_dt'] = pd.to_datetime(df['fecha']).dt.tz_localize(None)
    return df.sort_values('fecha_dt', ascending=False)

@st.cache_data
def get_layers():
    fundos = pd.read_excel('FUNDOS_COMPLEJIDADyRIESGO_20250409.xlsx').dropna(subset=['F_LATITUD'])
    with open('mapa2020-2025.kml', 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    kml_data = []
    for p in soup.find_all('Placemark'):
        coords = p.find('coordinates')
        if coords:
            lon, lat, _ = coords.text.strip().split(',')
            kml_data.append({'lat': float(lat), 'lon': float(lon), 'name': p.find('name').text})
    return fundos, pd.DataFrame(kml_data)

df = get_data()
df_fundos, df_kml = get_layers()

# --- FILTROS DE CABECERA ---
st.sidebar.title("Comando C5I")
periodo = st.sidebar.selectbox("Periodo", ["7 días", "30 días", "Todo"])
dias = {"7 días": 7, "30 días": 30, "Todo": 3650}[periodo]
df_f = df[df['fecha_dt'] >= (datetime.now() - timedelta(days=dias))]

# BIGRAMAS ARRIBA
st.markdown("### 🏷️ Trending OSINT (Filtro por Concepto)")
tags = Counter(df_f['palabra_clave'].dropna()).most_common(10)
cols_tags = st.columns(len(tags))
concepto_filtro = None
for i, (tag, count) in enumerate(tags):
    if cols_tags[i].button(f"#{tag}"): concepto_filtro = tag

if concepto_filtro: df_f = df_f[df_f['palabra_clave'] == concepto_filtro]

t1, t2, t3 = st.tabs(["🎯 TÁCTICO & GEOINT", "📊 PROSPECTIVA", "📄 RADAR DE CRISIS"])

with t1:
    c1, c2 = st.columns([3, 7])
    with c1:
        st.markdown('<div class="seccion-titulo">MINUTO A MINUTO (CRÍTICO)</div>', unsafe_allow_html=True)
        for _, r in df_f[df_f['nivel_alerta'] == 'CRÍTICO'].head(5).iterrows():
            st.markdown(f"""<div class="card" style="border-color:#ff1744">
                <small>{r['fecha_dt'].strftime('%d/%m/%Y %H:%M')} | {r['actor']}</small><br>
                <b>{r['titular']}</b><br>
                <div style="color:#ffd54f; font-size:11px">IA: {r['resumen_ia']}</div>
            </div>""", unsafe_allow_html=True)
    
    with c2:
        st.markdown('<div class="seccion-titulo">GEOINT: MAPA DE FUSIÓN MULTICAPA</div>', unsafe_allow_html=True)
        fig = go.Figure()
        # Capa Histórica KML
        fig.add_trace(go.Scattermapbox(lat=df_kml['lat'], lon=df_kml['lon'], mode='markers', marker=dict(size=4, color='#8892b0', opacity=0.4), name='Histórico 2020-25'))
        # Capa Predios CMPC
        fig.add_trace(go.Scattermapbox(lat=df_fundos['F_LATITUD'], lon=df_fundos['F_LONGITUD'], mode='markers', marker=dict(size=5, color='#4caf50', opacity=0.6), text=df_fundos['NOM_FUNDO'], name='Activos CMPC'))
        # Capa OSINT Viva
        col_map = {'CRÍTICO': '#ff1744', 'ALTO': '#ff9100', 'MEDIO': '#29b6f6'}
        for n, c in col_map.items():
            df_n = df_f[df_f['nivel_alerta'] == n]
            fig.add_trace(go.Scattermapbox(lat=df_n['latitud'], lon=df_n['longitud'], mode='markers', marker=dict(size=12, color=c), text=df_n['titular'], name=n))
        
        fig.update_layout(mapbox_style="carto-darkmatter", margin=dict(l=0,r=0,t=0,b=0), height=600, mapbox=dict(center=dict(lat=-38, lon=-73), zoom=6.5))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

with t2:
    st.markdown("### MATRIZ DE PROSPECTIVA")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="seccion-titulo">1. ACELERACIÓN DE VIOLENCIA</div>', unsafe_allow_html=True)
        st.markdown('<p class="desc-grafico">Mide la frecuencia de ataques cinéticos confirmados. Una curva empinada indica una fase de ofensiva territorial activa.</p>', unsafe_allow_html=True)
        df_v = df_f.groupby(df_f['fecha_dt'].dt.date).size().reset_index(name='cuenta')
        st.plotly_chart(px.line(df_v, x='fecha_dt', y='cuenta', template="plotly_dark", color_discrete_sequence=['#ff1744']), use_container_width=True)
        
        st.markdown('<div class="seccion-titulo">2. VECTORES DE PRESIÓN (TÁCTICA)</div>', unsafe_allow_html=True)
        st.markdown('<p class="desc-grafico">Desglose de la naturaleza del incidente. Permite distinguir entre sabotaje material y agitación política.</p>', unsafe_allow_html=True)
        df_p = df_f['accion_digital'].value_counts().reset_index()
        df_p = df_p[df_p['accion_digital'] != "1"] # Limpieza de basura
        st.plotly_chart(px.pie(df_p, values='count', names='accion_digital', hole=0.4, template="plotly_dark"), use_container_width=True)

    with g2:
        st.markdown('<div class="seccion-titulo">3. EXPOSICIÓN DE ACTIVOS CMPC</div>', unsafe_allow_html=True)
        st.markdown('<p class="desc-grafico">Radar de vulnerabilidad. Compara el impacto en maquinaria, predios y personal respecto al hito histórico.</p>', unsafe_allow_html=True)
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=[8, 6, 4, 7, 5], theta=['Predios', 'Maquinaria', 'Rutas', 'Personal', 'Plantas'], fill='toself', name='Exposición Actual', line_color='#ff1744'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=False)), template="plotly_dark")
        st.plotly_chart(fig_r, use_container_width=True)

        st.markdown('<div class="seccion-titulo">4. SOCIOGRAMA DE VÍNCULOS</div>', unsafe_allow_html=True)
        st.markdown('<p class="desc-grafico">Relación entre Orgánicas y Territorios. El tamaño del nodo indica la agresividad del grupo en la zona.</p>', unsafe_allow_html=True)
        df_s = df_f[df_f['actor'] != 'Desconocido'].groupby(['actor', 'ubicacion']).size().reset_index(name='n')
        st.plotly_chart(px.scatter(df_s, x='ubicacion', y='actor', size='n', color='actor', template="plotly_dark"), use_container_width=True)

with t3:
    st.markdown("### 📥 GENERAR RADAR DE CRISIS (.DOCX)")
    if st.button("Descargar Informe Ejecutivo"):
        doc = Document()
        doc.add_heading('RADAR DE CRISIS - INFORME EJECUTIVO C5I', 0)
        doc.add_paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')} | Clasificación: CONFIDENCIAL")
        doc.add_heading('1. SITUATIONAL AWARENESS', level=1)
        doc.add_paragraph("El análisis OSINT detecta una aceleración cinemática en la Macrozona Sur, con foco específico en activos de CMPC. La reciente actividad de la RML confirma un vector de hostilidad alto.")
        doc.add_heading('2. MATRIZ DE INCIDENTES CRÍTICOS', level=1)
        for _, r in df_f[df_f['nivel_alerta'] == 'CRÍTICO'].head(5).iterrows():
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{r['fecha_dt'].strftime('%d/%m/%Y')}: {r['titular']}").bold = True
            doc.add_paragraph(f"Análisis IA: {r['resumen_ia']}", style='Normal')
        
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button("Descargar Archivo", bio.getvalue(), "Radar_Crisis.docx")
