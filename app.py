import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="WAR ROOM CMPC", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

# --- CSS PERSONALIZADO (Grado Militar / Interfaz Oscura) ---
st.markdown("""
<style>
    .stApp { background-color: #0b111e; color: #ffffff; }
    h1, h2, h3 { color: #4fc3f7; font-family: 'Arial', sans-serif; }
    
    /* Tarjetas de Feed */
    .card-critico { border-left: 4px solid #ff1744; background-color: #151b2b; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
    .card-alto { border-left: 4px solid #ff9100; background-color: #151b2b; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
    .card-judicial { border-left: 4px solid #29b6f6; background-color: #151b2b; padding: 10px; margin-bottom: 10px; border-radius: 4px; }
    
    .titular { font-size: 14px; font-weight: bold; margin-bottom: 5px; }
    .fecha-fuente { font-size: 11px; color: #8892b0; text-align: right; }
    .prospectiva-box { border-left: 2px solid #ffd54f; padding-left: 8px; margin-top: 8px; font-size: 12px; color: #cfd8dc; }
    .etiqueta-prospectiva { color: #ffd54f; font-weight: bold; font-size: 10px; }
    
    /* Contenedores de Sección */
    .section-title { font-size: 14px; color: #ffffff; text-transform: uppercase; border-bottom: 1px solid #293145; padding-bottom: 5px; margin-bottom: 15px; margin-top: 15px; }
    
    /* KPIs Prospectiva */
    .kpi-box { background-color: #151b2b; padding: 15px; border-radius: 5px; border-top: 3px solid; text-align: left; }
    .kpi-title { font-size: 12px; color: #8892b0; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- CREDENCIALES ---
URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

@st.cache_data(ttl=300)
def load_data():
    supabase: Client = create_client(URL, API_KEY)
    response = supabase.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'fecha' in df.columns:
        df['fecha_orden'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha_orden']).sort_values(by='fecha_orden', ascending=False)
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y')
        df['Nivel de Amenaza'] = df['nivel_alerta'].fillna('BAJO').str.upper()
        df['Magnitud'] = df['puntaje_riesgo'].apply(lambda x: float(x) if pd.notnull(x) and float(x) > 0 else 1.0)
        df['actor'] = df['actor'].fillna('Desconocido')
        df['palabra_clave'] = df['palabra_clave'].fillna('')
    else:
        df = pd.DataFrame()
    return df

df_base = load_data()

if df_base.empty:
    st.error("Bóveda sin datos. Verifique la conexión o el motor Python.")
    st.stop()

# --- HEADER GLOBAL ---
st.markdown(f"**WAR ROOM CMPC** • V9.40 | Vista: **HISTÓRICO GLOBAL** | Eventos: **{len(df_base)}**")
tab_tactico, tab_prospectiva = st.tabs(["🎯 TÁCTICO", "📊 PROSPECTIVA"])

colores_tacticos = {'CRÍTICO': '#ff1744', 'ALTO': '#ff9100', 'MEDIO': '#29b6f6', 'BAJO': '#4caf50'}

# ==========================================
# PESTAÑA 1: TÁCTICO
# ==========================================
with tab_tactico:
    col_izq, col_mapa, col_der = st.columns([2.5, 5, 2.5])
    
    # --- COLUMNA IZQUIERDA ---
    with col_izq:
        st.markdown('<div class="section-title">FEED MULTIMEDIA (7 DÍAS)</div>', unsafe_allow_html=True)
        st.info("Conexión a repositorio de imágenes activada. Esperando capturas OSINT.")
        
        st.markdown('<div class="section-title">ÚLTIMOS ATENTADOS CMPC</div>', unsafe_allow_html=True)
        df_criticos = df_base[df_base['Nivel de Amenaza'] == 'CRÍTICO'].head(3)
        for _, row in df_criticos.iterrows():
            st.markdown(f"""
            <div class="card-critico">
                <div class="fecha-fuente">{row['fecha_mostrar']} | {row['actor']}</div>
                <div class="titular">{row['titular']}</div>
                <div class="prospectiva-box"><span class="etiqueta-prospectiva">💡 PROSPECTIVA:</span> {row['resumen_ia']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('<div class="section-title">CONTEXTO & JUDICIAL</div>', unsafe_allow_html=True)
        df_judicial = df_base[df_base['catalizador'].str.contains('Judicial|Contexto', case=False, na=False)].head(2)
        if df_judicial.empty:
             df_judicial = df_base[df_base['Nivel de Amenaza'] == 'MEDIO'].head(2)
        for _, row in df_judicial.iterrows():
            st.markdown(f"""
            <div class="card-judicial">
                <div class="fecha-fuente">{row['fecha_mostrar']}</div>
                <div class="titular">{row['titular']}</div>
                <div class="prospectiva-box"><span class="etiqueta-prospectiva">💡 PROSPECTIVA:</span> {row['resumen_ia']}</div>
            </div>
            """, unsafe_allow_html=True)

    # --- COLUMNA CENTRAL (MAPA) ---
    with col_mapa:
        st.markdown('<div class="section-title">MAPA TÁCTICO DE OPERACIONES</div>', unsafe_allow_html=True)
        df_mapa = df_base.dropna(subset=['latitud', 'longitud'])
        fig_mapa = px.scatter_mapbox(
            df_mapa, lat="latitud", lon="longitud", hover_name="titular",
            hover_data={"fecha_mostrar": False, "actor": False, "Nivel de Amenaza": False, "Magnitud": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza", size="Magnitud", size_max=12,
            color_discrete_map=colores_tacticos, zoom=6.5, height=750
        )
        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0},
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=12, font_family="Arial"),
            showlegend=False
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config={'displayModeBar': False})

    # --- COLUMNA DERECHA ---
    with col_der:
        st.markdown('<div class="section-title">FEED TÁCTICO GENERAL</div>', unsafe_allow_html=True)
        df_altos = df_base[df_base['Nivel de Amenaza'] == 'ALTO'].head(3)
        for _, row in df_altos.iterrows():
            st.markdown(f"""
            <div class="card-alto">
                <div class="fecha-fuente">{row['fecha_mostrar']}</div>
                <div class="titular">{row['titular']}</div>
                <div class="prospectiva-box"><span class="etiqueta-prospectiva">💡 PROSPECTIVA:</span> {row['resumen_ia']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown('<div class="section-title">ORGÁNICAS TERRORISTAS</div>', unsafe_allow_html=True)
        actores = df_base[~df_base['actor'].str.contains('Desconocido', case=False)]['actor'].value_counts().reset_index()
        actores.columns = ['Organización', 'Eventos']
        st.dataframe(actores.head(5), hide_index=True, use_container_width=True)
        
        st.markdown('<div class="section-title">TRENDING KEYWORDS</div>', unsafe_allow_html=True)
        todas_palabras = " ".join(df_base['palabra_clave'].dropna().tolist())
        palabras_limpias = [p.capitalize() for p in re.findall(r'\b\w+\b', todas_palabras) if len(p) > 3]
        conteo_palabras = Counter(palabras_limpias).most_common(12)
        tags_html = " ".join([f"<span style='color:#4fc3f7; font-size:12px; margin-right:8px;'>#{word}</span>" for word, _ in conteo_palabras])
        st.markdown(f"<div style='padding:10px; background-color:#151b2b; border-radius:5px;'>{tags_html}</div>", unsafe_allow_html=True)


# ==========================================
# PESTAÑA 2: PROSPECTIVA
# ==========================================
with tab_prospectiva:
    st.markdown("### INTELIGENCIA PROSPECTIVA OSINT", unsafe_allow_html=True)
    st.markdown("<span style='color:#8892b0; font-size:12px;'>Evaluación matemática de la amenaza real y distribución espacial.</span>", unsafe_allow_html=True)
    
    # --- KPIs Superiores ---
    k1, k2, k3, k4 = st.columns(4)
    k1.markdown("""<div class="kpi-box" style="border-color:#4caf50;"><div class="kpi-title">🌲 VECTOR PREDIAL</div><div class="kpi-value" style="color:#4caf50;">17%</div></div>""", unsafe_allow_html=True)
    k2.markdown("""<div class="kpi-box" style="border-color:#ff1744;"><div class="kpi-title">👤 VECTOR CONTRA PERSONAL</div><div class="kpi-value" style="color:#ff1744;">5%</div></div>""", unsafe_allow_html=True)
    k3.markdown("""<div class="kpi-box" style="border-color:#ba68c8;"><div class="kpi-title">🚜 VECTOR RUTAS/MAQUINARIA</div><div class="kpi-value" style="color:#ba68c8;">5%</div></div>""", unsafe_allow_html=True)
    k4.markdown("""<div class="kpi-box" style="border-color:#ffb300;"><div class="kpi-title">🏭 VECTOR PLANTAS</div><div class="kpi-value" style="color:#ffb300;">0%</div></div>""", unsafe_allow_html=True)
    
    st.write("")
    
    # --- Fila de Gráficos 1 ---
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown('<div class="section-title">ACELERACIÓN DE VIOLENCIA VS OSINT</div>', unsafe_allow_html=True)
        tendencia = df_base.groupby([df_base['fecha_orden'].dt.to_period("M")]).size().reset_index(name='Ataques Reales')
        tendencia['fecha_orden'] = tendencia['fecha_orden'].dt.to_timestamp()
        tendencia['Ruido OSINT'] = tendencia['Ataques Reales'] * 1.8  # Simulación de volumen
        
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ataques Reales'], mode='lines+markers', name='Ataques Reales', line=dict(color='#ff1744', width=2)))
        fig_line.add_trace(go.Scatter(x=tendencia['fecha_orden'], y=tendencia['Ruido OSINT'], mode='lines+markers', name='Ruido OSINT', line=dict(color='#00e5ff', width=2, dash='dash')))
        fig_line.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_line, use_container_width=True)

    with col_g2:
        st.markdown('<div class="section-title">MATRIZ EXPOSICIÓN DE ACTIVOS CMPC</div>', unsafe_allow_html=True)
        categorias = ['Reputación', 'Maquinaria', 'Plantas', 'Rutas de Carga', 'Personal Terreno', 'Predios Forestales']
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=[2, 5, 1, 4, 2, 8], theta=categorias, fill='toself', name='Vulnerabilidad Dinámica', line_color='#00e5ff'))
        fig_radar.add_trace(go.Scatterpolar(r=[3, 4, 2, 3, 3, 5], theta=categorias, fill='toself', name='Exposición Base', line_color='#9c27b0'))
        fig_radar.update_layout(template="plotly_dark", polar=dict(radialaxis=dict(visible=True, range=[0, 10], color='#8892b0')), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=300, margin=dict(l=40, r=40, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_radar, use_container_width=True)

    # --- Fila de Gráficos 2 ---
    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        st.markdown('<div class="section-title">DISTRIBUCIÓN CRIMINAL POR MACROZONA</div>', unsafe_allow_html=True)
        conteo_zona = df_base['ubicacion'].value_counts().reset_index().head(6)
        conteo_zona.columns = ['Zona', 'Ataques']
        fig_bar = px.bar(conteo_zona, x='Zona', y='Ataques', color_discrete_sequence=['#ff1744'])
        fig_bar.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_g4:
        st.markdown('<div class="section-title">SOCIOGRAMA TÁCTICO (LINK ANALYSIS)</div>', unsafe_allow_html=True)
        # Simulación de Grafo de red con Scatter para Plotly nativo
        fig_net = go.Figure(data=[go.Scatter(
            x=[1, 2, 3, 2, 4, 3.5, 1.5], y=[2, 3, 1.5, 1, 2.5, 0.5, 0.8],
            mode='markers+text',
            marker=dict(size=[40, 20, 25, 30, 15, 20, 15], color=['#ff1744', '#00e5ff', '#ff9100', '#ff1744', '#9c27b0', '#29b6f6', '#4caf50']),
            text=['Ataque Incendiario', 'CAM', 'WAM', 'RML', 'CMPC', 'Rutas', 'Contulmo'],
            textposition="bottom center",
            textfont=dict(color='#ffffff')
        )])
        fig_net.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0, r=0, t=10, b=0), xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        st.plotly_chart(fig_net, use_container_width=True)
