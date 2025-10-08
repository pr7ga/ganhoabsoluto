import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

st.title("Cálculo do Ganho da Antena AUT - Método das Três Antenas")

st.markdown("""
Este aplicativo calcula o **ganho absoluto da antena AUT** com base em três medições de S21 feitas duas a duas:
- AUT + LOGPED
- HORN + LOGPED
- AUT + HORN
""")

# Função universal para ler CSV com diferentes separadores e codificações
def read_s21_file(file):
    # Lê o conteúdo bruto
    raw = file.getvalue().decode(errors='ignore')
    sample = raw[:200]
    # Detecta separador mais provável
    if ";" in sample:
        sep = ";"
    elif "\t" in sample:
        sep = "\t"
    elif "," in sample:
        sep = ","
    else:
        sep = r"\s+"  # espaços múltiplos

    # Tenta ler o CSV sem cabeçalho
    df = pd.read_csv(io.StringIO(raw), sep=sep, header=None, engine="python")

    # Garante que há ao menos duas colunas
    if df.shape[1] < 2:
        raise ValueError("Arquivo tem menos de duas colunas válidas.")

    # Usa apenas as duas primeiras colunas
    df = df.iloc[:, :2]
    df.columns = ["Frequência (MHz)", "S21 (dB)"]
    df = df.dropna()

    # Se as frequências forem muito grandes, converte de Hz para MHz
    if df["Frequência (MHz)"].max() > 1e5:
        df["Frequência (MHz)"] /= 1e6

    return df

# Upload dos arquivos
file_aut_logped = st.file_uploader("Carregue o arquivo S21 AUT + LOGPED", type=["csv"])
file_horn_logped = st.file_uploader("Carregue o arquivo S21 HORN + LOGPED", type=["csv"])
file_aut_horn = st.file_uploader("Carregue o arquivo S21 AUT + HORN", type=["csv"])

freq_input = st.number_input("Informe a frequência (em MHz) para cálculo do ganho", min_value=0.0, step=0.1)

if file_aut_logped and file_horn_logped and file_aut_horn and freq_input > 0:
    try:
        df_aut_logped = read_s21_file(file_aut_logped)
        df_horn_logped = read_s21_file(file_horn_logped)
        df_aut_horn = read_s21_file(file_aut_horn)

        st.success("Arquivos lidos com sucesso!")
        st.write("Prévia dos dados (AUT + LOGPED):")
        st.dataframe(df_aut_logped.head())

    except Exception as e:
        st.error(f"Erro ao ler os arquivos: {e}")
        st.stop()

    # Interpola valores na frequência desejada
    def interp(freqs, values, target_freq):
        return np.interp(target_freq, freqs, values)

    M_aut_logped = interp(df_aut_logped["Frequência (MHz)"], df_aut_logped["S21 (dB)"], freq_input)
    M_horn_logped = interp(df_horn_logped["Frequência (MHz)"], df_horn_logped["S21 (dB)"], freq_input)
    M_aut_horn = interp(df_aut_horn["Frequência (MHz)"], df_aut_horn["S21 (dB)"], freq_input)

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
    ax.plot(df_aut_logped["Frequência (MHz)"], df_aut_logped["S21 (dB)"], label="AUT + LOGPED")
    ax.plot(df_horn_logped["Frequência (MHz)"], df_horn_logped["S21 (dB)"], label="HORN + LOGPED")
    ax.plot(df_aut_horn["Frequência (MHz)"], df_aut_horn["S21 (dB)"], label="AUT + HORN")
    ax.axvline(freq_input, color='red', linestyle='--', label=f"{freq_input} MHz")
    ax.set_xlabel("Frequência (MHz)")
    ax.set_ylabel("S21 (dB)")
    ax.legend()
    st.pyplot(fig)
else:
    st.info("Carregue os três arquivos e insira a frequência para calcular o ganho.")
