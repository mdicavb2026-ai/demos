import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px

# 1. Configuracion de pagina (Modo Pantalla Completa Oscura)
st.set_page_config(page_title="War Room CMPC", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

# 2. Credenciales Supabase
URL = "https://wffttolclywvofzakmfd.supabase.co"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmZnR0b2xjbHl3dm9memFrbWZkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc5MjMyOTksImV4cCI6MjA5MzQ5OTI5OX0.8vzHsEjPvZBf49VMCl1G8PtFYXLoxYSrzhbrYIBNEcU"

# 3. Extracción y Limpieza de Inteligencia
@st.cache_data(ttl=600)
def load_data():
    supabase: Client = create_client(URL, API_KEY)
    response = supabase.table("inteligencia_tactica").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty and 'fecha' in df.columns:
        df['fecha_orden'] = pd.to_datetime(df['fecha'], errors='coerce')
        df = df.dropna(subset=['fecha_orden']).copy() # Filtrar fechas corruptas
        df = df.sort_values(by='fecha_orden', ascending=False)
        df['fecha_mostrar'] = df['fecha_orden'].dt.strftime('%d/%m/%Y')
        
        # Asignación de Nivel de Amenaza Integrado
        def clasificar_riesgo(row):
            texto_analisis = str(row.get('titular', '')).upper() + " " + str(row.get('resumen_ia', '')).upper() + " " + str(row.get('actor', '')).upper()
            try:
                riesgo = float(row.get('puntaje_riesgo', 1.0))
            except:
                riesgo = 1.0
            if 'CMPC' in texto_analisis or 'MININCO' in texto_analisis:
                return 'Crítico'
            elif riesgo >= 6:
                return 'Alto'
            else:
                return 'Medio'
        
        df['Nivel de Amenaza'] = df.apply(clasificar_riesgo, axis=1)
        df['Magnitud'] = df['puntaje_riesgo'].apply(lambda x: float(x) if pd.notnull(x) and float(x) > 0 else 1.0)
    else:
        df = pd.DataFrame()
    return df

df_base = load_data()

if df_base.empty:
    st.warning("La bóveda está esperando datos o hay un error en las fechas.")
    st.stop()

# 4. FILTROS TÁCTICOS (Panel Lateral)
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/CMPC_logo.svg/1200px-CMPC_logo.svg.png", width=150)
st.sidebar.markdown("## ⚙️ Centro de Comando")

# Filtro de Fechas
fecha_min = df_base['fecha_orden'].min().date()
fecha_max = df_base['fecha_orden'].max().date()
rango_fechas = st.sidebar.date_input("Filtrar por Ventana Temporal", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

# Filtro de Amenaza
niveles_disponibles = df_base['Nivel de Amenaza'].unique().tolist()
filtro_nivel = st.sidebar.multiselect("Nivel de Alerta", niveles_disponibles, default=niveles_disponibles)

# Aplicar Filtros
df_filtrado = df_base[df_base['Nivel de Amenaza'].isin(filtro_nivel)]
if len(rango_fechas) == 2:
    df_filtrado = df_filtrado[(df_filtrado['fecha_orden'].dt.date >= rango_fechas[0]) & (df_filtrado['fecha_orden'].dt.date <= rango_fechas[1])]

# 5. INTERFAZ UI - WAR ROOM
st.title("🛡️ Sistema de Inteligencia y Prospectiva C5I")

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
c1.metric("Alertas en Rango", len(df_filtrado))
c2.metric("Incidentes Críticos", len(df_filtrado[df_filtrado['Nivel de Amenaza'] == 'Crítico']))
c3.metric("Incidentes Altos", len(df_filtrado[df_filtrado['Nivel de Amenaza'] == 'Alto']))
c4.metric("Última Alerta", df_filtrado['fecha_mostrar'].iloc[0] if not df_filtrado.empty else "N/A")

st.markdown("---")

# --- MAPA Y GRÁFICO PRINCIPAL ---
col_mapa, col_grafico = st.columns([6, 4]) # 60% Mapa, 40% Gráfico

with col_mapa:
    st.markdown("#### 📍 Despliegue Táctico Territorial")
    df_mapa = df_filtrado.dropna(subset=['latitud', 'longitud']).copy()
    if not df_mapa.empty:
        fig_mapa = px.scatter_mapbox(
            df_mapa, lat="latitud", lon="longitud", hover_name="titular",
            hover_data={"fecha_mostrar": True, "actor": True, "Nivel de Amenaza": False, "Magnitud": False, "latitud": False, "longitud": False},
            color="Nivel de Amenaza", size="Magnitud", size_max=18,
            color_discrete_map={'Crítico': '#ff0000', 'Alto': '#ff8800', 'Medio': '#e0e000'},
            zoom=6.2, height=500
        )
        fig_mapa.update_layout(mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0})
        # AQUÍ ESTÁ LA MAGIA DEL ZOOM: config={'scrollZoom': True}
        st.plotly_chart(fig_mapa, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

with col_grafico:
    st.markdown("#### 📊 Distribución de Riesgo")
    if not df_filtrado.empty:
        conteo_riesgo = df_filtrado['Nivel de Amenaza'].value_counts().reset_index()
        conteo_riesgo.columns = ['Nivel', 'Cantidad']
        fig_bar = px.bar(
            conteo_riesgo, x='Cantidad', y='Nivel', orientation='h', color='Nivel',
            color_discrete_map={'Crítico': '#ff0000', 'Alto': '#ff8800', 'Medio': '#e0e000'},
            height=240, template="plotly_dark"
        )
        fig_bar.update_layout(showlegend=False, margin={"r":10,"t":10,"l":10,"b":10}, yaxis_title=None, xaxis_title=None)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("#### 📈 Evolución Temporal de Amenazas")
    if not df_filtrado.empty:
        tendencia = df_filtrado.groupby([df_filtrado['fecha_orden'].dt.to_period("M"), 'Nivel de Amenaza']).size().reset_index(name='Incidentes')
        tendencia['fecha_orden'] = tendencia['fecha_orden'].dt.to_timestamp()
        fig_line = px.line(
            tendencia, x='fecha_orden', y='Incidentes', color='Nivel de Amenaza',
            color_discrete_map={'Crítico': '#ff0000', 'Alto': '#ff8800', 'Medio': '#e0e000'},
            height=240, template="plotly_dark"
        )
        fig_line.update_layout(margin={"r":10,"t":10,"l":10,"b":10}, yaxis_title=None, xaxis_title=None, legend_title=None)
        st.plotly_chart(fig_line, use_container_width=True)

# --- REPORTE Y DESCARGA (Oculto en un panel expandible) ---
st.markdown("---")
with st.expander("📂 VER Y EXPORTAR REGISTRO HISTÓRICO COMPLETO"):
    
    def limpiar_link(link):
        link = str(link).strip()
        if link.lower() in ['nan', 'none', '', 'null']: return None 
        if not link.startswith('http'): return "https://" + link
        return link

    df_export = df_filtrado[['fecha_mostrar', 'titular', 'actor', 'ubicacion', 'Nivel de Amenaza', 'puntaje_riesgo', 'enlace_noticia']].copy()
    df_export['enlace_noticia'] = df_export['enlace_noticia'].apply(limpiar_link)
    
    # Botón de Descarga
    csv = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte Filtrado (CSV para Excel)",
        data=csv,
        file_name='reporte_inteligencia.csv',
        mime='text/csv',
    )
    
    # Tabla visual pulida
    st.dataframe(
        df_export, 
        use_container_width=True, hide_index=True, height=300,
        column_config={
            "fecha_mostrar": "Fecha",
            "titular": st.column_config.TextColumn("Titular", width="large"),
            "actor": "Actor",
            "Nivel de Amenaza": "Clasificación",
            "puntaje_riesgo": st.column_config.NumberColumn("Riesgo", format="%.1f"),
            "enlace_noticia": st.column_config.LinkColumn("Fuente", display_text="Ver Noticia 🔗")
        }
    )
