import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import os
import zipfile
import tempfile
import pandas as pd
from PIL import Image

# --- Estilo visual ---
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

# --- Título y banner ---
st.title("📜 Visor de Territorios Formalizados")
st.markdown("Consulta local de territorios por ID o Nombre. Fuente: ANT")

# Mostrar banner
st.image("Ancestrario.png", use_container_width=True)

# --- Función para cargar shapefile desde ZIP ---
def cargar_shapefile_desde_zip(path_zip):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(path_zip, "r") as zip_ref:
            zip_ref.extractall(tmpdir)
            shp_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")][0]
            return gpd.read_file(shp_path).to_crs(epsg=4326)

# --- Cargar shapefile principal ---
ruta_formalizado = "Formalizado.zip"
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

# Mostrar logo institucional en el sidebar (esto va FUERA del with tab1:)
logo = Image.open("logo_ant.jpg")
st.sidebar.image(logo, use_container_width=True)

# --- Pestañas ---
tab1, tab2 = st.tabs(["🔍 Consulta por filtros", "📐 Consulta por traslape"])

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

            def estilo_tipo(x):
                tipo = x["properties"]["Tipo"].strip().lower()
                return {
                    "fillColor": "#228B22" if "indigena" in tipo else "#8B4513",
                    "color": "#228B22" if "indigena" in tipo else "#8B4513",
                    "weight": 2,
                    "fillOpacity": 0.5
                }

            folium.GeoJson(
                gdf_filtrado,
                tooltip=folium.GeoJsonTooltip(
                    fields=["ID_ANT", "NOMBRE", "DEPARTAMEN", "MUNICIPIO", "Tipo", "AREA_TOTAL"],
                    aliases=["ID:", "Nombre:", "Departamento:", "Municipio:", "Tipo:", "Área total (ha):"]
                ),
                style_function=estilo_tipo
            ).add_to(m)

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

# ===============================
# PESTAÑA 2: TRASLAPE
# ===============================
with tab2:
    st.markdown("### 📐 Verificar traslape con polígono cargado")

    archivo_zip = st.file_uploader("Cargar archivo .zip con shapefile (predio o polígono)", type="zip")

    if archivo_zip is not None:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "user.zip")
            with open(zip_path, "wb") as f:
                f.write(archivo_zip.read())

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
                shp_paths = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
                if not shp_paths:
                    st.warning("No se encontró ningún archivo .shp dentro del ZIP.")
                else:
                    user_shp = gpd.read_file(os.path.join(tmpdir, shp_paths[0])).to_crs("EPSG:4326")
                    st.success("✅ Archivo cargado correctamente.")

                    st.markdown("#### 🗺️ Mapa del predio cargado y traslapes encontrados")
                    bounds = user_shp.total_bounds
                    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
                    m2 = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron")

                    # Mostrar predio en rojo
                    folium.GeoJson(
                        user_shp,
                        name="Polígono cargado",
                        style_function=lambda x: {
                            "color": "red",
                            "weight": 3,
                            "fillOpacity": 0
                        }
                    ).add_to(m2)

                    # Obtener territorios que intersectan
                    territorios_afectados = gdf[gdf.intersects(user_shp.unary_union)]

                    # Calcular intersección exacta
                    intersecciones = gpd.overlay(gdf, user_shp, how="intersection").to_crs(epsg=9377)

                    if not intersecciones.empty:
                        intersecciones["area_m2"] = intersecciones.geometry.area
                        intersecciones["area_ha"] = intersecciones["area_m2"] / 10000

                        area_predio_m2 = user_shp.to_crs(epsg=9377).geometry.area.sum()
                        intersecciones["area_territorio_m2"] = intersecciones["AREA_TOTAL"] * 10000

                        intersecciones["% del predio"] = (intersecciones["area_m2"] / area_predio_m2 * 100).round(2)
                        intersecciones["% del territorio"] = (intersecciones["area_m2"] / intersecciones["area_territorio_m2"] * 100).round(2)

                        # Dibujar territorios completos (bordes)
                        def borde_tipo(x):
                            tipo = x["properties"]["Tipo"].strip().lower()
                            return {
                                "color": "#004400" if "indigena" in tipo else "#663300",
                                "weight": 1.5,
                                "fillOpacity": 0
                            }

                        folium.GeoJson(
                            territorios_afectados,
                            style_function=borde_tipo,
                            name="Territorios completos"
                        ).add_to(m2)

                        # Dibujar intersección (relleno)
                        def estilo_tipo(x):
                            tipo = x["properties"]["Tipo"].strip().lower()
                            return {
                                "fillColor": "#228B22" if "indigena" in tipo else "#8B4513",
                                "color": "#228B22" if "indigena" in tipo else "#8B4513",
                                "weight": 2,
                                "fillOpacity": 0.4
                            }

                        folium.GeoJson(
                            intersecciones.to_crs(epsg=4326),
                            tooltip=folium.GeoJsonTooltip(
                                fields=["NOMBRE", "Tipo", "area_ha", "% del predio", "% del territorio"],
                                aliases=["Nombre:", "Tipo:", "Área traslapada (ha):", "% del predio:", "% del territorio:"]
                            ),
                            style_function=estilo_tipo
                        ).add_to(m2)

                        m2.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
                        st_folium(m2, width=1200, height=600)

                        st.subheader("📋 Detalles del traslape")
                        tabla = intersecciones[["ID_ANT", "NOMBRE", "Tipo", "DEPARTAMEN", "MUNICIPIO", "area_ha", "% del predio", "% del territorio"]]
                        tabla["area_ha"] = tabla["area_ha"].round(2)
                        st.dataframe(tabla)

                        csv_traslape = tabla.to_csv(index=False).encode("utf-8")
                        st.download_button("⬇️ Descargar CSV del traslape", data=csv_traslape, file_name="traslapes_con_area.csv", mime="text/csv")
                    else:
                        st.info("✅ No se encontraron traslapes con territorios formalizados.")

# --- Derechos de autor ---
st.markdown("""
<hr style='border-top: 1px solid #444;'>
<div style='text-align: center; font-size: 14px; color: gray; padding-top: 10px;'>
    Realizado por <strong>Ing. Topográfico Luis Miguel Guerrero</strong> — 
    <a href="mailto:luis.guerrero@ant.gov.co" style="color:gray;">luis.guerrero@ant.gov.co</a><br>
    <em>© Derechos reservados</em>
</div>
""", unsafe_allow_html=True)
