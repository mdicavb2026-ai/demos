import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE PANTALLA ---
st.set_page_config(page_title="War Room CMPC", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

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
        df = df.dropna(subset=['fecha_orden']).copy()
        df = df.sort_values(by='fecha_orden', ascending=False)
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y %H:%M')
        
        # Respaldo de seguridad visual (El motor real de Python ya hace esto, esto es solo para colorear el dashboard)
        df['Nivel de Amenaza'] = df['nivel_alerta'].fillna('BAJO').str.upper()
        df['Magnitud'] = df['puntaje_riesgo'].apply(lambda x: float(x) if pd.notnull(x) and float(x) > 0 else 1.0)
    else:
        df = pd.DataFrame()
    return df

df_base = load_data()

if df_base.empty:
    st.warning("El Búnker está esperando la inyección de datos del Motor Python.")
    st.stop()

# --- PANEL LATERAL (FILTROS) ---
st.sidebar.markdown("# 🛡️ WAR ROOM CMPC")
st.sidebar.markdown("## ⚙️ Centro de Comando")

fecha_min = df_base['fecha_orden'].min().date()
fecha_max = df_base['fecha_orden'].max().date()
rango_fechas = st.sidebar.date_input("Filtrar por Ventana Temporal", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

niveles_disponibles = df_base['Nivel de Amenaza'].unique().tolist()
filtro_nivel = st.sidebar.multiselect("Nivel de Alerta", niveles_disponibles, default=niveles_disponibles)

df_filtrado = df_base[df_base['Nivel de Amenaza'].isin(filtro_nivel)]
if len(rango_fechas) == 2:
    df_filtrado = df_filtrado[(df_filtrado['fecha_orden'].dt.date >= rango_fechas[0]) & (df_filtrado['fecha_orden'].dt.date <= rango_fechas[1])]

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Sistema de Inteligencia y Prospectiva C5I")

# KPIs Ejecutivos
c1, c2, c3, c4 = st.columns(4)
c1.metric("Alertas en Rango", len(df_filtrado))
c2.metric("Incidentes Críticos", len(df_filtrado[df_filtrado['Nivel de Amenaza'] == 'CRÍTICO']))
c3.metric("Incidentes Altos", len(df_filtrado[df_filtrado['Nivel de Amenaza'] == 'ALTO']))
c4.metric("Última Alerta", df_filtrado['fecha_mostrar'].iloc[0] if not df_filtrado.empty else "N/A")

st.markdown("---")

# MÓDULOS 7 y 8: MAPA Y PROSPECTIVA
col_mapa, col_grafico = st.columns([5, 5])
colores_tacticos = {'CRÍTICO': '#FF1744', 'ALTO': '#FF9100', 'MEDIO': '#29B6F6', 'BAJO': '#4CAF50'}

with col_mapa:
    st.markdown("#### 📍 Despliegue Táctico Territorial")
    df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud']).copy()
    if not df_mapa.empty:
        fig_mapa = px.scatter_mapbox(
            df_mapa, lat="latitud", lon="longitud", hover_name="titular",
            hover_data={"fecha_mostrar": False, "actor": False, "ubicacion": False, "Nivel de Amenaza": False, "Magnitud": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza", size="Magnitud", size_max=16,
            color_discrete_map=colores_tacticos, zoom=6.0, height=500
        )
        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0},
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=14)
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

with col_grafico:
    st.markdown("#### 📊 Prospectiva: Distribución de Riesgo")
    if not df_filtrado.empty:
        conteo_riesgo = df_filtrado['Nivel de Amenaza'].value_counts().reset_index()
        conteo_riesgo.columns = ['Nivel', 'Cantidad']
        fig_bar = px.bar(
            conteo_riesgo, x='Cantidad', y='Nivel', orientation='h', color='Nivel',
            color_discrete_map=colores_tacticos, height=220, template="plotly_dark", text='Cantidad'
        )
        fig_bar.update_layout(showlegend=False, margin={"r":10,"t":10,"l":10,"b":10}, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("#### 📈 Prospectiva: Evolución Temporal")
    if not df_filtrado.empty:
        tendencia = df_filtrado.groupby([df_filtrado['fecha_orden'].dt.to_period("D"), 'Nivel de Amenaza']).size().reset_index(name='Incidentes')
        tendencia['fecha_orden'] = tendencia['fecha_orden'].dt.to_timestamp()
        fig_line = px.line(
            tendencia, x='fecha_orden', y='Incidentes', color='Nivel de Amenaza',
            color_discrete_map=colores_tacticos, height=220, template="plotly_dark", markers=True
        )
        fig_line.update_layout(margin={"r":10,"t":10,"l":10,"b":10}, yaxis_title=None, xaxis_title=None, legend_title=None)
        st.plotly_chart(fig_line, use_container_width=True)

st.markdown("---")
with st.expander("📂 VER Y EXPORTAR REGISTRO HISTÓRICO Y ANÁLISIS IA (EXCEL/CSV)"):
    def limpiar_link(link):
        link = str(link).strip()
        if link.lower() in ['nan', 'none', '', 'null']: return None 
        if not link.startswith('http'): return "https://" + link
        return link

    df_export = df_filtrado[['fecha_mostrar', 'titular', 'resumen_ia', 'actor', 'ubicacion', 'Nivel de Amenaza', 'puntaje_riesgo', 'enlace_noticia']].copy()
    df_export['enlace_noticia'] = df_export['enlace_noticia'].apply(limpiar_link)
    
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Descargar Reporte de Inteligencia (CSV)", data=csv, file_name='reporte_inteligencia.csv', mime='text/csv')
    
    st.dataframe(
        df_export, use_container_width=True, hide_index=True, height=400,
        column_config={
            "fecha_mostrar": "Fecha",
            "titular": st.column_config.TextColumn("Titular", width="medium"),
            "resumen_ia": st.column_config.TextColumn("Análisis IA (Prospectiva)", width="large"),
            "actor": "Actor",
            "Nivel de Amenaza": "Nivel",
            "puntaje_riesgo": st.column_config.NumberColumn("Riesgo", format="%.1f"),
            "enlace_noticia": st.column_config.LinkColumn("Fuente", display_text="Ver Noticia 🔗")
        }
    )
