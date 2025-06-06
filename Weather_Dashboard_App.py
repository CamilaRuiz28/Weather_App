import streamlit as st
import pandas as pd
import plotly.express as px
import re
from io import StringIO, BytesIO

# ───── Función para procesar líneas individuales ─────
def parse_line(line: str):
    if not re.match(r'^[A-Za-z]{3} \d{2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2}', line):
        return None

    rest = line.split(",", 1)[1].lstrip()
    parts = [p.replace('\x02', '').replace('\x03', '').strip() for p in rest.split(",") if p != ""]

    if parts and parts[0] == "Q":
        parts.pop(0)

    if parts and re.fullmatch(r'[0-9A-Fa-f]{1,2}', parts[-1]):
        parts.pop()

    if len(parts) != 13:
        return None

    parts[5] = parts[5].lstrip("+")
    parts[6] = parts[6].lstrip("+")

    parts.pop(-2)

    return parts

# ───── Procesa el buffer ─────
def procesar_buffer(buffer):
    lines = StringIO(buffer.getvalue().decode("utf-8", errors="ignore"))
    filas = [row for l in lines if (row := parse_line(l))]

    if not filas:
        st.error("No se encontraron registros válidos.")
        return pd.DataFrame()

    cols = ["DirViento", "VelViento", "DirVientoCorr", "Presion", "Humedad",
            "Temp", "PuntoRocio", "PrecipTotal", "IntensidadPrec",
            "Irradiancia", "FechaISO", "Flag"]

    df = pd.DataFrame(filas, columns=cols)

    num = [c for c in cols if c not in ("FechaISO", "Flag")]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")

    df["FechaISO"] = pd.to_datetime(df["FechaISO"], errors="coerce")
    df = df.dropna(subset=["FechaISO"])

    df["FechaHora"] = df["FechaISO"].dt.floor("h")
    df_h = df.groupby("FechaHora")[num].mean().reset_index()

    return df_h

# ───── Interfaz de Streamlit ─────
st.set_page_config(page_title="Dashboard Meteorológico", layout="wide", page_icon="🌦️")
st.title("🌦️ Dashboard Meteorológico")

archivo = st.file_uploader("📁 Sube el archivo .txt", type="txt")

if archivo:
    df = procesar_buffer(archivo)

    if not df.empty:
        st.success(f"✅ Procesadas {len(df)} horas de datos.")
        st.dataframe(df, use_container_width=True)

        # Descargas
        csv = StringIO()
        df.to_csv(csv, index=False, sep=";")
        st.download_button("⬇️ Descargar CSV", csv.getvalue(), "datos_procesados.csv", "text/csv")

        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.download_button("⬇️ Descargar Excel", bio.getvalue(),
                           "datos_procesados.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # ─── Dashboard ───
        variables = df.columns.drop("FechaHora")
        tabs = st.tabs(variables.tolist())

        for tab, var in zip(tabs, variables):
            with tab:
                col1, col2 = st.columns([3, 1])
                with col1:
                    fig = px.line(df, x="FechaHora", y=var, title=f"{var} por Fecha")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.metric("Promedio", f"{df[var].mean():.2f}")
                    st.metric("Máximo", f"{df[var].max():.2f}")
                    st.metric("Mínimo", f"{df[var].min():.2f}")
else:
    st.info("⬆️ Sube un archivo para comenzar.")
