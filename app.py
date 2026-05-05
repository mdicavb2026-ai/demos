import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import numpy as np

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
    
    if not df.empty and 'fecha' in df.columns:
        # Convertir a fecha para ordenar, pero guardando una copia limpia para mostrar
        df['fecha_orden'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.sort_values(by='fecha_orden', ascending=False)
        # Crear una columna de fecha en formato DD/MM/YYYY, y si es nula, poner "Sin registro"
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y').fillna('Sin registro')
    else:
        df['fecha_mostrar'] = 'Sin registro'
        
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
    
    # Buscar la última fecha válida para el KPI
    fechas_validas = df[df['fecha_mostrar'] != 'Sin registro']['fecha_mostrar']
    ultima_fecha = fechas_validas.iloc[0] if not fechas_validas.empty else "Desconocida"
    col3.metric("Última Alerta Procesada", ultima_fecha)

    # --- Mapa Táctico ---
    st.subheader("📍 Mapa de Riesgo Operacional")
    
    df_mapa = df.dropna(subset=['latitud', 'longitud']).copy()
    if not df_mapa.empty:
        def get_color(row):
            texto_analisis = str(row.get('titular', '')).upper() + " " + str(row.get('resumen_ia', '')).upper() + " " + str(row.get('actor', '')).upper()
            try:
                riesgo = float(row.get('puntaje_riesgo', 1.0))
            except (ValueError, TypeError):
                riesgo = 1.0
                
            if 'CMPC' in texto_analisis or 'MININCO' in texto_analisis:
                return 'Crítico'
            elif riesgo >= 6:
                return 'Alto'
            else:
                return 'Medio'
                
        df_mapa['Nivel de Amenaza'] = df_mapa.apply(get_color, axis=1)
        
        fig = px.scatter_mapbox(
            df_mapa, 
            lat="latitud", 
            lon="longitud", 
            hover_name="titular",
            hover_data={"fecha_mostrar": True, "actor": True, "ubicacion": True, "Nivel de Amenaza": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza",
            color_discrete_map={'Crítico': 'red', 'Alto': 'orange', 'Medio': '#e0e000'},
            zoom=6.5, 
            height=550
        )
        fig.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
        
    # --- Tabla de Datos (Diseño Pulido) ---
    st.subheader("📋 Registro Histórico")
    
    # Preparar datos limpios para la tabla
    df_mostrar = df[['fecha_mostrar', 'titular', 'actor', 'ubicacion', 'puntaje_riesgo', 'enlace_noticia']].copy()
    
    # Limpiar los links vacíos o que dicen "nan" desde Excel
    df_mostrar['enlace_noticia'] = df_mostrar['enlace_noticia'].fillna("").astype(str)
    df_mostrar['enlace_noticia'] = df_mostrar['enlace_noticia'].replace({'nan': '', 'None': ''})
    # Asegurar que si hay link, empiece con http para que no se rompa el click
    df_mostrar['enlace_noticia'] = df_mostrar['enlace_noticia'].apply(lambda x: x if x == "" or str(x).startswith("http") else "https://" + str(x))

    # Renderizar tabla con configuración visual de columnas
    st.dataframe(
        df_mostrar, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "fecha_mostrar": st.column_config.TextColumn("Fecha", width="small"),
            "titular": st.column_config.TextColumn("Titular de la Alerta", width="large"),
            "actor": st.column_config.TextColumn("Actor / Entidad"),
            "ubicacion": st.column_config.TextColumn("Ubicación"),
            "puntaje_riesgo": st.column_config.NumberColumn("Riesgo", format="%.1f", width="small"),
            "enlace_noticia": st.column_config.LinkColumn("Fuente", display_text="Ver Noticia 🔗", width="small")
        }
    )
