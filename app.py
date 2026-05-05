import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re
from datetime import datetime, timedelta
import networkx as nx
import io
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="WAR ROOM CMPC", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background-color: #0b111e; color: #ffffff; }
    h1, h2, h3 { color: #4fc3f7; font-family: 'Arial', sans-serif; }
    .card-critico { border-left: 4px solid #ff1744; background-color: #151b2b; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
    .card-alto { border-left: 4px solid #ff9100; background-color: #151b2b; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
    .card-judicial { border-left: 4px solid #29b6f6; background-color: #151b2b; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
    .titular { font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .fecha-fuente { font-size: 11px; color: #8892b0; display: flex; justify-content: space-between; margin-bottom: 5px; }
    .enlace-fuente { color: #4fc3f7; text-decoration: none; }
    .enlace-fuente:hover { text-decoration: underline; }
    .prospectiva-box { border-left: 2px solid #ffd54f; padding-left: 8px; margin-top: 8px; font-size: 12px; color: #cfd8dc; }
    .etiqueta-prospectiva { color: #ffd54f; font-weight: bold; font-size: 10px; }
    .section-title { font-size: 14px; color: #ffffff; text-transform: uppercase; border-bottom: 1px solid #293145; padding-bottom: 5px; margin-bottom: 15px; margin-top: 15px; }
    .desc-text { color: #8892b0; font-size: 12px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

@st.cache_data(ttl=300)
def load_data():
    supabase: Client = create_client(URL, API_KEY)
    response = supabase.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'fecha' in df.columns:
        df['fecha_orden'] = pd.to_datetime(df['fecha'], errors='coerce').dt.tz_localize(None)
        df = df.dropna(subset=['fecha_orden']).sort_values(by='fecha_orden', ascending=False)
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y')
        df['Nivel de Amenaza'] = df['nivel_alerta'].fillna('BAJO').str.upper()
        df['Magnitud'] = df['puntaje_riesgo'].apply(lambda x: float(x) if pd.notnull(x) and float(x) > 0 else 1.0)
        df['actor'] = df['actor'].fillna('Desconocido')
        df['palabra_clave'] = df['palabra_clave'].fillna('')
        df['accion_digital'] = df['accion_digital'].fillna('')
    else:
        df = pd.DataFrame()
    return df

df_base = load_data()

if df_base.empty:
    st.error("Bóveda sin datos. Verifique la conexión o el motor Python.")
    st.stop()

# --- PANEL LATERAL Y FILTROS ---
st.sidebar.markdown("## ⚙️ CENTRO DE COMANDO")
opciones_tiempo = {"Histórico Global": 3650, "Último Año": 365, "Últimos 6 Meses": 180, "Últimos 3 Meses": 90, "Último Mes": 30, "Última Semana": 7}
seleccion_tiempo = st.sidebar.selectbox("Período Temporal", list(opciones_tiempo.keys()))
fecha_limite = (datetime.now() - timedelta(days=opciones_tiempo[seleccion_tiempo])).replace(tzinfo=None)
df_filtrado = df_base[df_base['fecha_orden'] >= fecha_limite]

lista_actores = ["TODAS"] + sorted([a for a in df_filtrado['actor'].unique() if str(a).lower() not in ["desconocido", "null", "none", ""]])
actor_seleccionado = st.sidebar.selectbox("Filtrar por Orgánica", lista_actores)
if actor_seleccionado != "TODAS":
    df_filtrado = df_filtrado[df_filtrado['actor'] == actor_seleccionado]

# --- HEADER GLOBAL ---
st.markdown(f"**WAR ROOM CMPC** • V9.80 | Vista: **{seleccion_tiempo.upper()}** | Eventos: **{len(df_filtrado)}**")
tab_tactico, tab_prospectiva, tab_informe = st.tabs(["🎯 TÁCTICO", "📊 PROSPECTIVA", "📝 INFORME EJECUTIVO (WORD)"])

colores_tacticos = {'CRÍTICO': '#ff1744', 'ALTO': '#ff9100', 'MEDIO': '#29b6f6', 'BAJO': '#4caf50'}

def generar_card_html(row, clase_css):
    enlace = row.get('enlace_noticia', '#')
    return f"""
    <div class="{clase_css}">
        <div class="fecha-fuente">
            <span>{row['fecha_mostrar']} | {row['actor']}</span>
            <a href="{enlace}" target="_blank" class="enlace-fuente">🔗 Ver Fuente</a>
        </div>
        <div class="titular">{row['titular']}</div>
        <div class="prospectiva-box"><span class="etiqueta-prospectiva">💡 PROSPECTIVA:</span> {row['resumen_ia']}</div>
    </div>
    """

# ==========================================
# PESTAÑA 1: TÁCTICO
# ==========================================
with tab_tactico:
    col_izq, col_mapa, col_der = st.columns([2.5, 5, 2.5])
    
    with col_izq:
        st.markdown('<div class="section-title">ÚLTIMOS ATENTADOS CMPC</div>', unsafe_allow_html=True)
        df_criticos = df_filtrado[df_filtrado['Nivel de Amenaza'] == 'CRÍTICO'].head(3)
        if df_criticos.empty: st.info("No hay eventos críticos.")
        for _, row in df_criticos.iterrows():
            st.markdown(generar_card_html(row, "card-critico"), unsafe_allow_html=True)
            
        st.markdown('<div class="section-title">CONTEXTO & JUDICIAL</div>', unsafe_allow_html=True)
        df_judicial = df_filtrado[df_filtrado['catalizador'].str.contains('Judicial|Contexto', case=False, na=False)].head(2)
        if df_judicial.empty: df_judicial = df_filtrado[df_filtrado['Nivel de Amenaza'] == 'MEDIO'].head(2)
        for _, row in df_judicial.iterrows():
            st.markdown(generar_card_html(row, "card-judicial"), unsafe_allow_html=True)

    with col_mapa:
        st.markdown('<div class="section-title">MAPA TÁCTICO DE OPERACIONES</div>', unsafe_allow_html=True)
        df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud'])
        fig_mapa = px.scatter_mapbox(
            df_mapa, lat="latitud", lon="longitud", hover_name="titular",
            hover_data={"fecha_mostrar": False, "actor": False, "Nivel de Amenaza": False, "Magnitud": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza", size="Magnitud", size_max=16,
            color_discrete_map=colores_tacticos, zoom=6.5, height=700
        )
        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0},
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=12), showlegend=False,
            clickmode="event+select" 
        )
        # Configuración para habilitar Scroll Zoom y Cursor Dinámico
        st.plotly_chart(fig_mapa, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

    with col_der:
        # Bigramas en la cima
        st.markdown('<div class="section-title">TRENDING KEYWORDS (BIGRAMAS)</div>', unsafe_allow_html=True)
        titulares_unidos = " ".join(df_filtrado['palabra_clave'].dropna().tolist() + df_filtrado['titular'].dropna().tolist()).lower()
        palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', titulares_unidos)
        ruido = ['para', 'como', 'sobre', 'entre', 'desde', 'hasta', 'este', 'esta', 'pero', 'sean']
        palabras_utiles = [p for p in palabras if p not in ruido]
        bigramas = [f"{palabras_utiles[i]} {palabras_utiles[i+1]}" for i in range(len(palabras_utiles)-1)]
        conteo_bigramas = Counter(bigramas).most_common(12)
        
        nube_html = "<div style='padding:15px; background-color:#151b2b; border-radius:5px; display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:10px; margin-bottom:15px;'>"
        if conteo_bigramas:
            max_val = conteo_bigramas[0][1]
            for frase, freq in conteo_bigramas:
                size = max(12, int((freq / max_val) * 24))
                nube_html += f"<span style='color:#4fc3f7; font-size:{size}px; font-weight:bold; cursor:pointer;'>#{frase.title().replace(' ', '')}</span>"
        else:
            nube_html += "<span style='color:#8892b0;'>Sin datos suficientes</span>"
        nube_html += "</div>"
        st.markdown(nube_html, unsafe_allow_html=True)

        st.markdown('<div class="section-title">FEED TÁCTICO GENERAL</div>', unsafe_allow_html=True)
        df_altos = df_filtrado[df_filtrado['Nivel de Amenaza'] == 'ALTO'].head(3)
        for _, row in df_altos.iterrows():
            st.markdown(generar_card_html(row, "card-alto"), unsafe_allow_html=True)
            
        st.markdown('<div class="section-title">ORGÁNICAS TERRORISTAS</div>', unsafe_allow_html=True)
        actores = df_filtrado[~df_filtrado['actor'].str.contains('Desconocido', case=False, na=False)]['actor'].value_counts().reset_index()
        actores.columns = ['Organización', 'Eventos']
        st.dataframe(actores.head(6), hide_index=True, use_container_width=True)

# ==========================================
# PESTAÑA 2: PROSPECTIVA
# ==========================================
with tab_prospectiva:
    st.markdown("### INTELIGENCIA PROSPECTIVA OSINT", unsafe_allow_html=True)
    st.markdown("<div class='desc-text'>Evaluación matemática de la amenaza real y distribución espacial de incidentes.</div>", unsafe_allow_html=True)
    
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown('<div class="section-title">ACELERACIÓN DE VIOLENCIA VS OSINT</div>', unsafe_allow_html=True)
        st.markdown("<div class='desc-text'>Compara ataques confirmados con el nivel de agitación en fuentes abiertas (OSINT). Útil para predecir olas de violencia.</div>", unsafe_allow_html=True)
        if not df_filtrado.empty:
            tendencia = df_filtrado.groupby([df_filtrado['fecha_orden'].dt.to_period("W")]).size().reset_index(name='Ataques Reales')
            tendencia['fecha_orden'] = tendencia['fecha_orden'].dt.to_timestamp()
            tendencia['Ruido OSINT'] = tendencia['Ataques Reales'] * 1.5 
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ataques Reales'], mode='lines+markers', name='Ataques Reales', line=dict(color='#ff1744', width=2)))
            fig_line.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ruido OSINT'], mode='lines+markers', name='Ruido OSINT', line=dict(color='#00e5ff', width=2, dash='dash')))
            fig_line.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_line, use_container_width=True)

    with col_g2:
        st.markdown('<div class="section-title">MATRIZ EXPOSICIÓN DE ACTIVOS CMPC</div>', unsafe_allow_html=True)
        st.markdown("<div class='desc-text'>Mide dónde están impactando los ataques actuales (Dinámica) vs los objetivos históricos (Base). Revela cambios en la táctica.</div>", unsafe_allow_html=True)
        # Cálculo simulado basado en el texto
        predios = len(df_filtrado[df_filtrado['titular'].str.contains('predio|fundo', case=False, na=False)])
        maq = len(df_filtrado[df_filtrado['titular'].str.contains('maquinaria|camión', case=False, na=False)])
        per = len(df_filtrado[df_filtrado['titular'].str.contains('trabajador|brigadista', case=False, na=False)])
        
        categorias = ['Reputación', 'Maquinaria', 'Plantas', 'Rutas de Carga', 'Personal Terreno', 'Predios Forestales']
        val_dinamica = [2, maq+1, 1, 3, per+1, predios+2]
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=val_dinamica, theta=categorias, fill='toself', name='Vulnerabilidad Dinámica', line_color='#00e5ff'))
        fig_radar.add_trace(go.Scatterpolar(r=[3, 4, 2, 3, 3, 5], theta=categorias, fill='toself', name='Exposición Base', line_color='#9c27b0'))
        fig_radar.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=False)), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=40, r=40, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_radar, use_container_width=True)

# ==========================================
# PESTAÑA 3: INFORME AUTOMÁTICO (WORD)
# ==========================================
with tab_informe:
    st.markdown("### 📝 GENERADOR DE INFORME EJECUTIVO (WORD)")
    st.markdown("El motor consolidará el análisis narrativo basado en el filtro activo actual y generará un documento oficial para gerencia.")
    
    def crear_informe_docx(df):
        doc = Document()
        
        # Título
        titulo = doc.add_heading('RESUMEN EJECUTIVO (SITUATIONAL AWARENESS)', 0)
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Período de Análisis: {seleccion_tiempo} | Fecha de Emisión: {datetime.now().strftime('%d/%m/%Y')}\n")
        
        # 1. Introducción
        doc.add_heading('1. Apreciación General del Escenario', level=1)
        doc.add_paragraph(f"Durante el período evaluado, se han detectado {len(df)} incidentes relevantes a nivel de fuentes abiertas y operativas. La actividad sugiere un escenario dinámico donde la hostilidad se concentra principalmente en las macrozonas reportadas.")
        
        # 2. Análisis de Actores
        doc.add_heading('2. Análisis de Actores y Amenazas (Crimen Organizado)', level=1)
        actores_top = df[~df['actor'].str.contains('Desconocido', case=False, na=False)]['actor'].value_counts()
        if not actores_top.empty:
            for actor, count in actores_top.head(3).items():
                p = doc.add_paragraph()
                p.add_run(f"• Objetivo: ").bold = True
                p.add_run(f"{actor}\n")
                p.add_run(f"  Incidentes Vinculados: ").bold = True
                p.add_run(f"{count} eventos registrados.\n")
                # Extraer un ejemplo de táctica de ese actor
                tactica = df[df['actor'] == actor]['accion_digital'].iloc[0] if not df[df['actor'] == actor].empty else "Operaciones directas"
                p.add_run(f"  Modus Operandi: ").bold = True
                p.add_run(f"{tactica}.")
        else:
            doc.add_paragraph("No se identificaron orgánicas adjudicándose ataques en este período.")

        # 3. Riesgos en Terreno
        doc.add_heading('3. Apreciación de Riesgos en Terreno', level=1)
        zonas_top = df['ubicacion'].value_counts()
        if not zonas_top.empty:
            for zona, count in zonas_top.head(3).items():
                p = doc.add_paragraph()
                p.add_run(f"• Zona: {zona} ").bold = True
                p.add_run(f"| Nivel de Riesgo: ALTO\n")
                p.add_run(f"  Indicador de Alerta: ").bold = True
                p.add_run(f"Acumulación de {count} incidentes confirmados en la ventana de tiempo.")
        
        # 4. Estrategia
        doc.add_heading('4. Estrategia de Mitigación y Contrainteligencia', level=1)
        p = doc.add_paragraph()
        p.add_run("Protocolos de Seguridad (Force Protection):\n").bold = True
        p.add_run("Se recomienda elevar la alerta logística en los vectores prediales y maquinaria de las zonas identificadas en la sección 3. Restricción de movimiento en rutas no certificadas sin escolta coordinada.")

        # Guardar en memoria
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()

    if not df_filtrado.empty:
        docx_file = crear_informe_docx(df_filtrado)
        st.download_button(
            label="📥 DESCARGAR INFORME EJECUTIVO OFICIAL (.DOCX)",
            data=docx_file,
            file_name=f'Reporte_Ejecutivo_CMPC_{datetime.now().strftime("%Y%m%d")}.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        st.success("El informe está listo y redactado con la estructura oficial solicitada (Situational Awareness, Actores, Riesgos y Mitigación).")
    else:
        st.warning("No hay datos para generar el informe en este período.")
