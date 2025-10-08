import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO, StringIO

st.title("Cálculo do Ganho Absoluto - Método das Três Antenas")

st.markdown("""
Este aplicativo calcula o **ganho absoluto da antena AUT** pelo método das **três antenas**, 
usando medições de S21 feitas entre:
- AUT + ANT1  
- AUT + ANT2  
- ANT1 + ANT2  
""")

# Upload dos três arquivos CSV
file_aut_ant2 = st.file_uploader("Carregue o arquivo CSV de S21 AUT + ANT2", type=["csv"])
file_ant1_ant2 = st.file_uploader("Carregue o arquivo CSV de S21 ANT1 + ANT2", type=["csv"])
file_aut_ant1 = st.file_uploader("Carregue o arquivo CSV de S21 AUT + ANT1", type=["csv"])

freq_mhz = st.number_input("Informe a frequência (MHz) para cálculo do ganho:", min_value=0.0, step=0.1)

def read_csv_auto(file):
    """Tenta ler um CSV com diferentes separadores e codificações"""
    if file is None:
        return None
    for sep in [',', ';', '\t']:
        try:
            df = pd.read_csv(file, sep=sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue
    return None

if file_aut_ant2 and file_ant1_ant2 and file_aut_ant1:
    df_aut_ant2 = read_csv_auto(file_aut_ant2)
    df_ant1_ant2 = read_csv_auto(file_ant1_ant2)
    df_aut_ant1 = read_csv_auto(file_aut_ant1)

    if df_aut_ant2 is None or df_ant1_ant2 is None or df_aut_ant1 is None:
        st.error("Erro ao ler os arquivos: Verifique o separador ou o formato.")
    else:
        # Detectar colunas de frequência e S21 automaticamente
        def prepare_df(df):
            df.columns = [col.strip() for col in df.columns]
            freq_col = [c for c in df.columns if 'freq' in c.lower()][0]
            s21_col = [c for c in df.columns if 's21' in c.lower() or 'amplitude' in c.lower() or 'mag' in c.lower()][0]
            df = df[[freq_col, s21_col]].copy()
            df.columns = ["Freq_MHz", "S21_dB"]
            return df

        df_aut_ant2 = prepare_df(df_aut_ant2)
        df_ant1_ant2 = prepare_df(df_ant1_ant2)
        df_aut_ant1 = prepare_df(df_aut_ant1)

        # Garantir que as frequências são números
        for df in [df_aut_ant2, df_ant1_ant2, df_aut_ant1]:
            df["Freq_MHz"] = pd.to_numeric(df["Freq_MHz"], errors="coerce")
            df["S21_dB"] = pd.to_numeric(df["S21_dB"], errors="coerce")
            df.dropna(inplace=True)

        # Calcular o ganho usando o método das três antenas
        # Fórmulas baseadas na simetria do método
        merged = df_aut_ant2.merge(df_aut_ant1, on="Freq_MHz", suffixes=("_AUT_ANT2", "_AUT_ANT1"))
        merged = merged.merge(df_ant1_ant2, on="Freq_MHz")
        merged.rename(columns={"S21_dB": "S21_ANT1_ANT2"}, inplace=True)

        merged["G_AUT"] = (merged["S21_dB_AUT_ANT1"] + merged["S21_dB_AUT_ANT2"] - merged["S21_ANT1_ANT2"]) / 2
        merged["G_ANT1"] = (merged["S21_dB_AUT_ANT1"] + merged["S21_ANT1_ANT2"] - merged["S21_dB_AUT_ANT2"]) / 2
        merged["G_ANT2"] = (merged["S21_dB_AUT_ANT2"] + merged["S21_ANT1_ANT2"] - merged["S21_dB_AUT_ANT1"]) / 2

        # Mostrar resultado na frequência desejada
        if freq_mhz > 0:
            freq_sel = merged.iloc[(merged["Freq_MHz"] - freq_mhz).abs().argsort()[:1]]
            g_aut = freq_sel["G_AUT"].values[0]
            st.success(f"Ganho da antena AUT em **{freq_sel['Freq_MHz'].values[0]:.2f} MHz**: **{g_aut:.2f} dB**")

        # Gráfico dos ganhos
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(merged["Freq_MHz"], merged["G_AUT"], label="AUT", linewidth=2)
        ax.plot(merged["Freq_MHz"], merged["G_ANT1"], label="ANT1", linestyle="--")
        ax.plot(merged["Freq_MHz"], merged["G_ANT2"], label="ANT2", linestyle=":")
        ax.set_xlabel("Frequência (MHz)")
        ax.set_ylabel("Ganho (dB)")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend()
        st.pyplot(fig)

        # Gerar CSV para download
        csv_buffer = StringIO()
        merged.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📊 Baixar dados do ganho (CSV)",
            data=csv_buffer.getvalue(),
            file_name="ganho_tres_antenas.csv",
            mime="text/csv"
        )

        # Baixar gráfico em PNG
        img_bytes = BytesIO()
        fig.savefig(img_bytes, format="png", bbox_inches="tight")
        st.download_button(
            label="📈 Baixar gráfico (PNG)",
            data=img_bytes.getvalue(),
            file_name="grafico_ganho_tres_antenas.png",
            mime="image/png"
        )

else:
    st.info("Por favor, carregue os três arquivos CSV para iniciar o cálculo.")
