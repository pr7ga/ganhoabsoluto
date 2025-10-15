import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.title("Cálculo de Ganho da Antena Sob Teste (AUT) a partir de arquivos S2P")

st.markdown("""
Este aplicativo calcula o **ganho da antena sob teste (AUT)** com base em medições S2P.
Carregue:
- Um arquivo S2P referente à medição entre a **antena transmissora** e a **antena padrão** (com ganho conhecido);
- Um arquivo S2P referente à medição entre a **antena transmissora** e a **antena sob teste (AUT)**.

O programa irá:
1. Ler e interpretar os arquivos S2P (ignorando cabeçalho);
2. Interpolar os dados para a frequência informada;
3. Calcular o ganho da AUT;
4. Mostrar o gráfico do ganho centrado na frequência informada (±20%).
""")

# === Upload dos arquivos ===
file_ref = st.file_uploader("Carregue o arquivo S2P da antena padrão", type=["s2p"])
file_aut = st.file_uploader("Carregue o arquivo S2P da antena sob teste (AUT)", type=["s2p"])

# === Entradas ===
freq_input = st.number_input("Frequência de interesse (MHz):", min_value=0.0, step=0.1)
G_ref = st.number_input("Ganho conhecido da antena padrão (dBi):", step=0.1)

# === Função para ler S2P ===
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

# === Cálculo do ganho ===
def calc_gain(G_ref, S21_aut_dB, S21_ref_dB, S11_aut_dB, S11_ref_dB):
    gamma_aut = 10**(S11_aut_dB/20)
    gamma_ref = 10**(S11_ref_dB/20)
    gain_aut = G_ref + (S21_aut_dB - S21_ref_dB) + 10*np.log10((1 - gamma_ref**2)/(1 - gamma_aut**2))
    return gain_aut, gamma_aut, gamma_ref

if file_ref and file_aut:
    df_ref = read_s2p(file_ref)
    df_aut = read_s2p(file_aut)

    if df_ref is not None and df_aut is not None:
        # Ajuste de unidade de frequência
        freq_ref_mean = df_ref["Freq"].mean()
        if freq_ref_mean > 1e6:
            df_ref["Freq_MHz"] = df_ref["Freq"] / 1e6
            df_aut["Freq_MHz"] = df_aut["Freq"] / 1e6
        else:
            df_ref["Freq_MHz"] = df_ref["Freq"]
            df_aut["Freq_MHz"] = df_aut["Freq"]

        # Interpola e calcula o ganho em todas as frequências coincidentes
        freqs_common = np.intersect1d(df_ref["Freq_MHz"], df_aut["Freq_MHz"])
        if len(freqs_common) == 0:
            freqs_common = np.linspace(max(df_ref["Freq_MHz"].min(), df_aut["Freq_MHz"].min()),
                                       min(df_ref["Freq_MHz"].max(), df_aut["Freq_MHz"].max()), 300)

        S21_ref_interp = np.interp(freqs_common, df_ref["Freq_MHz"], df_ref["S21_mag"])
        S21_aut_interp = np.interp(freqs_common, df_aut["Freq_MHz"], df_aut["S21_mag"])
        S11_ref_interp = np.interp(freqs_common, df_ref["Freq_MHz"], df_ref["S11_mag"])
        S11_aut_interp = np.interp(freqs_common, df_aut["Freq_MHz"], df_aut["S11_mag"])

        G_aut_curve = []
        for i in range(len(freqs_common)):
            g, _, _ = calc_gain(G_ref, S21_aut_interp[i], S21_ref_interp[i],
                                S11_aut_interp[i], S11_ref_interp[i])
            G_aut_curve.append(g)
        G_aut_curve = np.array(G_aut_curve)

        # === Faixa de frequência para exibir (±20%) ===
        if freq_input > 0:
            bw_min = freq_input * 0.8
            bw_max = freq_input * 1.2
        else:
            bw_min = freqs_common.min()
            bw_max = freqs_common.max()

        mask_bw = (freqs_common >= bw_min) & (freqs_common <= bw_max)
        freqs_plot = freqs_common[mask_bw]
        gains_plot = G_aut_curve[mask_bw]

        # === Gráfico ===
        fig, ax = plt.subplots()
        ax.plot(freqs_plot, gains_plot, label="Ganho da AUT", linewidth=2)
        ax.axvline(freq_input, color='r', linestyle='--', label=f'{freq_input:.1f} MHz')
        ax.set_xlim(bw_min, bw_max)
        ax.set_xlabel("Frequência (MHz)")
        ax.set_ylabel("Ganho (dBi)")
        ax.set_title(f"Ganho da AUT em torno de {freq_input:.1f} MHz (±20%)")
        ax.grid(True)
        ax.legend()
        #st.pyplot(fig)

        # === Cálculo pontual ===
        if freq_input > 0:
            S21_ref = np.interp(freq_input, df_ref["Freq_MHz"], df_ref["S21_mag"])
            S21_aut = np.interp(freq_input, df_aut["Freq_MHz"], df_aut["S21_mag"])
            S11_ref = np.interp(freq_input, df_ref["Freq_MHz"], df_ref["S11_mag"])
            S11_aut = np.interp(freq_input, df_aut["Freq_MHz"], df_aut["S11_mag"])

            G_aut, gamma_aut, gamma_ref = calc_gain(G_ref, S21_aut, S21_ref, S11_aut, S11_ref)

            st.markdown("### 📊 Cálculo detalhado na frequência selecionada")
            st.write(f"**Frequência:** {freq_input:.2f} MHz")
            st.write(f"**S21_ref (dB):** {S21_ref:.2f}")
            st.write(f"**S21_aut (dB):** {S21_aut:.2f}")
            st.write(f"**S11_ref (dB):** {S11_ref:.2f} → |Γ_ref| = {gamma_ref:.3f}")
            st.write(f"**S11_aut (dB):** {S11_aut:.2f} → |Γ_aut| = {gamma_aut:.3f}")

            st.latex(r"G_{AUT} = G_{ref} + (S21_{AUT} - S21_{REF}) + 10 \log_{10}\frac{1 - |\Gamma_{ref}|^2}{1 - |\Gamma_{AUT}|^2}")
            st.success(f"**Ganho calculado da AUT:** {G_aut:.2f} dBi")
