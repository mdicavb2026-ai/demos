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
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup

# --- 1. CONFIGURACIÓN UI (WAR ROOM DARK ESTILO ORIGINAL) ---
st.set_page_config(page_title="War Room CMPC - C5I Predictivo", layout="wide", initial_sidebar_state="expanded")

if 'filtro_bigrama' not in st.session_state: st.session_state.filtro_bigrama = None

st.markdown("""
<style>
    .stApp { background-color: #0b1120; color: #94a3b8; font-family: 'Segoe UI', Roboto, sans-serif; }
    .card { background-color: #0f172a; padding: 15px; border-radius: 0.4rem; border: 1px solid #1e293b; margin-bottom: 10px; border-left: 4px solid; transition: all 0.2s; }
    .card:hover { border-color: #60a5fa; background-color: #1e293b !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .seccion-titulo { font-size: 0.8rem; font-weight: bold; letter-spacing: 0.05em; color: #e2e8f0; border-bottom: 2px solid #334155; padding-bottom: 4px; margin-bottom: 10px; text-transform: uppercase; }
    .desc-grafico { font-size: 0.65rem; color: #94a3b8; margin-bottom: 10px; display: block; line-height: 1.3; }
    .metric-box { background: #1e293b; border-radius: 6px; padding: 12px; border-top: 4px solid #3b82f6; text-align: center; }
    .metric-title { font-size: 0.65rem; color: #cbd5e1; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 1.5rem; font-weight: 900; margin-top: 4px; color: #ffffff;}
    .card-summary { font-size: 0.75rem; color: #cbd5e1; font-style: normal; margin-top: 6px; display: block; background-color: #0b1120; padding: 5px 7px; border-radius: 4px; border-left: 2px solid #3b82f6; }
</style>
""", unsafe_allow_html=True)

# --- 2. CREDENCIALES SUPABASE ---
URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"
supabase: Client = create_client(URL, API_KEY)

def sanitizar_texto(val):
    if pd.isna(val) or val is None: return ""
    texto = str(val).replace('\\', '/').replace('"', "'").replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    return ''.join(c for c in texto if c.isprintable()).strip()

# --- 3. MOTORES DE DATOS ---
@st.cache_data(ttl=300)
def get_osint_data():
    try:
        data = supabase.table("inteligencia_tactica").select("*").execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce').dt.tz_localize(None)
            df = df.dropna(subset=['fecha_dt']).sort_values('fecha_dt', ascending=False)
            for col in ['actor', 'titular', 'resumen_ia', 'ubicacion', 'palabra_clave']:
                if col in df.columns: df[col] = df[col].apply(sanitizar_texto)
            df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
            df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
        return df
    except: return pd.DataFrame()

@st.cache_data
def get_layers_data():
    try:
        fundos = pd.read_excel('FUNDOS_COMPLEJIDADyRIESGO_20250409.xlsx')
        fundos['F_LATITUD'] = pd.to_numeric(fundos['F_LATITUD'], errors='coerce')
        fundos['F_LONGITUD'] = pd.to_numeric(fundos['F_LONGITUD'], errors='coerce')
        fundos = fundos.dropna(subset=['F_LATITUD', 'F_LONGITUD'])
        if 'NOM_FUNDO' in fundos.columns: fundos['NOM_FUNDO'] = fundos['NOM_FUNDO'].apply(sanitizar_texto)
    except: fundos = pd.DataFrame()

    kml_data = []
    try:
        with open('mapa2020-2025.kml', 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')
        for p in soup.find_all('Placemark'):
            name = sanitizar_texto(p.find('name').text if p.find('name') else 'Incidente')
            desc_text = p.find('description').text if p.find('description') else ""
            fecha_hist = "Sin Fecha"
            match_fecha = re.search(r'(\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2})', desc_text)
            if match_fecha: fecha_hist = match_fecha.group(1)
            desc_limpia = sanitizar_texto(re.sub(r'<[^>]+>', ' ', desc_text))[:100] + "..."
            coords = p.find('coordinates')
            if coords:
                lon, lat, _ = coords.text.strip().split(',')
                kml_data.append({'lat': float(lat), 'lon': float(lon), 'name': name, 'fecha': fecha_hist, 'desc': desc_limpia})
    except: pass
    return fundos, pd.DataFrame(kml_data)

df_osint = get_osint_data()
df_fundos, df_kml = get_layers_data()

# --- 4. PANEL LATERAL (FILTROS MANUALES) ---
st.sidebar.markdown('<span style="color:#ef4444; font-size:12px; font-weight:bold;">● WAR ROOM CMPC</span>', unsafe_allow_html=True)
st.sidebar.markdown("### ⚙️ CONTROLES")

# Filtro de Fechas Manual (Basado en el diseño original)
rango_rapido = st.sidebar.selectbox("Filtro Rápido:", ["Histórico Global", "Últimos 6 Meses", "Últimos 30 Días", "Última Semana"])
dias_restar = {"Última Semana": 7, "Últimos 30 Días": 30, "Últimos 6 Meses": 180, "Histórico Global": 3650}[rango_rapido]

st.sidebar.markdown("**Búsqueda Manual:**")
f_inicio = st.sidebar.date_input("Desde:", value=datetime.now() - timedelta(days=dias_restar))
f_fin = st.sidebar.date_input("Hasta:", value=datetime.now())

if not df_osint.empty:
    df_f = df_osint[(df_osint['fecha_dt'].dt.date >= f_inicio) & (df_osint['fecha_dt'].dt.date <= f_fin)]
else:
    df_f = pd.DataFrame()

if st.sidebar.button("🗑️ Limpiar Base de Datos (Reset)"):
    if not df_osint.empty:
        try:
            ids = df_osint['id'].tolist()
            for r_id in ids: supabase.table("inteligencia_tactica").delete().eq("id", r_id).execute()
            st.sidebar.success("Base limpiada. Recargue la página.")
            st.cache_data.clear()
        except: pass

# --- 5. CABECERA: TRENDING KEYWORDS INTERACTIVAS ---
st.markdown('<div class="seccion-titulo">Trending Keywords (Filtro)</div>', unsafe_allow_html=True)
if not df_f.empty:
    titulares_unidos = " ".join(df_f['palabra_clave'].dropna().tolist() + df_f['titular'].dropna().tolist()).lower()
    palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', titulares_unidos)
    ruido = ['para', 'como', 'sobre', 'entre', 'desde', 'hasta', 'este', 'esta', 'pero', 'sean', 'tras']
    palabras_utiles = [p for p in palabras if p not in ruido]
    conteo_bigramas = Counter([f"{palabras_utiles[i]} {palabras_utiles[i+1]}" for i in range(len(palabras_utiles)-1)]).most_common(8)
    
    cols = st.columns(len(conteo_bigramas))
    for i, (frase, _) in enumerate(conteo_bigramas):
        if cols[i].button(f"#{frase.title()}", key=f"btn_{frase}"):
            st.session_state.filtro_bigrama = None if st.session_state.filtro_bigrama == frase else frase

    if st.session_state.filtro_bigrama:
        st.warning(f"🔍 Filtrando por: **{st.session_state.filtro_bigrama.upper()}**.")
        df_f = df_f[df_f['titular'].str.lower().str.contains(st.session_state.filtro_bigrama, na=False) | df_f['palabra_clave'].str.lower().str.contains(st.session_state.filtro_bigrama, na=False)]

# --- 6. TABS TÁCTICOS ---
t1, t2, t3 = st.tabs(["📡 Táctico & Mapa", "🔮 Prospectiva OSINT", "📄 Informe Ejecutivo"])

# === PESTAÑA 1: MAPA Y FEED ===
with t1:
    capas = st.multiselect("Capas del Mapa:", ["🚨 OSINT (Vivo)", "📜 Histórico (2020-25)", "🏭 CMPC (Predios)"], default=["🚨 OSINT (Vivo)", "🏭 CMPC (Predios)"])
    c1, c2 = st.columns([7, 3])
    
    with c1:
        fig_map = go.Figure()
        if "📜 Histórico (2020-25)" in capas and not df_kml.empty:
            fig_map.add_trace(go.Scattermapbox(lat=df_kml['lat'], lon=df_kml['lon'], mode='markers', marker=dict(size=5, color='#ffb300', opacity=0.4), text=df_kml['fecha']+"<br>"+df_kml['name']+"<br>"+df_kml['desc'], hoverinfo='text', name='Histórico'))
        if "🏭 CMPC (Predios)" in capas and not df_fundos.empty:
            fig_map.add_trace(go.Scattermapbox(lat=df_fundos['F_LATITUD'], lon=df_fundos['F_LONGITUD'], mode='markers', marker=dict(size=6, color='#10b981', opacity=0.7), text="🌲 "+df_fundos['NOM_FUNDO'], hoverinfo='text', name='CMPC'))
        if "🚨 OSINT (Vivo)" in capas and not df_f.empty:
            df_v = df_f.dropna(subset=['latitud'])
            col_map = {'CRÍTICO': '#ef4444', 'ALTO': '#f97316', 'MEDIO': '#3b82f6'}
            for n, c in col_map.items():
                df_n = df_v[df_v['nivel_alerta'] == n]
                if not df_n.empty:
                    fig_map.add_trace(go.Scattermapbox(lat=df_n['latitud'], lon=df_n['longitud'], mode='markers', marker=dict(size=12, color=c), text=df_n['fecha_dt'].dt.strftime('%d/%m/%Y')+" | "+df_n['actor']+"<br>"+df_n['titular'], hoverinfo='text', name=n))

        fig_map.update_layout(mapbox_style="carto-darkmatter", margin=dict(l=0, r=0, t=0, b=0), height=600, mapbox=dict(center=dict(lat=-38.2, lon=-72.6), zoom=6.5), showlegend=False)
        st.plotly_chart(fig_map, use_container_width=True)

    with c2:
        st.markdown('<div class="seccion-titulo">Últimos Atentados CMPC</div>', unsafe_allow_html=True)
        if not df_f.empty:
            for _, r in df_f[df_f['nivel_alerta'] == 'CRÍTICO'].head(5).iterrows():
                st.markdown(f"""
                <div class="card" style="border-color:#ef4444">
                    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                        <span style="font-size:0.65rem; color:#ef4444; font-weight:bold;">CRÍTICO | {r['actor']}</span>
                        <span style="font-size:0.65rem; color:#94a3b8;">{r['fecha_dt'].strftime('%d/%m/%Y')}</span>
                    </div>
                    <span style="font-size:0.75rem; color:#e2e8f0; font-weight:500;">{r['titular']}</span>
                    <div class="card-summary">💡 <strong>PROSPECTIVA:</strong> {r['resumen_ia']}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Operación Normal. Sin alertas.")

# === PESTAÑA 2: PROSPECTIVA Y KPIs ===
with t2:
    st.markdown('<div class="seccion-titulo" style="color:#38bdf8;">INTELIGENCIA PROSPECTIVA OSINT</div>', unsafe_allow_html=True)
    
    # LÓGICA DE KPIs EXACTA A TU CÓDIGO JS
    atq_predio = len(df_f[df_f['titular'].str.contains('predio|fundo|forestal', case=False, na=False)]) if not df_f.empty else 0
    atq_per = len(df_f[df_f['titular'].str.contains('trabajador|guardia|carabinero', case=False, na=False)]) if not df_f.empty else 0
    atq_rutas = len(df_f[df_f['titular'].str.contains('ruta|camión', case=False, na=False)]) if not df_f.empty else 0
    atq_plan = len(df_f[df_f['titular'].str.contains('planta|aserradero', case=False, na=False)]) if not df_f.empty else 0
    total = len(df_f) if not df_f.empty and len(df_f) > 0 else 1
    
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='metric-box' style='border-top-color:#10b981;'><div class='metric-title'>🌲 VECTOR PREDIAL</div><div class='metric-value' style='color:#34d399;'>{round((atq_predio/total)*100)}%</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-box' style='border-top-color:#be123c;'><div class='metric-title'>👷 VECTOR CONTRA PERSONAL</div><div class='metric-value' style='color:#fb7185;'>{round((atq_per/total)*100)}%</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-box' style='border-top-color:#a855f7;'><div class='metric-title'>🚛 VECTOR RUTAS/MAQUINARIA</div><div class='metric-value' style='color:#c084fc;'>{round((atq_rutas/total)*100)}%</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-box' style='border-top-color:#f59e0b;'><div class='metric-title'>🏭 VECTOR PLANTAS</div><div class='metric-value' style='color:#fbbf24;'>{round((atq_plan/total)*100)}%</div></div>", unsafe_allow_html=True)

    st.write("")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown('<div class="seccion-titulo">► ACELERACIÓN DE VIOLENCIA VS OSINT</div>', unsafe_allow_html=True)
        st.markdown('<div class="desc-grafico">Nota: En Plotly, haga click en "Expand" (esquina superior derecha) para ver en pantalla completa.</div>', unsafe_allow_html=True)
        if not df_f.empty:
            df_v = df_f.groupby(df_f['fecha_dt'].dt.date).size().reset_index(name='Incidentes')
            fig_1 = px.line(df_v, x='fecha_dt', y='Incidentes', template="plotly_dark", color_discrete_sequence=['#ef4444'])
            fig_1.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
            st.plotly_chart(fig_1, use_container_width=True)

        st.markdown('<div class="seccion-titulo">► SOCIOGRAMA TÁCTICO</div>', unsafe_allow_html=True)
        if not df_f.empty:
            df_s = df_f[df_f['actor'] != 'Desconocido'].groupby(['actor', 'ubicacion']).size().reset_index(name='Ataques')
            if not df_s.empty:
                fig_soc = px.scatter(df_s, x='ubicacion', y='actor', size='Ataques', color='actor', template="plotly_dark")
                fig_soc.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
                st.plotly_chart(fig_soc, use_container_width=True)

    with g2:
        st.markdown('<div class="seccion-titulo">► DISTRIBUCIÓN CRIMINAL POR MACROZONA</div>', unsafe_allow_html=True)
        if not df_f.empty:
            conteo_zona = df_f['ubicacion'].value_counts().reset_index().head(6)
            conteo_zona.columns = ['Territorio', 'Incidentes']
            fig_3 = px.bar(conteo_zona, x='Territorio', y='Incidentes', color='Territorio', template="plotly_dark")
            fig_3.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, showlegend=False)
            st.plotly_chart(fig_3, use_container_width=True)

        st.markdown('<div class="seccion-titulo">► MATRIZ EXPOSICIÓN DE ACTIVOS CMPC</div>', unsafe_allow_html=True)
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=[(atq_predio/total)*100, (atq_rutas/total)*100, 30, (atq_per/total)*100, (atq_plan/total)*100], theta=['Predios', 'Maquinaria', 'Rutas', 'Personal', 'Plantas'], fill='toself', name='Dinámica', line_color='#06b6d4'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=False)), template="plotly_dark", height=300, margin=dict(l=40, r=40, t=10, b=0))
        st.plotly_chart(fig_r, use_container_width=True)

# === PESTAÑA 3: INFORME GERENCIAL BASADO EN DATOS ===
with t3:
    st.markdown('<div class="seccion-titulo">Generador de Documentos Corporativos</div>', unsafe_allow_html=True)
    st.info("Este módulo replica la estructura exacta del 'Radar de Crisis', compilando la matriz de incidentes y actores directamente desde la base de datos local para máxima seguridad y velocidad.")
    
    if st.button("📄 GENERAR INFORME .DOCX"):
        doc = Document()
        doc.add_heading('REPORTE DE INTELIGENCIA TÁCTICA - C5I', 0)
        
        p_info = doc.add_paragraph()
        p_info.add_run(f"FECHA DE EMISIÓN: ").bold = True
        p_info.add_run(f"{datetime.now().strftime('%d/%m/%Y')} | ")
        p_info.add_run(f"VENTANA OPERATIVA: ").bold = True
        p_info.add_run(f"{f_inicio.strftime('%d/%m/%Y')} al {f_fin.strftime('%d/%m/%Y')}")
        
        # 1. Mapeo
        doc.add_heading('1. Mapeo de Amenaza', level=1)
        if not df_f.empty:
            vol_cmpc = len(df_f[df_f['nivel_alerta'] == 'CRÍTICO'])
            actores = df_f[df_f['actor'] != 'Desconocido']['actor'].value_counts().head(3).index.tolist()
            doc.add_paragraph(f"• Volumen de inteligencia procesado: {len(df_f)} reportes OSINT.", style='List Bullet')
            doc.add_paragraph(f"• Ataques dirigidos a CMPC: {vol_cmpc} incidentes críticos.", style='List Bullet')
            doc.add_paragraph(f"• Orgánicas con mayor despliegue operativo: {', '.join(actores) if actores else 'No detectadas'}.", style='List Bullet')
        else:
            doc.add_paragraph("No hay datos en el rango seleccionado.")
            
        # 2. Eventos CMPC
        doc.add_heading('2. Eventos Críticos (Afectación CMPC)', level=1)
        if not df_f.empty:
            df_crit = df_f[df_f['nivel_alerta'] == 'CRÍTICO']
            if not df_crit.empty:
                for _, r in df_crit.iterrows():
                    p = doc.add_paragraph(style='List Bullet')
                    p.add_run(f"{r['fecha_dt'].strftime('%d/%m/%Y')} | {r['titular']}\n").bold = True
                    p.add_run(f"Análisis Táctico: {r['resumen_ia']}").italic = True
            else: doc.add_paragraph("Sin eventos directos a CMPC.")
        
        # 3. Contexto General
        doc.add_heading('3. Panorama Táctico Macrozona (Contexto General)', level=1)
        if not df_f.empty:
            df_alto = df_f[df_f['nivel_alerta'] == 'ALTO'].head(5)
            if not df_alto.empty:
                for _, r in df_alto.iterrows():
                    p = doc.add_paragraph(style='List Bullet')
                    p.add_run(f"{r['fecha_dt'].strftime('%d/%m/%Y')} | {r['titular']}\n").bold = True
                    p.add_run(f"Análisis Táctico: {r['resumen_ia']}").italic = True
            else: doc.add_paragraph("Sin actividad táctica exógena relevante.")

        bio = io.BytesIO()
        doc.save(bio)
        st.download_button(label="📥 DESCARGAR INFORME .DOCX", data=bio.getvalue(), file_name=f'Reporte_Inteligencia_C5I_{datetime.now().strftime("%Y%m%d")}.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
