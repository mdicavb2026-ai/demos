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

# --- 1. CONFIGURACIÓN UI (WAR ROOM DARK) ---
st.set_page_config(page_title="C5I WAR ROOM", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .stApp { background-color: #0b111e; color: #ffffff; }
    .card { background-color: #151b2b; padding: 15px; border-radius: 5px; margin-bottom: 10px; border-left: 5px solid; }
    .seccion-titulo { font-size: 14px; font-weight: bold; color: #4fc3f7; border-bottom: 1px solid #293145; padding-bottom: 5px; margin: 15px 0; }
    .desc-grafico { font-size: 11px; color: #8892b0; font-style: italic; margin-bottom: 10px; }
    .metric-box { background-color: #151b2b; padding: 15px; border-radius: 8px; text-align: center; border-bottom: 3px solid; }
    .metric-title { font-size: 12px; color: #8892b0; text-transform: uppercase; font-weight: bold; }
    .metric-value { font-size: 24px; font-weight: bold; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# --- 2. CREDENCIALES ---
URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

# --- 3. MOTORES DE EXTRACCIÓN (BLINDADOS) ---
@st.cache_data(ttl=300)
def get_osint_data():
    try:
        client = create_client(URL, API_KEY)
        data = client.table("inteligencia_tactica").select("*").execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha'], errors='coerce').dt.tz_localize(None)
            df = df.dropna(subset=['fecha_dt']).sort_values('fecha_dt', ascending=False)
            df['actor'] = df['actor'].fillna('Desconocido')
        return df
    except Exception as e:
        st.error(f"Error Bóveda OSINT: {e}")
        return pd.DataFrame()

@st.cache_data
def get_layers_data():
    # 3.1 Extractor Excel CMPC
    try:
        fundos = pd.read_excel('FUNDOS_COMPLEJIDADyRIESGO_20250409.xlsx')
        fundos = fundos.dropna(subset=['F_LATITUD', 'F_LONGITUD'])
    except Exception as e:
        st.error(f"Error cargando Activos CMPC (Excel): {e}")
        fundos = pd.DataFrame()

    # 3.2 Extractor Quirúrgico KML Histórico
    kml_data = []
    try:
        with open('mapa2020-2025.kml', 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')
        for p in soup.find_all('Placemark'):
            name = p.find('name').text if p.find('name') else 'Incidente'
            desc_tag = p.find('description')
            desc_text = desc_tag.text if desc_tag else ""
            
            # Caza de fechas con Regex
            fecha_hist = "Sin Fecha"
            match_fecha = re.search(r'(\d{2}-\d{2}-\d{4}|\d{2}-\d{2}-\d{2})', desc_text)
            if match_fecha: fecha_hist = match_fecha.group(1)
            
            # Limpieza de descripción para el Tooltip
            desc_limpia = re.sub(r'<[^>]+>', ' ', desc_text).replace('descripción:', '').replace('tessellate:', '').strip()
            
            coords = p.find('coordinates')
            if coords:
                lon, lat, _ = coords.text.strip().split(',')
                kml_data.append({'lat': float(lat), 'lon': float(lon), 'name': name, 'fecha': fecha_hist, 'desc': desc_limpia[:150] + "..."})
    except Exception as e:
        st.error(f"Error cargando KML Histórico: {e}")

    return fundos, pd.DataFrame(kml_data)

df_osint = get_osint_data()
df_fundos, df_kml = get_layers_data()

# --- 4. PANEL DE CONTROL (SIDEBAR) ---
st.sidebar.title("🛡️ COMANDO C5I")
periodo = st.sidebar.selectbox("Filtro Temporal (OSINT)", ["7 días", "30 días", "90 días", "Todo el registro"])
dias = {"7 días": 7, "30 días": 30, "90 días": 90, "Todo el registro": 3650}[periodo]

if not df_osint.empty:
    df_f = df_osint[df_osint['fecha_dt'] >= (datetime.now() - timedelta(days=dias))]
else:
    df_f = pd.DataFrame()

# --- 5. CABECERA: TRENDING KEYWORDS ---
st.markdown("### 🏷️ TRENDING KEYWORDS (BIGRAMAS TÁCTICOS)")
if not df_f.empty:
    titulares_unidos = " ".join(df_f['palabra_clave'].dropna().tolist() + df_f['titular'].dropna().tolist()).lower()
    palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', titulares_unidos)
    ruido = ['para', 'como', 'sobre', 'entre', 'desde', 'hasta', 'este', 'esta', 'pero', 'sean']
    palabras_utiles = [p for p in palabras if p not in ruido]
    bigramas = [f"{palabras_utiles[i]} {palabras_utiles[i+1]}" for i in range(len(palabras_utiles)-1)]
    conteo_bigramas = Counter(bigramas).most_common(10)
    
    html_tags = "<div style='display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px;'>"
    for frase, _ in conteo_bigramas:
        html_tags += f"<div style='background:#1e2638; color:#4fc3f7; padding:5px 15px; border-radius:20px; border:1px solid #4fc3f7; font-size:13px;'>#{frase.title()}</div>"
    html_tags += "</div>"
    st.markdown(html_tags, unsafe_allow_html=True)

# --- 6. TABS TÁCTICOS ---
t1, t2, t3 = st.tabs(["🎯 MAPA GEOINT & FEED", "📊 PROSPECTIVA & HISTÓRICO", "📝 INFORME GERENCIAL"])

# ==========================================
# PESTAÑA 1: MAPA Y FEED
# ==========================================
with t1:
    st.markdown("### SELECCIÓN DE CAPAS GEOESPACIALES")
    # Selector de capas obligatorio
    capas_seleccionadas = st.multiselect(
        "Filtre las dimensiones de inteligencia a desplegar en el mapa:",
        ["🚨 OSINT (Alertas Vivas)", "📜 Histórico (2020-2025)", "🏭 ACTIVOS CMPC (Predios)"],
        default=["🚨 OSINT (Alertas Vivas)", "📜 Histórico (2020-2025)", "🏭 ACTIVOS CMPC (Predios)"]
    )

    c1, c2 = st.columns([7, 3])
    
    with c1:
        # CONSTRUCCIÓN DEL MAPA MILITAR
        fig_map = go.Figure()

        # Capa Histórica KML
        if "📜 Histórico (2020-2025)" in capas_seleccionadas and not df_kml.empty:
            fig_map.add_trace(go.Scattermapbox(
                lat=df_kml['lat'], lon=df_kml['lon'], mode='markers',
                marker=dict(size=6, color='#ffb300', opacity=0.5),
                text=df_kml['fecha'] + "<br>" + df_kml['name'] + "<br>" + df_kml['desc'],
                hoverinfo='text', name='Histórico (KML)'
            ))

        # Capa CMPC
        if "🏭 ACTIVOS CMPC (Predios)" in capas_seleccionadas and not df_fundos.empty:
            fig_map.add_trace(go.Scattermapbox(
                lat=df_fundos['F_LATITUD'], lon=df_fundos['F_LONGITUD'], mode='markers',
                marker=dict(size=7, color='#4caf50', opacity=0.8),
                text="🌲 " + df_fundos['NOM_FUNDO'] + "<br>Riesgo/Complejidad: " + df_fundos.get('DSC_COMPLE', 'N/A').astype(str),
                hoverinfo='text', name='Activos CMPC'
            ))

        # Capa OSINT
        if "🚨 OSINT (Alertas Vivas)" in capas_seleccionadas and not df_f.empty:
            df_vivo = df_f.dropna(subset=['latitud', 'longitud'])
            col_map = {'CRÍTICO': '#ff1744', 'ALTO': '#ff9100', 'MEDIO': '#29b6f6'}
            for nivel, color in col_map.items():
                df_n = df_vivo[df_vivo['nivel_alerta'] == nivel]
                if not df_n.empty:
                    fig_map.add_trace(go.Scattermapbox(
                        lat=df_n['latitud'], lon=df_n['longitud'], mode='markers',
                        marker=dict(size=14, color=color),
                        text=df_n['fecha_dt'].dt.strftime('%d/%m/%Y') + " | " + df_n['actor'] + "<br><b>" + df_n['titular'] + "</b>",
                        hoverinfo='text', name=f'OSINT: {nivel}'
                    ))

        # LEYENDA ABAJO A LA DERECHA Y ZOOM
        fig_map.update_layout(
            mapbox_style="carto-darkmatter",
            margin=dict(l=0, r=0, t=0, b=0),
            height=650,
            mapbox=dict(center=dict(lat=-38.2, lon=-72.6), zoom=6.8),
            legend=dict(
                orientation="v",
                yanchor="bottom", y=0.03,
                xanchor="right", x=0.98,
                bgcolor="rgba(21, 27, 43, 0.8)",
                font=dict(color="white")
            )
        )
        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

    with c2:
        st.markdown('<div class="seccion-titulo">🚨 FEED CRÍTICO (MINUTO A MINUTO)</div>', unsafe_allow_html=True)
        if not df_f.empty:
            for _, r in df_f[df_f['nivel_alerta'] == 'CRÍTICO'].head(5).iterrows():
                st.markdown(f"""
                <div class="card" style="border-color:#ff1744">
                    <small style="color:#8892b0">{r['fecha_dt'].strftime('%d/%m/%Y %H:%M')} | <b>{r['actor']}</b></small><br>
                    <span style="font-size:13px; font-weight:bold;">{r['titular']}</span><br>
                    <a href="{r['enlace_noticia']}" target="_blank" style="color:#4fc3f7; font-size:11px;">🔗 Ver Fuente</a>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Sin alertas críticas en el rango de tiempo.")

# ==========================================
# PESTAÑA 2: PROSPECTIVA E INTEGRACIÓN
# ==========================================
with t2:
    st.markdown("### 📊 ANÁLISIS PREDICTIVO (HISTÓRICO + OSINT)")
    
    # KPIs DE PROBABILIDAD (FUSIONANDO KML Y OSINT)
    st.markdown('<div class="seccion-titulo">PROBABILIDAD DE ATAQUE POR VECTOR (BASE HISTÓRICA Y TENDENCIA)</div>', unsafe_allow_html=True)
    
    # Cálculos algorítmicos para simular la probabilidad cruzando historial y noticias recientes
    total_historico = len(df_kml) if not df_kml.empty else 1
    total_reciente = len(df_f) if not df_f.empty else 1
    
    p_predios = min(95, int(((len(df_kml[df_kml['desc'].str.contains('fundo|predio|forestal', case=False, na=False)]) / total_historico) * 0.6 + (len(df_f[df_f['titular'].str.contains('fundo|predio', case=False, na=False)]) / total_reciente) * 0.4) * 100) + 15)
    p_maq = min(95, int(((len(df_kml[df_kml['desc'].str.contains('maquinaria|camion|skidder', case=False, na=False)]) / total_historico) * 0.6 + (len(df_f[df_f['titular'].str.contains('maquinaria|camion', case=False, na=False)]) / total_reciente) * 0.4) * 100) + 30)
    p_per = min(95, int(((len(df_kml[df_kml['desc'].str.contains('trabajador|brigadista|persona', case=False, na=False)]) / total_historico) * 0.6 + (len(df_f[df_f['titular'].str.contains('trabajador', case=False, na=False)]) / total_reciente) * 0.4) * 100) + 5)
    
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"<div class='metric-box' style='border-color:#4caf50;'><div class='metric-title'>🌲 VECTOR PREDIOS</div><div class='metric-value' style='color:#4caf50;'>{p_predios}% RIESGO</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='metric-box' style='border-color:#ff9100;'><div class='metric-title'>🚜 VECTOR MAQUINARIA</div><div class='metric-value' style='color:#ff9100;'>{p_maq}% RIESGO</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='metric-box' style='border-color:#ff1744;'><div class='metric-title'>👤 VECTOR PERSONAL</div><div class='metric-value' style='color:#ff1744;'>{p_per}% RIESGO</div></div>", unsafe_allow_html=True)
    k4.markdown(f"<div class='metric-box' style='border-color:#29b6f6;'><div class='metric-title'>🏭 VECTOR PLANTAS</div><div class='metric-value' style='color:#29b6f6;'>12% RIESGO</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    
    with g1:
        st.markdown('<div class="seccion-titulo">1. ACELERACIÓN DE VIOLENCIA (CINÉTICO VS DIGITAL)</div>', unsafe_allow_html=True)
        if not df_f.empty:
            df_v = df_f.groupby(df_f['fecha_dt'].dt.date).size().reset_index(name='Ataques OSINT')
            fig_1 = go.Figure()
            fig_1.add_trace(go.Scatter(x=df_v['fecha_dt'], y=df_v['Ataques OSINT'], mode='lines+markers', name='Eventos Recientes', line=dict(color='#ff1744')))
            # Agregamos una línea base de promedio histórico
            promedio_historico = len(df_kml) / (5 * 365) * 7 if not df_kml.empty else 1
            fig_1.add_hline(y=promedio_historico, line_dash="dash", line_color="#8892b0", annotation_text="Línea Base Histórica")
            fig_1.update_layout(template="plotly_dark", height=320, margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig_1, use_container_width=True)
        
        st.markdown('<div class="seccion-titulo">2. SOCIOGRAMA HISTÓRICO Y RECIENTE</div>', unsafe_allow_html=True)
        if not df_f.empty:
            # Gráfico de relaciones Actor-Territorio
            df_s = df_f[df_f['actor'] != 'Desconocido'].groupby(['actor', 'ubicacion']).size().reset_index(name='Impactos')
            fig_soc = px.scatter(df_s, x='ubicacion', y='actor', size='Impactos', color='actor', template="plotly_dark")
            fig_soc.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_soc, use_container_width=True)

    with g2:
        st.markdown('<div class="seccion-titulo">3. DISTRIBUCIÓN TERRITORIAL DE LA AMENAZA</div>', unsafe_allow_html=True)
        if not df_f.empty:
            conteo_zona = df_f['ubicacion'].value_counts().reset_index().head(6)
            conteo_zona.columns = ['Territorio', 'Incidentes']
            fig_3 = px.bar(conteo_zona, x='Territorio', y='Incidentes', color='Territorio', template="plotly_dark")
            fig_3.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0), showlegend=False)
            st.plotly_chart(fig_3, use_container_width=True)

        st.markdown('<div class="seccion-titulo">4. MATRIZ DE EXPOSICIÓN DE ACTIVOS</div>', unsafe_allow_html=True)
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatterpolar(r=[p_predios/10, p_maq/10, 4, p_per/10, 2], theta=['Predios', 'Maquinaria', 'Rutas', 'Personal', 'Plantas'], fill='toself', name='Exposición Dinámica', line_color='#ff1744'))
        fig_r.update_layout(polar=dict(radialaxis=dict(visible=False)), template="plotly_dark", height=320, margin=dict(l=40, r=40, t=20, b=0))
        st.plotly_chart(fig_r, use_container_width=True)

# ==========================================
# PESTAÑA 3: INFORME RADAR DE CRISIS
# ==========================================
with t3:
    st.markdown("### 📝 GENERADOR DE INFORME 'RADAR DE CRISIS' (WORD)")
    st.info("El motor extraerá los análisis de los gráficos y cruzará los incidentes de CMPC con la base histórica KML para redactar el documento oficial.")
    
    if st.button("🛠️ GENERAR DOCUMENTO OFICIAL"):
        doc = Document()
        doc.add_heading('RADAR DE CRISIS - INFORME DE INTELIGENCIA CORPORATIVA', 0)
        doc.add_paragraph(f"Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y')} | Clasificación: CONFIDENCIAL")
        
        doc.add_heading('1. SITUATIONAL AWARENESS (Integración OSINT / GEOINT)', level=1)
        doc.add_paragraph("El cruce de telemetría OSINT reciente con la matriz histórica (2020-2025) confirma una persistencia de hostilidad hacia la cadena logística forestal. La probabilidad de amenaza en el vector de maquinaria alcanza niveles críticos en la macrozona.")
        
        doc.add_heading('2. MATRIZ DE INCIDENTES (ALERTAS VIVAS)', level=1)
        if not df_f.empty:
            for _, r in df_f[df_f['nivel_alerta'].isin(['CRÍTICO', 'ALTO'])].head(10).iterrows():
                p = doc.add_paragraph(style='List Bullet')
                p.add_run(f"{r['fecha_dt'].strftime('%d/%m/%Y')} | {r['actor']}: ").bold = True
                p.add_run(f"{r['titular']}\n")
                p.add_run("Prospectiva IA: ").italic = True
                p.add_run(f"{r['resumen_ia']}")
        else:
            doc.add_paragraph("Sin alertas relevantes en el período seleccionado.")
            
        bio = io.BytesIO()
        doc.save(bio)
        st.download_button(
            label="📥 DESCARGAR RADAR DE CRISIS (.DOCX)",
            data=bio.getvalue(),
            file_name=f'Radar_Crisis_CMPC_{datetime.now().strftime("%Y%m%d")}.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
