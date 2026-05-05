import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import re
from datetime import datetime, timedelta
import networkx as nx

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
    .kpi-box { background-color: #151b2b; padding: 15px; border-radius: 5px; border-top: 3px solid; text-align: left; }
    .kpi-title { font-size: 12px; color: #8892b0; text-transform: uppercase; }
    .kpi-value { font-size: 28px; font-weight: bold; }
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
        # FIX ZONA HORARIA: Removemos la zona horaria para que todas sean "naives" y compatibles
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

# 1. Filtro Temporal Rápido
opciones_tiempo = {"Histórico Global": 3650, "Último Año": 365, "Últimos 6 Meses": 180, "Últimos 3 Meses": 90, "Último Mes": 30, "Última Semana": 7}
seleccion_tiempo = st.sidebar.selectbox("Período Temporal", list(opciones_tiempo.keys()))
dias_restar = opciones_tiempo[seleccion_tiempo]
# Creamos la fecha límite sin zona horaria para emparejar con el df
fecha_limite = (datetime.now() - timedelta(days=dias_restar)).replace(tzinfo=None)

# Aplicar filtro de fecha
df_filtrado = df_base[df_base['fecha_orden'] >= fecha_limite]

# 2. Filtro de Orgánica (Actor)
lista_actores = ["TODAS"] + sorted([a for a in df_filtrado['actor'].unique() if str(a).lower() not in ["desconocido", "null", "none", ""]])
actor_seleccionado = st.sidebar.selectbox("Filtrar por Orgánica", lista_actores)

if actor_seleccionado != "TODAS":
    df_filtrado = df_filtrado[df_filtrado['actor'] == actor_seleccionado]

# --- HEADER GLOBAL ---
st.markdown(f"**WAR ROOM CMPC** • V9.60 | Vista: **{seleccion_tiempo.upper()}** | Eventos Procesados: **{len(df_filtrado)}**")
tab_tactico, tab_prospectiva, tab_informe = st.tabs(["🎯 TÁCTICO", "📊 PROSPECTIVA", "📥 INFORME AUTOMÁTICO"])

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
        if df_criticos.empty: st.info("No hay eventos críticos en este período.")
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
            color="Nivel de Amenaza", size="Magnitud", size_max=14,
            color_discrete_map=colores_tacticos, zoom=6.5, height=750
        )
        fig_mapa.update_layout(
            mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0},
            hoverlabel=dict(bgcolor="#1E1E1E", font_size=12), showlegend=False
        )
        st.plotly_chart(fig_mapa, use_container_width=True, config={'scrollZoom': True, 'displayModeBar': False})

    with col_der:
        st.markdown('<div class="section-title">FEED TÁCTICO GENERAL</div>', unsafe_allow_html=True)
        df_altos = df_filtrado[df_filtrado['Nivel de Amenaza'] == 'ALTO'].head(3)
        for _, row in df_altos.iterrows():
            st.markdown(generar_card_html(row, "card-alto"), unsafe_allow_html=True)
            
        st.markdown('<div class="section-title">ORGÁNICAS TERRORISTAS</div>', unsafe_allow_html=True)
        actores = df_filtrado[~df_filtrado['actor'].str.contains('Desconocido', case=False, na=False)]['actor'].value_counts().reset_index()
        actores.columns = ['Organización', 'Eventos']
        st.dataframe(actores.head(6), hide_index=True, use_container_width=True)
        
        st.markdown('<div class="section-title">TRENDING KEYWORDS (BIGRAMAS)</div>', unsafe_allow_html=True)
        titulares_unidos = " ".join(df_filtrado['palabra_clave'].dropna().tolist() + df_filtrado['titular'].dropna().tolist()).lower()
        palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', titulares_unidos)
        ruido = ['para', 'como', 'sobre', 'entre', 'desde', 'hasta', 'este', 'esta', 'pero', 'sean']
        palabras_utiles = [p for p in palabras if p not in ruido]
        
        bigramas = [f"{palabras_utiles[i]} {palabras_utiles[i+1]}" for i in range(len(palabras_utiles)-1)]
        conteo_bigramas = Counter(bigramas).most_common(12)
        
        nube_html = "<div style='padding:15px; background-color:#151b2b; border-radius:5px; display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:10px;'>"
        if conteo_bigramas:
            max_val = conteo_bigramas[0][1]
            for frase, freq in conteo_bigramas:
                size = max(12, int((freq / max_val) * 24))
                nube_html += f"<span style='color:#4fc3f7; font-size:{size}px; font-weight:bold;'>#{frase.title().replace(' ', '')}</span>"
        else:
            nube_html += "<span style='color:#8892b0;'>Sin datos suficientes</span>"
        nube_html += "</div>"
        st.markdown(nube_html, unsafe_allow_html=True)

# ==========================================
# PESTAÑA 2: PROSPECTIVA
# ==========================================
with tab_prospectiva:
    st.markdown("### INTELIGENCIA PROSPECTIVA OSINT", unsafe_allow_html=True)
    
    k1, k2, k3, k4 = st.columns(4)
    ataques_predio = len(df_filtrado[df_filtrado['titular'].str.contains('predio|fundo', case=False, na=False)])
    k1.markdown(f"""<div class="kpi-box" style="border-color:#4caf50;"><div class="kpi-title">🌲 EVENTOS PREDIALES</div><div class="kpi-value" style="color:#4caf50;">{ataques_predio}</div></div>""", unsafe_allow_html=True)
    k2.markdown("""<div class="kpi-box" style="border-color:#ff1744;"><div class="kpi-title">👤 VECTOR CONTRA PERSONAL</div><div class="kpi-value" style="color:#ff1744;">N/A</div></div>""", unsafe_allow_html=True)
    k3.markdown("""<div class="kpi-box" style="border-color:#ba68c8;"><div class="kpi-title">🚜 VECTOR MAQUINARIA</div><div class="kpi-value" style="color:#ba68c8;">N/A</div></div>""", unsafe_allow_html=True)
    k4.markdown("""<div class="kpi-box" style="border-color:#ffb300;"><div class="kpi-title">🏭 VECTOR PLANTAS</div><div class="kpi-value" style="color:#ffb300;">N/A</div></div>""", unsafe_allow_html=True)
    
    st.write("")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown('<div class="section-title">DISTRIBUCIÓN POR MACROZONA</div>', unsafe_allow_html=True)
        if not df_filtrado.empty:
            conteo_zona = df_filtrado['ubicacion'].value_counts().reset_index().head(6)
            conteo_zona.columns = ['Zona', 'Ataques']
            # Paleta de colores más variada para no saturar
            fig_bar = px.bar(conteo_zona, x='Zona', y='Ataques', color='Zona', color_discrete_sequence=['#ff1744', '#ff9100', '#ffd54f', '#4fc3f7', '#29b6f6', '#4caf50'])
            fig_bar.update_layout(template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_g2:
        st.markdown('<div class="section-title">SOCIOGRAMA TÁCTICO (ANÁLISIS DE VÍNCULOS REAL)</div>', unsafe_allow_html=True)
        if not df_filtrado.empty:
            # Construcción del grafo de red dinámico
            G = nx.Graph()
            node_sizes = {}
            
            for _, row in df_filtrado.iterrows():
                actor = str(row.get('actor', '')).strip()
                ubi = str(row.get('ubicacion', '')).strip()
                if not actor or actor.lower() in ['desconocido', 'none']: continue
                if not ubi or ubi.lower() in ['macrozona sur', 'none']: continue
                
                # Frecuencias para el tamaño
                node_sizes[actor] = node_sizes.get(actor, 0) + 1
                node_sizes[ubi] = node_sizes.get(ubi, 0) + 1
                
                # Añadir conexión (línea)
                if G.has_edge(actor, ubi):
                    G[actor][ubi]['weight'] += 1
                else:
                    G.add_edge(actor, ubi, weight=1)
            
            if G.nodes():
                pos = nx.spring_layout(G, k=0.8, iterations=50) # Coordenadas matemáticas
                
                # Dibujar las líneas
                edge_x, edge_y = [], []
                for edge in G.edges():
                    x0, y0 = pos[edge[0]]
                    x1, y1 = pos[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.8, color='#8892b0'), hoverinfo='none', mode='lines')
                
                # Dibujar los nodos
                node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
                for node in G.nodes():
                    x, y = pos[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node)
                    # Tamaño dinámico basado en ataques reales
                    node_size.append(min(15 + (node_sizes[node] * 4), 60)) 
                    # Orgánicas en rojo, Ubicaciones en azul
                    node_color.append('#ff1744' if node in df_filtrado['actor'].unique() else '#4fc3f7')

                node_trace = go.Scatter(
                    x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="bottom center",
                    hoverinfo='text', marker=dict(size=node_size, color=node_color, line=dict(width=2, color='#ffffff'))
                )
                
                fig_net = go.Figure(data=[edge_trace, node_trace])
                fig_net.update_layout(
                    template="plotly_dark", plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    margin=dict(l=0, r=0, t=10, b=0), height=350, showlegend=False
                )
                st.plotly_chart(fig_net, use_container_width=True)
            else:
                st.info("No hay suficientes vínculos (Actor -> Ubicación) para trazar la red.")

# ==========================================
# PESTAÑA 3: INFORME AUTOMÁTICO
# ==========================================
with tab_informe:
    st.markdown("### 📥 GENERADOR DE INFORMES C5I")
    
    def limpiar_link(link):
        link = str(link).strip()
        if link.lower() in ['nan', 'none', '', 'null']: return None 
        if not link.startswith('http'): return "https://" + link
        return link

    df_export = df_filtrado[['fecha_mostrar', 'titular', 'actor', 'accion_digital', 'ubicacion', 'Nivel de Amenaza', 'resumen_ia', 'enlace_noticia']].copy()
    df_export['enlace_noticia'] = df_export['enlace_noticia'].apply(limpiar_link)
    
    csv = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig') 
    
    st.download_button(
        label="📥 DESCARGAR MATRIZ CSV (APTO PARA EXCEL)",
        data=csv,
        file_name=f'Reporte_C5I_CMPC_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv',
    )
    
    st.dataframe(
        df_export, use_container_width=True, hide_index=True, height=500,
        column_config={
            "fecha_mostrar": "Fecha",
            "titular": st.column_config.TextColumn("Titular", width="medium"),
            "actor": "Actor / Orgánica",
            "accion_digital": "Táctica",
            "Nivel de Amenaza": "Nivel",
            "resumen_ia": st.column_config.TextColumn("Prospectiva", width="large"),
            "enlace_noticia": st.column_config.LinkColumn("Fuente", display_text="Ver Noticia 🔗")
        }
    )
