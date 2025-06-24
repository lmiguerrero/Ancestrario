import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile
import pandas as pd
from PIL import Image

# ======================================================================================================================
# Visor de Territorios Formalizados (Ancestrario)
#
# Desarrollado por: Ing. Topográfico Luis Miguel Guerrero
# Contacto: luis.guerrero@ant.gov.co
# Actualizado: 24 6 2025
#
# Este script de Streamlit permite la visualización y consulta de territorios formalizados en Colombia.
# Los datos provienen de la Agencia Nacional de Tierras (ANT).
#
# Funcionalidades principales:
# 1. Carga y procesamiento de datos geográficos (Shapefile) desde un archivo ZIP.
# 2. Interfaz de usuario interactiva para filtrar territorios por ID, Nombre, Tipo, Departamento y Municipio.
# 3. Visualización de los territorios filtrados en un mapa interactivo (Folium).
# 4. Presentación de datos tabulares y estadísticas de los resultados de la consulta.
# 5. Opciones para exportar los resultados (CSV, Shapefile ZIP, HTML del mapa).
# ======================================================================================================================

# --- Estilo visual de la aplicación ---
st.set_page_config(page_title="Ancestrario", layout="wide") # Configura el título de la página y el diseño.
st.markdown("""
    <style>
    html, body, .stApp {
        background-color: #1b2e1b; /* Color de fondo oscuro */
        color: white; /* Color de texto principal */
    }
    .stButton>button {
        background-color: #346b34; /* Color de fondo para botones */
        color: white; /* Color de texto para botones */
    }
    </style>
""", unsafe_allow_html=True) # Aplica estilos CSS personalizados.

# --- Título y banner principal ---
st.title("📜 Visor de Territorios Formalizados")
st.markdown("Consulta local de territorios por ID o Nombre. Fuente: ANT")

# Mostrar banner/logo principal
st.image("Ancestrario.png", use_container_width=True)

# --- Función para cargar shapefile desde ZIP ---
@st.cache_data # Cachea los datos para mejorar el rendimiento
def cargar_shapefile_desde_zip(path_zip):
    """
    Carga un archivo shapefile contenido dentro de un archivo ZIP.
    Extrae el contenido del ZIP a un directorio temporal y lee el .shp.
    Retorna un GeoDataFrame en CRS EPSG:4326.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(path_zip, "r") as zip_ref:
            zip_ref.extractall(tmpdir) # Extrae todos los archivos del ZIP al directorio temporal
            # Encuentra el archivo .shp dentro del directorio temporal
            shp_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")][0]
            return gpd.read_file(shp_path).to_crs(epsg=4326) # Lee el shapefile y lo convierte a WGS84

# --- Cargar shapefile principal de territorios formalizados ---
ruta_formalizado = "Formalizado.zip" # Ruta al archivo ZIP que contiene el shapefile
gdf = cargar_shapefile_desde_zip(ruta_formalizado)
# Convierte cualquier columna de tipo Timestamp a string para evitar errores de serialización
for col in gdf.columns:
    if isinstance(gdf[col].iloc[0], pd.Timestamp):
        gdf[col] = gdf[col].astype(str)

# --- Definición de fondos de mapa disponibles para Folium ---
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

with tab1:
    st.sidebar.header("🔎 Filtros de búsqueda")

    # Campos de entrada y selección para filtros
    id_input = st.sidebar.text_input("Buscar por ID (ID_ANT):")
    nombre_input = st.sidebar.selectbox("Buscar por Nombre (NOMBRE):", options=[""] + sorted(gdf['NOMBRE'].dropna().unique()))
    tipo_sel = st.sidebar.multiselect("Filtrar por tipo (Tipo)", sorted(gdf["Tipo"].dropna().unique()))
    depto_sel = st.sidebar.multiselect("Filtrar por departamento", sorted(gdf["DEPARTAMEN"].dropna().unique()))
    mpio_sel = st.sidebar.multiselect("Filtrar por municipio", sorted(gdf["MUNICIPIO"].dropna().unique()))

    # Selector de fondo de mapa
    fondo_seleccionado = st.sidebar.selectbox("🗺️ Fondo del mapa", list(fondos_disponibles.keys()), index=1)

    # Inicializa el estado de la sesión para mostrar el mapa
    if "mostrar_mapa" not in st.session_state:
        st.session_state["mostrar_mapa"] = False

    # Botones de acción en la barra lateral
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("🧭 Mostrar mapa"):
            st.session_state["mostrar_mapa"] = True
    with col2:
        if st.button("🔄 Reiniciar visor"):
            # Reinicia todas las variables de estado para limpiar filtros y mapa
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun() # Vuelve a ejecutar la aplicación para aplicar el reinicio
    with col3:
        exportar_html = st.button("💾 Exportar HTML")

    # --- Aplicación de filtros al GeoDataFrame ---
    gdf_filtrado = gdf.copy() # Crea una copia para no modificar el original
    if id_input:
        # Filtra por ID_ANT, buscando coincidencias parciales
        gdf_filtrado = gdf_filtrado[gdf_filtrado["ID_ANT"].astype(str).str.contains(id_input)]
    if nombre_input:
        # Filtra por nombre exacto
        gdf_filtrado = gdf_filtrado[gdf_filtrado["NOMBRE"] == nombre_input]
    if tipo_sel:
        # Filtra por tipo (permite múltiples selecciones)
        gdf_filtrado = gdf_filtrado[gdf_filtrado["Tipo"].isin(tipo_sel)]
    if depto_sel:
        # Filtra por departamento (permite múltiples selecciones)
        gdf_filtrado = gdf_filtrado[gdf_filtrado["DEPARTAMEN"].isin(depto_sel)]
    if mpio_sel:
        # Filtra por municipio (permite múltiples selecciones)
        gdf_filtrado = gdf_filtrado[gdf_filtrado["MUNICIPIO"].isin(mpio_sel)]

    # Mensaje cuando se consulta un único territorio
    if st.session_state["mostrar_mapa"] and len(gdf_filtrado) == 1:
        nombre_unico = gdf_filtrado["NOMBRE"].iloc[0]
        st.markdown(
            f"<div style='background-color:#ffffff11; padding:10px; border-radius:10px; font-size:18px; "
            f"color:white; text-align:center; font-weight:bold;'>📂 Territorio consultado: {nombre_unico}</div>",
            unsafe_allow_html=True
        )

    # --- Mostrar el mapa y los resultados si se ha activado el botón "Mostrar mapa" ---
    if st.session_state["mostrar_mapa"]:
        if not gdf_filtrado.empty:
            st.subheader("🗺️ Resultado geográfico")

            # Calcula los límites del mapa para centrarlo en los resultados
            bounds = gdf_filtrado.total_bounds
            center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
            m = folium.Map(location=center, zoom_start=10, tiles=fondos_disponibles[fondo_seleccionado])

            # Función para aplicar estilos a los polígonos según el tipo (Indígena o Campesino/Comunitario)
            def estilo_tipo(x):
                tipo = x["properties"]["Tipo"].strip().lower()
                return {
                    "fillColor": "#228B22" if "indigena" in tipo else "#8B4513", # Verde para indígena, marrón para otros
                    "color": "#228B22" if "indigena" in tipo else "#8B4513",
                    "weight": 2,
                    "fillOpacity": 0.5
                }

            # Añade los GeoJson filtrados al mapa con tooltips y estilos
            folium.GeoJson(
                gdf_filtrado,
                tooltip=folium.GeoJsonTooltip(
                    fields=["ID_ANT", "NOMBRE", "DEPARTAMEN", "MUNICIPIO", "Tipo", "AREA_TOTAL"],
                    aliases=["ID:", "Nombre:", "Departamento:", "Municipio:", "Tipo:", "Área total (ha):"]
                ),
                style_function=estilo_tipo
            ).add_to(m)

            # Ajusta el mapa para que muestre todos los elementos filtrados
            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
            # Renderiza el mapa de Folium en Streamlit
            st_folium(m, width=1200, height=600)

            st.subheader("📋 Datos encontrados")
            # Muestra la tabla de datos de los territorios filtrados (excluyendo la columna de geometría)
            st.dataframe(gdf_filtrado.drop(columns="geometry"))

            # --- Estadísticas de los resultados ---
            total_comunidades = len(gdf_filtrado)
            area_total = gdf_filtrado["AREA_TOTAL"].sum()
            hectareas = int(area_total)
            metros2 = int(round((area_total - hectareas) * 10000)) # Calcula los metros cuadrados restantes
            tipo_normalizado = gdf_filtrado["Tipo"].str.lower().str.strip()
            cuenta_indigena = tipo_normalizado.str.contains("indigena").sum()
            cuenta_consejo = tipo_normalizado.str.contains("comunitario").sum()

            # Muestra las estadísticas en un cuadro estilizado
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

            # --- Opciones de exportación de datos ---
            # Exportar a CSV
            csv = gdf_filtrado.drop(columns="geometry").to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", data=csv, file_name="resultados_formalizados.csv", mime="text/csv")

            # Exportar a Shapefile (ZIP)
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "shapefile_filtrado.zip")
                shp_base = os.path.join(tmpdir, "shapefile_filtrado")
                gdf_filtrado.to_file(shp_base + ".shp", driver="ESRI Shapefile", encoding="utf-8")
                # Crea el archivo ZIP con todos los componentes del shapefile
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
                        fpath = shp_base + ext
                        if os.path.exists(fpath):
                            zipf.write(fpath, arcname="shapefile_filtrado" + ext)
                with open(zip_path, "rb") as f:
                    st.download_button("⬇️ Descargar SHP filtrado (.zip)", data=f, file_name="shapefile_filtrado.zip", mime="application/zip")

            # Exportar el mapa a HTML
            if exportar_html:
                with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmpfile:
                    m.save(tmpfile.name) # Guarda el mapa de Folium como HTML
                    st.success("✅ Mapa exportado correctamente.")
                    with open(tmpfile.name, "rb") as f:
                        st.download_button("⬇️ Descargar HTML del mapa", data=f, file_name="mapa_formalizado.html", mime="text/html")

        else:
            st.warning("⚠️ No se encontraron resultados con los filtros aplicados.")

# --- Sección de derechos de autor ---
st.markdown("""
<hr style='border-top: 1px solid #444;'>
<div style='text-align: center; font-size: 14px; color: gray; padding-top: 10px;'>
    Realizado por <strong>Ing. Topográfico Luis Miguel Guerrero</strong> —
    <a href="mailto:luis.guerrero@ant.gov.co" style="color:gray;">luis.guerrero@ant.gov.co</a><br>
    <em>© Derechos reservados</em>
</div>
""", unsafe_allow_html=True)
