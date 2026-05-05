import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# 1. Configuracion de pagina (Bunker mode)
st.set_page_config(page_title="War Room CMPC", page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")

# 2. Credenciales Supabase
URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

# 3. Extracción de Inteligencia (Caché para velocidad)
@st.cache_data(ttl=600)
def load_data():
    supabase: Client = create_client(URL, API_KEY)
    response = supabase.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(response.data)
    
    # Unificar los distintos formatos de fecha al vuelo
    if not df.empty and 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.sort_values(by='fecha', ascending=False)
        
    return df

df = load_data()

# 4. Interfaz UI
st.title("🛡️ C5I - Sistema de Inteligencia Táctica")
st.markdown("---")

if df.empty:
    st.warning("La bóveda está esperando datos.")
else:
    # --- KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Alertas Registradas", len(df))
    
    # Logica de clasificacion estricta CMPC
    df_cmpc = df[df['titular'].str.contains('CMPC|Mininco', case=False, na=False) | 
                 df['actor'].str.contains('CMPC|Mininco', case=False, na=False) |
                 df['resumen_ia'].str.contains('CMPC|Mininco', case=False, na=False)]
    col2.metric("Alertas Críticas (Infraestructura Propia)", len(df_cmpc))
    
    ultima_fecha = df['fecha'].iloc[0].strftime("%d/%m/%Y") if pd.notnull(df['fecha'].iloc[0]) else "Desconocida"
    col3.metric("Última Alerta Procesada", ultima_fecha)

    # --- Mapa Táctico ---
    st.subheader("📍 Mapa de Riesgo Operacional")
    
    df_mapa = df.dropna(subset=['latitud', 'longitud'])
    if not df_mapa.empty:
        # Forzar color rojo para CMPC y naranja para el resto
        def get_color(row):
            texto_analisis = str(row['titular']).upper() + " " + str(row['resumen_ia']).upper() + " " + str(row['actor']).upper()
            if 'CMPC' in texto_analisis or 'MININCO' in texto_analisis:
                return 'Crítico (CMPC)'
            elif row['puntaje_riesgo'] >= 6:
                return 'Alto'
            else:
                return 'Medio'
                
        df_mapa['Nivel de Amenaza'] = df_mapa.apply(get_color, axis=1)
        
        fig = px.scatter_mapbox(
            df_mapa, 
            lat="latitud", 
            lon="longitud", 
            hover_name="titular",
            hover_data={"fecha": True, "actor": True, "ubicacion": True, "Nivel de Amenaza": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza",
            color_discrete_map={'Crítico (CMPC)': 'red', 'Alto': 'orange', 'Medio': '#e0e000'},
            zoom=6.5, 
            height=550
        )
        fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
        
    # --- Tabla de Datos ---
    st.subheader("📋 Registro Histórico")
    df_mostrar = df[['fecha', 'titular', 'actor', 'ubicacion', 'puntaje_riesgo', 'enlace_noticia']].copy()
    st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
