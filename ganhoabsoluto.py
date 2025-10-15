import streamlit as st
import pandas as pd
import numpy as np
import io

st.title("Cálculo de Ganho da Antena Sob Teste (AUT) a partir de arquivos S2P")

st.markdown("""
Este aplicativo calcula o ganho de uma antena sob teste (AUT) com base em medições S2P.
Você deve carregar:
- Um arquivo S2P referente à medição entre a antena transmissora e a **antena padrão** (com ganho conhecido);
- Um arquivo S2P referente à medição entre a antena transmissora e a **antena sob teste (AUT)**.
""")

# === Upload dos arquivos ===
file_ref = st.file_uploader("Carregue o arquivo S2P da antena padrão", type=["s2p"])
file_aut = st.file_uploader("Carregue o arquivo S2P da antena sob teste (AUT)", type=["s2p"])

# === Entradas adicionais ===
freq_input = st.number_input("Frequência de interesse (MHz):", min_value=0.0, step=0.1)
G_ref = st.number_input("Ganho conhecido da antena padrão (dBi):", step=0.1)

# === Função para ler arquivo S2P ===
def read_s2p(file):
    if file is None:
        return None

    # Lê o conteúdo e ignora o cabeçalho (linhas começando com '!' ou '#')
    content = file.getvalue().decode(errors='ignore').splitlines()
    data_lines = [line for line in content if not line.startswith('!') and not line.startswith('#') and line.strip() != '']
    df = pd.read_csv(io.StringIO("\n".join(data_lines)), 
                     delim_whitespace=True, 
                     header=None,
                     names=["Freq", "S11_mag", "S11_phase", "S21_mag", "S21_phase", 
                            "S12_mag", "S12_phase", "S22_mag", "S22_phase"])
    return df

# === Interpolação ===
def interpolate_param(df, freq_target):
    # Verifica se freq_target está dentro do intervalo
    if freq_target < df["Freq"].min() or freq_target > df["Freq"].max():
        st.warning("Frequência fora do intervalo de dados!")
        return None
    
    # Interpola magnitude e fase
    s11_mag = np.interp(freq_target, df["Freq"], df["S11_mag"])
    s21_mag = np.interp(freq_target, df["Freq"], df["S21_mag"])
    s22_mag = np.interp(freq_target, df["Freq"], df["S22_mag"])
    return s11_mag, s21_mag, s22_mag

# === Cálculo do ganho ===
def calc_gain(G_ref, S21_aut_dB, S21_ref_dB, S11_aut_dB, S11_ref_dB):
    # Converte S11 de dB para |Γ|
    gamma_aut = 10**(S11_aut_dB/20)
    gamma_ref = 10**(S11_ref_dB/20)

    # Fórmula: G_AUT = G_ref + (S21_aut - S21_ref) + 10*log10((1 - |Γ_ref|²)/(1 - |Γ_aut|²))
    gain_aut = G_ref + (S21_aut_dB - S21_ref_dB) + 10*np.log10((1 - gamma_ref**2)/(1 - gamma_aut**2))
    return gain_aut

# === Quando ambos arquivos são carregados ===
if file_ref and file_aut and freq_input > 0:
    df_ref = read_s2p(file_ref)
    df_aut = read_s2p(file_aut)

    if df_ref is not None and df_aut is not None:
        # Converte MHz para mesma unidade dos arquivos (verifica automaticamente)
        freq_target = freq_input
        # Detecta unidade (se valores ~10^6, então Hz)
        if df_ref["Freq"].mean() > 1e6:
            freq_target *= 1e6

        s11_ref, s21_ref, s22_ref = interpolate_param(df_ref, freq_target)
        s11_aut, s21_aut, s22_aut = interpolate_param(df_aut, freq_target)

        if None not in [s11_ref, s21_ref, s11_aut, s21_aut]:
            # Cálculo do ganho
            G_aut = calc_gain(G_ref, s21_aut, s21_ref, s11_aut, s11_ref)
            st.success(f"Ganho da antena sob teste (AUT) na frequência {freq_input:.2f} MHz: **{G_aut:.2f} dBi**")
        else:
            st.error("Erro ao interpolar os parâmetros.")
