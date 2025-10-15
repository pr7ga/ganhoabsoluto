import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.title("Cálculo e Visualização do Ganho da Antena Sob Teste (AUT) a partir de arquivos S2P")

st.markdown("""
Este aplicativo calcula o **ganho da antena sob teste (AUT)** a partir de medições S2P.

Você deve carregar:
- Um arquivo S2P referente à medição entre a **antena transmissora e a antena padrão** (ganho conhecido);
- Um arquivo S2P referente à medição entre a **antena transmissora e a antena sob teste (AUT)**.
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
    s11_mag = np.interp(freq_target, df["Freq"], df["S11_mag"])
    s21_mag = np.interp(freq_target, df["Freq"], df["S21_mag"])
    s22_mag = np.interp(freq_target, df["Freq"], df["S22_mag"])
    return s11_mag, s21_mag, s22_mag

# === Cálculo do ganho ===
def calc_gain(G_ref, S21_aut_dB, S21_ref_dB, S11_aut_dB, S11_ref_dB):
    gamma_aut = 10**(S11_aut_dB/20)
    gamma_ref = 10**(S11_ref_dB/20)
    gain_aut = G_ref + (S21_aut_dB - S21_ref_dB) + 10*np.log10((1 - gamma_ref**2)/(1 - gamma_aut**2))
    return gain_aut

if file_ref and file_aut:
    df_ref = read_s2p(file_ref)
    df_aut = read_s2p(file_aut)

    if df_ref is not None and df_aut is not None:
        # Detecta se a frequência está em Hz (valores grandes)
        freq_target = freq_input
        if df_ref["Freq"].mean() > 1e6:
            freq_target *= 1e6  # converte MHz -> Hz

        # Interpola nas frequências
        s11_ref, s21_ref, s22_ref = interpolate_param(df_ref, freq_target)
        s11_aut, s21_aut, s22_aut = interpolate_param(df_aut, freq_target)

        # Calcula o ganho ponto a ponto (para gráfico)
        min_len = min(len(df_ref), len(df_aut))
        freq_common = df_ref["Freq"].iloc[:min_len]
        G_aut_curve = G_ref + (df_aut["S21_mag"].iloc[:min_len] - df_ref["S21_mag"].iloc[:min_len]) + \
                      10*np.log10((1 - 10**(df_ref["S11_mag"].iloc[:min_len]/10))/(1 - 10**(df_aut["S11_mag"].iloc[:min_len]/10)))

        # === Resultado na frequência de interesse ===
        G_aut_freq = calc_gain(G_ref, s21_aut, s21_ref, s11_aut, s11_ref)

        st.subheader("📈 Gráfico do ganho da antena sob teste (AUT)")
        fig, ax = plt.subplots()
        ax.plot(freq_common/1e6, G_aut_curve, label="Ganho AUT (calculado)", linewidth=2)
        ax.axvline(freq_input, color='r', linestyle='--', label=f'{freq_input:.2f} MHz')
        ax.set_xlabel("Frequência (MHz)")
        ax.set_ylabel("Ganho (dBi)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)

        # === Exibe resultados numéricos ===
        st.subheader("📊 Dados usados no cálculo")
        st.write(f"**Frequência de interesse:** {freq_input:.2f} MHz")
        st.write(f"**S21 (Tx → Ref):** {s21_ref:.2f} dB")
        st.write(f"**S21 (Tx → AUT):** {s21_aut:.2f} dB")
        st.write(f"**S11 (Ref):** {s11_ref:.2f} dB → |Γ_ref| = {10**(s11_ref/20):.4f}")
        st.write(f"**S11 (AUT):** {s11_aut:.2f} dB → |Γ_aut| = {10**(s11_aut/20):.4f}")
        st.write(f"**Ganho conhecido da antena padrão:** {G_ref:.2f} dBi")

        st.subheader("🧮 Cálculo do ganho da AUT")
        st.latex(r"""
        G_{AUT} = G_{ref} + (S_{21,AUT} - S_{21,ref}) + 10 \log_{10}\left(\frac{1 - |\Gamma_{ref}|^2}{1 - |\Gamma_{AUT}|^2}\right)
        """)
        st.write(f"**Resultado:** {G_aut_freq:.2f} dBi")

        st
