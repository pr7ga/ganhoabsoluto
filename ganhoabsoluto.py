import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.title("Cálculo do Ganho da Antena AUT - Método das Três Antenas")

st.markdown("""
Este aplicativo calcula o **ganho absoluto da antena AUT** com base em três medições de S21 feitas duas a duas:
- AUT + LOGPED
- HORN + LOGPED
- AUT + HORN
""")

# Upload dos arquivos
file_aut_logped = st.file_uploader("Carregue o arquivo S21 AUT + LOGPED", type=["csv"])
file_horn_logped = st.file_uploader("Carregue o arquivo S21 HORN + LOGPED", type=["csv"])
file_aut_horn = st.file_uploader("Carregue o arquivo S21 AUT + HORN", type=["csv"])

freq_input = st.number_input("Informe a frequência (em MHz) para cálculo do ganho", min_value=0.0, step=0.1)

if file_aut_logped and file_horn_logped and file_aut_horn and freq_input > 0:
    # Leitura dos arquivos
    df_aut_logped = pd.read_csv(file_aut_logped)
    df_horn_logped = pd.read_csv(file_horn_logped)
    df_aut_horn = pd.read_csv(file_aut_horn)

    # Detecta colunas com base no conteúdo
    def detect_columns(df):
        if len(df.columns) == 1:
            df = pd.read_csv(StringIO(df.columns[0]), sep=";|,", engine="python")
        return df

    # Garante que a primeira coluna é frequência e a segunda é S21 em dB
    for df in [df_aut_logped, df_horn_logped, df_aut_horn]:
        df.columns = [col.strip() for col in df.columns]
        df = df.dropna()
    
    # Assume que primeira coluna = frequência (MHz), segunda = S21 (dB)
    freq_aut_logped = df_aut_logped.iloc[:, 0]
    s21_aut_logped = df_aut_logped.iloc[:, 1]

    freq_horn_logped = df_horn_logped.iloc[:, 0]
    s21_horn_logped = df_horn_logped.iloc[:, 1]

    freq_aut_horn = df_aut_horn.iloc[:, 0]
    s21_aut_horn = df_aut_horn.iloc[:, 1]

    # Interpola valores próximos à frequência solicitada
    def interp(freqs, values, target_freq):
        return np.interp(target_freq, freqs, values)

    M_aut_logped = interp(freq_aut_logped, s21_aut_logped, freq_input)
    M_horn_logped = interp(freq_horn_logped, s21_horn_logped, freq_input)
    M_aut_horn = interp(freq_aut_horn, s21_aut_horn, freq_input)

    # Cálculo do ganho da AUT
    G_aut = (M_aut_horn + M_aut_logped - M_horn_logped) / 2

    st.subheader("Resultado:")
    st.write(f"**Frequência:** {freq_input:.2f} MHz")
    st.write(f"**M(AUT,LOGPED):** {M_aut_logped:.2f} dB")
    st.write(f"**M(HORN,LOGPED):** {M_horn_logped:.2f} dB")
    st.write(f"**M(AUT,HORN):** {M_aut_horn:.2f} dB")
    st.success(f"**Ganho da antena AUT:** {G_aut:.2f} dB")

    # Plot comparativo
    fig, ax = plt.subplots()
    ax.plot(freq_aut_logped, s21_aut_logped, label="AUT + LOGPED")
    ax.plot(freq_horn_logped, s21_horn_logped, label="HORN + LOGPED")
    ax.plot(freq_aut_horn, s21_aut_horn, label="AUT + HORN")
    ax.axvline(freq_input, color='red', linestyle='--', label=f"{freq_input} MHz")
    ax.set_xlabel("Frequência (MHz)")
    ax.set_ylabel("S21 (dB)")
    ax.legend()
    st.pyplot(fig)
else:
    st.info("Carregue os três arquivos e insira a frequência para calcular o ganho.")
