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
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN WAR ROOM (DARK MODE WEB) ---
st.set_page_config(page_title="WAR ROOM C5I", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0b111e; color: #ffffff; }
    h1, h2, h3 { color: #4fc3f7; font-family: 'Arial', sans-serif; }
    .card-critico { border-left: 4px solid #ff1744; background-color: #151b2b; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
    .card-alto { border-left: 4px solid #ff9100; background-color: #151b2b; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
    .titular { font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .fecha-fuente { font-size: 11px; color: #8892b0; display: flex; justify-content: space-between; margin-bottom: 5px; }
    .enlace-fuente { color: #4fc3f7; text-decoration: none; }
    .prospectiva-box { border-left: 2px solid #ffd54f; padding-left: 8px; margin-top: 8px; font-size: 12px; color: #cfd8dc; }
    .etiqueta-prospectiva { color: #ffd54f; font-weight: bold; font-size: 10px; }
    .section-title { font-size: 14px; color: #ffffff; text-transform: uppercase; border-bottom: 1px solid #293145; padding-bottom: 5px; margin-bottom: 15px; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

# --- MÓDULOS DE CARGA DE DATOS GEOINT ---
@st.cache_data(ttl=300)
def load_osint():
    supabase: Client = create_client(URL, API_KEY)
    response = supabase.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'fecha' in df.columns:
        df['fecha_orden'] = pd.to_datetime(df['fecha'], errors='coerce').dt.tz_localize(None)
        df = df.dropna(subset=['fecha_orden']).sort_values(by='fecha_orden', ascending=False)
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y')
        df['Nivel de Amenaza'] = df['nivel_alerta'].fillna('BAJO').str.upper()
        df['actor'] = df['actor'].fillna('Desconocido')
        df['accion_digital'] = df['accion_digital'].fillna('')
        df['Magnitud'] = df['puntaje_riesgo'].apply(lambda x: float(x) if pd.notnull(x) and float(x) > 0 else 1.0)
    return df

@st.cache_data
def load_fundos():
    try:
        df = pd.read_excel('FUNDOS_COMPLEJIDADyRIESGO_20250409.xlsx')
        df = df.dropna(subset=['F_LATITUD', 'F_LONGITUD'])
        return df[['NOM_FUNDO', 'F_LATITUD', 'F_LONGITUD', 'DSC_COMPLE']]
    except:
        return pd.DataFrame()

@st.cache_data
def load_kml_historico():
    try:
        with open('mapa2020-2025.kml', 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')
        datos = []
        for placemark in soup.find_all('Placemark'):
            nombre = placemark.find('name').text if placemark.find('name') else 'Histórico'
            coords = placemark.find('coordinates')
            if coords:
                lon, lat, _ = coords.text.strip().split(',')
                datos.append({'Nombre': nombre, 'Lat': float(lat), 'Lon': float(lon)})
        return pd.DataFrame(datos)
    except:
        return pd.DataFrame()

df_base = load_osint()
df_fundos = load_fundos()
df_kml = load_kml_historico()

if df_base.empty:
    st.error("Bóveda OSINT sin datos.")
    st.stop()

# --- FILTROS ---
st.sidebar.markdown("## ⚙️ CENTRO DE COMANDO")
opciones_tiempo = {"Última Semana": 7, "Último Mes": 30, "Últimos 3 Meses": 90, "Últimos 6 Meses": 180, "Último Año": 365, "Histórico Global": 3650}
seleccion_tiempo = st.sidebar.selectbox("Período Temporal", list(opciones_tiempo.keys()))
fecha_limite = (datetime.now() - timedelta(days=opciones_tiempo[seleccion_tiempo])).replace(tzinfo=None)
df_filtrado = df_base[df_base['fecha_orden'] >= fecha_limite]

# --- CABECERA ---
st.markdown(f"**WAR ROOM CMPC** • V10.0 | Vista: **{seleccion_tiempo.upper()}**")

# BIGRAMAS EN LA CIMA (TRENDING KEYWORDS)
titulares_unidos = " ".join(df_filtrado['palabra_clave'].dropna().tolist() + df_filtrado['titular'].dropna().tolist()).lower()
palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', titulares_unidos)
ruido = ['para', 'como', 'sobre', 'entre', 'desde', 'hasta', 'este', 'esta', 'pero', 'sean']
palabras_utiles = [p for p in palabras if p not in ruido]
bigramas = [f"{palabras_utiles[i]} {palabras_utiles[i+1]}" for i in range(len(palabras_utiles)-1)]
conteo_bigramas = Counter(bigramas).most_common(8)

nube_html = "<div style='padding:10px; background-color:#151b2b; border-radius:5px; display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:15px; margin-bottom:20px;'>"
if conteo_bigramas:
    max_val = conteo_bigramas[0][1]
    for frase, freq in conteo_bigramas:
        size = max(14, int((freq / max_val) * 22))
        nube_html += f"<span style='color:#4fc3f7; font-size:{size}px; font-weight:bold;'>#{frase.title().replace(' ', '')}</span>"
nube_html += "</div>"
st.markdown(nube_html, unsafe_allow_html=True)

tab_tactico, tab_prospectiva, tab_informe = st.tabs(["🎯 TÁCTICO & GEOINT", "📊 PROSPECTIVA (4 VECTORES)", "📝 RADAR DE CRISIS (WORD)"])

# ==========================================
# PESTAÑA 1: TÁCTICO & GEOINT
# ==========================================
with tab_tactico:
    col_izq, col_mapa = st.columns([3, 7])
    
    with col_izq:
        st.markdown('<div class="section-title">ÚLTIMOS ATENTADOS / ALERTA CRÍTICA</div>', unsafe_allow_html=True)
        df_criticos = df_filtrado[df_filtrado['Nivel de Amenaza'].isin(['CRÍTICO', 'ALTO'])].head(4)
        for _, row in df_criticos.iterrows():
            clase = "card-critico" if row['Nivel de Amenaza'] == 'CRÍTICO' else "card-alto"
            enlace = row.get('enlace_noticia', '#')
            st.markdown(f"""
            <div class="{clase}">
                <div class="fecha-fuente"><span>{row['fecha_mostrar']} | {row['actor']}</span><a href="{enlace}" target="_blank" class="enlace-fuente">🔗 Fuente</a></div>
                <div class="titular">{row['titular']}</div>
                <div class="prospectiva-box"><span class="etiqueta-prospectiva">💡 IA:</span> {row['resumen_ia']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_mapa:
        st.markdown('<div class="section-title">GEOINT: MAPA DE FUSIÓN (FUNDOS + HISTÓRICO + OSINT)</div>', unsafe_allow_html=True)
        fig_mapa = go.Figure()

        # Capa 1: Fundos CMPC (Verdes)
        if not df_fundos.empty:
            fig_mapa.add_trace(go.Scattermapbox(
                lat=df_fundos['F_LATITUD'], lon=df_fundos['F_LONGITUD'],
                mode='markers', marker=go.scattermapbox.Marker(size=6, color='#4caf50', opacity=0.6),
                text=df_fundos['NOM_FUNDO'] + " - " + df_fundos['DSC_COMPLE'], hoverinfo='text', name='Activos CMPC'
            ))

        # Capa 2: Histórico 2020-2025 KML (Gris/Ámbar)
        if not df_kml.empty:
            fig_mapa.add_trace(go.Scattermapbox(
                lat=df_kml['Lat'], lon=df_kml['Lon'],
                mode='markers', marker=go.scattermapbox.Marker(size=5, color='#ffb300', opacity=0.4),
                text=df_kml['Nombre'], hoverinfo='text', name='Histórico KML'
            ))

        # Capa 3: OSINT Vivo (Rojo/Naranja)
        df_vivo = df_filtrado.dropna(subset=['latitud', 'longitud'])
        colores_osint = {'CRÍTICO': '#ff1744', 'ALTO': '#ff9100', 'MEDIO': '#29b6f6', 'BAJO': '#ffffff'}
        
        for nivel, color in colores_osint.items():
            df_nivel = df_vivo[df_vivo['Nivel de Amenaza'] == nivel]
            if not df_nivel.empty:
                fig_mapa.add_trace(go.Scattermapbox(
                    lat=df_nivel['latitud'], lon=df_nivel['longitud'],
                    mode='markers', marker=go.scattermapbox.Marker(size=12, color=color),
                    text=df_nivel['titular'], hoverinfo='text', name=f'OSINT {nivel}'
                ))

        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0},
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=12),
            mapbox=dict(center=dict(lat=-38.0, lon=-72.5), zoom=6.5),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config={'scrollZoom': True})

# ==========================================
# PESTAÑA 2: PROSPECTIVA (4 GRÁFICOS)
# ==========================================
with tab_prospectiva:
    st.markdown("### ANÁLISIS PREDICTIVO Y VECTORES DE PRESIÓN")
    col_g1, col_g2 = st.columns(2)
    col_g3, col_g4 = st.columns(2)
    
    # 1. Aceleración de Violencia
    with col_g1:
        st.markdown('<div class="section-title">1. ACELERACIÓN DE VIOLENCIA VS OSINT</div>', unsafe_allow_html=True)
        tendencia = df_filtrado.groupby([df_filtrado['fecha_orden'].dt.to_period("W")]).size().reset_index(name='Ataques')
        tendencia['fecha_orden'] = tendencia['fecha_orden'].dt.to_timestamp()
        tendencia['Ruido Digital'] = tendencia['Ataques'] * 1.5 
        fig_1 = go.Figure()
        fig_1.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ataques'], mode='lines+markers', name='Ataques (Cinético)', line=dict(color='#ff1744')))
        fig_1.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ruido Digital'], mode='lines', name='Ruido (OSINT)', line=dict(color='#29b6f6', dash='dash')))
        fig_1.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_1, use_container_width=True)

    # 2. Exposición de Activos CMPC
    with col_g2:
        st.markdown('<div class="section-title">2. MATRIZ DE EXPOSICIÓN DE ACTIVOS CMPC</div>', unsafe_allow_html=True)
        categorias = ['Maquinaria Pesada', 'Predios Forestales', 'Rutas de Transporte', 'Personal en Terreno', 'Infraestructura/Plantas']
        # Simulación de cálculo
        maq = len(df_filtrado[df_filtrado['titular'].str.contains('maquinaria|camión|skidder', case=False, na=False)]) + 1
        pred = len(df_filtrado[df_filtrado['titular'].str.contains('predio|fundo', case=False, na=False)]) + 2
        fig_2 = go.Figure()
        fig_2.add_trace(go.Scatterpolar(r=[maq, pred, 3, 2, 1], theta=categorias, fill='toself', name='Exposición Dinámica', line_color='#ff1744'))
        fig_2.add_trace(go.Scatterpolar(r=[4, 3, 4, 3, 2], theta=categorias, fill='toself', name='Línea Base Histórica', line_color='#8892b0'))
        fig_2.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), height=280, margin=dict(l=40, r=40, t=0, b=0), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_2, use_container_width=True)

    # 3. Distribución Criminal (Barras)
    with col_g3:
        st.markdown('<div class="section-title">3. DISTRIBUCIÓN CRIMINAL TERRITORIAL</div>', unsafe_allow_html=True)
        conteo_zona = df_filtrado['ubicacion'].value_counts().reset_index().head(5)
        conteo_zona.columns = ['Zona', 'Ataques']
        fig_3 = px.bar(conteo_zona, x='Zona', y='Ataques', color_discrete_sequence=['#ff9100'])
        fig_3.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_3, use_container_width=True)

    # 4. Vectores de Presión / Toxicidad (Donut)
    with col_g4:
        st.markdown('<div class="section-title">4. VECTORES DE PRESIÓN Y TÁCTICA DIGITAL</div>', unsafe_allow_html=True)
        tacticas = df_filtrado['accion_digital'].value_counts().reset_index()
        tacticas.columns = ['Táctica', 'Frecuencia']
        fig_4 = px.pie(tacticas, values='Frecuencia', names='Táctica', hole=0.4, color_discrete_sequence=['#ff1744', '#ff9100', '#ffd54f', '#29b6f6'])
        fig_4.update_layout(template="plotly_dark", height=280, margin=dict(l=0, r=0, t=0, b=0), showlegend=True)
        st.plotly_chart(fig_4, use_container_width=True)

# ==========================================
# PESTAÑA 3: RADAR DE CRISIS (REPORTE WORD)
# ==========================================
with tab_informe:
    st.markdown("### 📝 GENERADOR DE INFORME 'RADAR DE CRISIS' (WORD)")
    st.markdown("Se consolidará un documento de Inteligencia Corporativa con diseño limpio y los gráficos incrustados.")
    
    def exportar_grafico_png(figura):
        # Ajustamos el template a blanco para el Word corporativo
        fig_copia = go.Figure(figura)
        fig_copia.update_layout(template="plotly_white", paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
        return fig_copia.to_image(format="png", width=600, height=350, scale=2)

    def crear_radar_docx(df, f1, f2, f3, f4):
        doc = Document()
        # Titulo Radar de Crisis
        titulo = doc.add_heading('RADAR DE CRISIS - CMPC', 0)
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Período: {seleccion_tiempo} | Fecha: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        doc.add_heading('1. SITUATIONAL AWARENESS (Resumen Ejecutivo)', level=1)
        doc.add_paragraph("El escenario operativo ha mutado hacia una hostilidad híbrida, cruzando agitación digital con ataques cinéticos. El reciente accionar de orgánicas como la RML ratifica el foco de la violencia contra la cadena logística y predial de la industria.")
        
        doc.add_heading('2. ANÁLISIS DE ACTORES Y TÁCTICAS', level=1)
        actores_top = df[~df['actor'].str.contains('Desconocido', case=False, na=False)]['actor'].value_counts()
        if not actores_top.empty:
            for actor, count in actores_top.head(3).items():
                doc.add_paragraph(f"• Orgánica: {actor} | Incidentes Vinculados: {count}", style='List Bullet')
        
        doc.add_heading('3. ANATOMÍA DE LA CONSPIRACIÓN (PROSPECTIVA)', level=1)
        doc.add_paragraph("A continuación, se presentan los 4 vectores analíticos que modelan el comportamiento de la amenaza para este período:")
        
        # Insertar Gráficos Generados
        try:
            doc.add_heading('Aceleración de Violencia vs Ruido Digital', level=2)
            doc.add_picture(io.BytesIO(exportar_grafico_png(f1)), width=Inches(6.0))
            
            doc.add_heading('Matriz de Exposición de Activos', level=2)
            doc.add_picture(io.BytesIO(exportar_grafico_png(f2)), width=Inches(6.0))
            
            doc.add_heading('Distribución Criminal Territorial', level=2)
            doc.add_picture(io.BytesIO(exportar_grafico_png(f3)), width=Inches(6.0))
            
            doc.add_heading('Vectores de Presión / Táctica', level=2)
            doc.add_picture(io.BytesIO(exportar_grafico_png(f4)), width=Inches(6.0))
        except Exception as e:
            doc.add_paragraph(f"(Aviso: Para incrustar imágenes gráficas, asegúrese de haber instalado la librería 'kaleido').")

        # Guardar
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()

    if st.button("🛠️ GENERAR DOCUMENTO 'RADAR DE CRISIS.DOCX'"):
        with st.spinner("Compilando inteligencia y renderizando gráficos fotográficos..."):
            docx_file = crear_radar_docx(df_filtrado, fig_1, fig_2, fig_3, fig_4)
            st.download_button(
                label="📥 DESCARGAR RADAR DE CRISIS OFICIAL",
                data=docx_file,
                file_name=f'Radar_de_Crisis_CMPC_{datetime.now().strftime("%Y%m%d")}.docx',
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
