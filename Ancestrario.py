import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# ======================================================================================================================
# Visor de Territorios Formalizados (Ancestrario)
# 26-06-2025
# Desarrollado por: Ing. Topográfico Luis Miguel Guerrero
# Contacto: luis.guerrero@ant.gov.co
#
# Este script de Streamlit permite la visualización y consulta de territorios formalizados en Colombia.
# Los datos provienen de la Agencia Nacional de Tierras (ANT).
#
# Funcionalidades principales:
# 1. Carga y procesamiento de datos geográficos (Shapefile) desde un archivo ZIP (ahora con soporte para URL).
# 2. Interfaz de usuario interactiva para filtrar territorios por ID, Nombre, Tipo, Departamento y Municipio.
# 3. Visualización de los territorios filtrados en un mapa interactivo (Folium) con tooltip mejorado y leyenda.
# 4. Presentación de datos tabulares y estadísticas de los resultados de la consulta, incluyendo nuevos atributos.
# 5. Opciones para exportar los resultados (CSV, Shapefile ZIP, HTML del mapa).
# ======================================================================================================================

# --- Estilo visual de la aplicación ---
st.set_page_config(page_title="Ancestrario", layout="wide")
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #1b2e1b;
        color: white;
    }
    .stButton>button {
        background-color: #346b34;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- Título y banner principal ---
st.title("📜 Visor de Territorios Formalizados")
st.markdown("Consulta local de territorios por ID o Nombre. Fuente: ANT")

# Mostrar banner/logo principal
st.image("Ancestrario.png", use_container_width=True)

# --- Función para cargar shapefile desde ZIP (ahora soporta URL) ---
@st.cache_data
def cargar_shapefile_desde_zip(zip_source):
    """
    Carga un archivo shapefile contenido dentro de un archivo ZIP.
    Puede aceptar una ruta de archivo local o una URL.
    Extrae el contenido del ZIP a un directorio temporal y lee el .shp.
    Retorna un GeoDataFrame en CRS EPSG:4326.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        if zip_source.startswith("http"):
            # Descargar el archivo ZIP desde la URL
            try:
                response = requests.get(zip_source, stream=True)
                response.raise_for_status()
                zip_content = BytesIO(response.content)
                zip_ref = zipfile.ZipFile(zip_content, "r")
            except requests.exceptions.RequestException as e:
                st.error(f"Error al descargar el archivo ZIP: {e}")
                st.stop()
        else:
            # Abrir archivo ZIP local
            zip_ref = zipfile.ZipFile(zip_source, "r")

        with zip_ref as zf:
            zf.extractall(tmpdir)
            shp_paths = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shp_paths:
                st.error("No se encontró ningún archivo .shp dentro del ZIP.")
                st.stop()
            shp_path = shp_paths[0]
            return gpd.read_file(shp_path).to_crs(epsg=4326)

# --- Cargar shapefile principal de territorios formalizados ---
ruta_formalizado = "https://github.com/lmiguerrero/Ancestrario/raw/main/Formalizados.zip"
gdf = cargar_shapefile_desde_zip(ruta_formalizado)

for col in gdf.columns:
    if isinstance(gdf[col].iloc[0], pd.Timestamp):
        gdf[col] = gdf[col].astype(str)

# --- Fondo de mapa disponible ---
fondos_disponibles = {
    "OpenStreetMap": "OpenStreetMap",
    "CartoDB Claro (Positron)": "CartoDB positron",
    "CartoDB Oscuro": "CartoDB dark_matter",
    "Satélite (Esri)": "Esri.WorldImagery",
    "Esri NatGeo World Map": "Esri.NatGeoWorldMap",
    "Esri World Topo Map": "Esri.WorldTopoMap"
}

# --- Mostrar logo institucional en la barra lateral ---
logo = Image.open("logo_ant.jpg")
st.sidebar.image(logo, use_container_width=True)

# --- Pestañas de la aplicación ---
tab1 = st.tabs(["🔍 Consulta por filtros"])[0]

# ===============================
# PESTAÑA 1: CONSULTA POR FILTROS
# ===============================
with tab1:
    st.sidebar.header("🔎 Filtros de búsqueda")

    id_input = st.sidebar.text_input("Buscar por ID (ID_ANT):")
    nombre_input = st.sidebar.selectbox("Buscar por Nombre (NOMBRE):", options=[""] + sorted(gdf['NOMBRE'].dropna().unique()))
    tipo_sel = st.sidebar.multiselect("Filtrar por tipo (Tipo)", sorted(gdf["Tipo"].dropna().unique()))
    depto_sel = st.sidebar.multiselect("Filtrar por departamento", sorted(gdf["DEPARTAMEN"].dropna().unique()))
    mpio_sel = st.sidebar.multiselect("Filtrar por municipio", sorted(gdf["MUNICIPIO"].dropna().unique()))

    fondo_seleccionado = st.sidebar.selectbox("🗺️ Fondo del mapa", list(fondos_disponibles.keys()), index=1)

    # --- Nueva opción para el estilo de visualización del polígono ---
    visualizacion_poligono = st.sidebar.radio(
        "🎨 Estilo de Visualización del Polígono",
        ("Con Relleno", "Solo Contorno"),
        index=0 # Por defecto: "Con Relleno"
    )

    if "mostrar_mapa" not in st.session_state:
        st.session_state["mostrar_mapa"] = False

    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("🧭 Mostrar mapa"):
            st.session_state["mostrar_mapa"] = True
    with col2:
        if st.button("🔄 Reiniciar visor"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    with col3:
        exportar_html = st.button("💾 Exportar HTML")

    # Filtros
    gdf_filtrado = gdf.copy()
    if id_input:
        gdf_filtrado = gdf_filtrado[gdf_filtrado["ID_ANT"].astype(str).str.contains(id_input)]
    if nombre_input:
        gdf_filtrado = gdf_filtrado[gdf_filtrado["NOMBRE"] == nombre_input]
    if tipo_sel:
        gdf_filtrado = gdf_filtrado[gdf_filtrado["Tipo"].isin(tipo_sel)]
    if depto_sel:
        gdf_filtrado = gdf_filtrado[gdf_filtrado["DEPARTAMEN"].isin(depto_sel)]
    if mpio_sel:
        gdf_filtrado = gdf_filtrado[gdf_filtrado["MUNICIPIO"].isin(mpio_sel)]

    if st.session_state["mostrar_mapa"] and len(gdf_filtrado) == 1:
        nombre_unico = gdf_filtrado["NOMBRE"].iloc[0]
        st.markdown(
            f"<div style='background-color:#ffffff11; padding:10px; border-radius:10px; font-size:18px; "
            f"color:white; text-align:center; font-weight:bold;'>📂 Territorio consultado: {nombre_unico}</div>",
            unsafe_allow_html=True
        )

    if st.session_state["mostrar_mapa"]:
        if not gdf_filtrado.empty:
            st.subheader("🗺️ Resultado geográfico")

            bounds = gdf_filtrado.total_bounds
            center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
            m = folium.Map(location=center, zoom_start=10, tiles=fondos_disponibles[fondo_seleccionado])

            # Función para aplicar estilos a los polígonos según el tipo y la opción de visualización
            def estilo_tipo(x, viz_option):
                tipo = x["properties"]["Tipo"].strip().lower()
                base_fill_color = "#228B22" if "indigena" in tipo else "#8B4513" # Verde para indígena, marrón para otros
                base_color = "#228B22" if "indigena" in tipo else "#8B4513" # Color del borde

                # Ajusta la opacidad del relleno según la opción seleccionada
                fill_opacity = 0.5 if viz_option == "Con Relleno" else 0

                return {
                    "fillColor": base_fill_color,
                    "color": base_color,
                    "weight": 2,
                    "fillOpacity": fill_opacity
                }

            folium.GeoJson(
                gdf_filtrado,
                tooltip=folium.GeoJsonTooltip(
                    fields=["ID_ANT", "NOMBRE", "DEPARTAMEN", "MUNICIPIO", "Tipo", "AREA_TOTAL", "Recons"],
                    aliases=["ID:", "Nombre:", "Departamento:", "Municipio:", "Tipo:", "Área total (ha):", "Reconstruido:"]
                ),
                # Pasa la opción de visualización a la función de estilo
                style_function=lambda x: estilo_tipo(x, visualizacion_poligono)
            ).add_to(m)

            # --- Añadir Leyenda al mapa ---
            legend_html = """
                <div style="
                    position: fixed;
                    bottom: 50px;
                    left: 50px;
                    width: 180px;
                    height: 90px;
                    background-color: white;
                    border:2px solid grey;
                    z-index:9999;
                    font-size:14px;
                    padding:10px;
                    border-radius: 8px;
                    color: black; /* Texto negro para contraste */
                ">
                    <b>Leyenda de Territorios</b><br>
                    <i style="background:#228B22; opacity:0.7; width:18px; height:18px; float:left; margin-right:8px; border:1px solid #228B22;"></i> Resguardo Indígena<br>
                    <i style="background:#8B4513; opacity:0.7; width:18px; height:18px; float:left; margin-right:8px; border:1px solid #8B4513;"></i> Consejo Comunitario<br>
                </div>
                """
            m.get_root().html.add_child(folium.Element(legend_html))


            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            st_folium(m, width=1200, height=600)

            st.subheader("📋 Datos encontrados")
            st.dataframe(gdf_filtrado.drop(columns="geometry"))

            # Estadísticas
            total_comunidades = len(gdf_filtrado)
            area_total = gdf_filtrado["AREA_TOTAL"].sum()
            hectareas = int(area_total)
            metros2 = int(round((area_total - hectareas) * 10000))
            tipo_normalizado = gdf_filtrado["Tipo"].str.lower().str.strip()
            cuenta_indigena = tipo_normalizado.str.contains("indigena").sum()
            cuenta_consejo = tipo_normalizado.str.contains("comunitario").sum()

            st.markdown(
                f"""
                <div style='
                    margin-top: 1em;
                    padding: 0.7em;
                    background-color: #264d26;
                    border-radius: 8px;
                    font-size: 16px;
                    color: white;'>
                    <strong>📊 Estadísticas del resultado:</strong><br>
                    Territorios filtrados: <strong>{total_comunidades}</strong><br>
                    ▸ Comunidades indígenas: <strong>{cuenta_indigena}</strong><br>
                    ▸ Consejos comunitarios: <strong>{cuenta_consejo}</strong><br>
                    Área total: <strong>{hectareas} ha + {metros2} m²</strong>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Exportar
            csv = gdf_filtrado.drop(columns="geometry").to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv, file_name="resultados_formalizados.csv", mime="text/csv")

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "shapefile_filtrado.zip")
                shp_base = os.path.join(tmpdir, "shapefile_filtrado")
                gdf_filtrado.to_file(shp_base + ".shp", driver="ESRI Shapefile", encoding="utf-8")
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                        fpath = shp_base + ext
                        if os.path.exists(fpath):
                            zipf.write(fpath, arcname="shapefile_filtrado" + ext)
                with open(zip_path, "rb") as f:
                    st.download_button("⬇️ Descargar SHP filtrado (.zip)", data=f, file_name="shapefile_filtrado.zip", mime="application/zip")

            if exportar_html:
                with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmpfile:
                    m.save(tmpfile.name)
                    st.success("✅ Mapa exportado correctamente.")
                    with open(tmpfile.name, "rb") as f:
                        st.download_button("⬇️ Descargar HTML del mapa", data=f, file_name="mapa_formalizado.html", mime="text/html")

        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados.")

# --- Derechos de autor ---
st.markdown("""
<hr style='border-top: 1px solid #444;'>
<div style='text-align: center; font-size: 14px; color: gray; padding-top: 10px;'>
    Realizado por <strong>Ing. Topográfico Luis Miguel Guerrero</strong> —
    <a href="mailto:luis.guerrero@ant.gov.co" style="color:gray;">luis.guerrero@ant.gov.co</a><br>
    <em>© Derechos reservados</em>
</div>
""", unsafe_allow_html=True)
