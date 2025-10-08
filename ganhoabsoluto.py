import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import re

st.set_page_config(layout="wide")
st.title("Ganho da Antena AUT — Método das Três Antenas")
st.markdown("Faça upload dos três arquivos S21 (duas a duas) e informe a frequência (MHz) para calcular o ganho da AUT.")

def read_s21_file(uploaded_file):
    """
    Lê arquivos como os que você enviou:
    - pula cabeçalhos estranhos até encontrar a linha 'Frequency' ou a primeira linha de dados,
    - lê CSV com vírgula,
    - seleciona as duas primeiras colunas (freq + amplitude),
    - converte de Hz->MHz se necessário e retorna DataFrame com colunas:
      'Frequência (MHz)', 'S21 (dB)'
    """
    raw = uploaded_file.getvalue()
    # tentar decodificações comuns
    text = None
    for enc in ("utf-8", "latin1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode("utf-8", errors="ignore")

    lines = text.splitlines()

    # 1) procura linha que contém 'frequency' (cabeçalho)
    idx = next((i for i, L in enumerate(lines) if "frequency" in L.lower()), None)

    # 2) se não encontrar cabeçalho, procura a primeira linha que contenha notação científica (dados)
    if idx is None:
        pattern = re.compile(r"^[\s\"']*[+\-]?\d+(\.\d+)?[eE][+\-]?\d+")
        idx = next((i for i, L in enumerate(lines) if pattern.search(L)), 0)

    sub = "\n".join(lines[idx:])

    # tenta ler com vírgula (formato dos seus arquivos). se falhar, tenta whitespace
    try:
        df = pd.read_csv(io.StringIO(sub), sep=",", engine="python")
    except Exception:
        df = pd.read_csv(io.StringIO(sub), sep=r"\s+", engine="python", header=None)

    if df.shape[1] < 2:
        raise ValueError("Não foi possível extrair pelo menos duas colunas (freq + amplitude). Verifique o arquivo.")

    # usa apenas as duas primeiras colunas
    df = df.iloc[:, :2].copy()
    # normaliza nomes e remove espaços/aspas
    df.columns = [str(c).strip() for c in df.columns]
    df.columns = ["Frequency_raw", "S21_raw"]

    # remove '+' e aspas em strings e converte para numérico
    df["Frequency_raw"] = df["Frequency_raw"].astype(str).str.replace(r"[+\"']", "", regex=True)
    df["S21_raw"] = df["S21_raw"].astype(str).str.replace(r"[+\"']", "", regex=True)

    df["Frequency_raw"] = pd.to_numeric(df["Frequency_raw"], errors="coerce")
    df["S21_raw"] = pd.to_numeric(df["S21_raw"], errors="coerce")
    df = df.dropna().reset_index(drop=True)

    if df.empty:
        raise ValueError("Após limpeza não restaram dados válidos.")

    # se frequência estiver em Hz (ex.: 1e8...), converte para MHz
    if df["Frequency_raw"].max() > 1e6:
        df["Frequency_MHz"] = df["Frequency_raw"] / 1e6
    else:
        df["Frequency_MHz"] = df["Frequency_raw"]

    df = df[["Frequency_MHz", "S21_raw"]].rename(columns={"Frequency_MHz": "Frequência (MHz)", "S21_raw": "S21 (dB)"})
    df = df.sort_values("Frequência (MHz)").drop_duplicates(subset="Frequência (MHz)", keep="first").reset_index(drop=True)
    return df

# upload (nomes atualizados: HORN -> ANT1, LOGPED -> ANT2)
f_aut_logped = st.file_uploader("S21 AUT + ANT2", type=["csv"])
f_horn_logped = st.file_uploader("S21 ANT1 + ANT2", type=["csv"])
f_aut_horn = st.file_uploader("S21 AUT + ANT1", type=["csv"])

freq_input = st.number_input("Frequência (MHz) para cálculo do ganho", min_value=0.0, step=0.01, format="%.4f")

if f_aut_logped and f_horn_logped and f_aut_horn and freq_input > 0:
    try:
        df_aut_logped = read_s21_file(f_aut_logped)
        df_horn_logped = read_s21_file(f_horn_logped)
        df_aut_horn = read_s21_file(f_aut_horn)
    except Exception as e:
        st.error(f"Erro ao ler os arquivos: {e}")
        st.stop()

    # mostra prévias para conferência (nomes atualizados)
    st.write("Prévia (AUT + ANT2):")
    st.dataframe(df_aut_logped.head())
    st.write("Prévia (ANT1 + ANT2):")
    st.dataframe(df_horn_logped.head())
    st.write("Prévia (AUT + ANT1):")
    st.dataframe(df_aut_horn.head())

    # função de interpolaçao (garante ordenação)
    def interp(df, fMHz):
        xs = df["Frequência (MHz)"].values
        ys = df["S21 (dB)"].values
        # se fMHz fora do range, interp irá extrapolar — avisamos
        if fMHz < xs.min() or fMHz > xs.max():
            st.warning(f"Frequência {fMHz} MHz está fora do intervalo de dados ({xs.min():.3f} — {xs.max():.3f} MHz). O valor será extrapolado.")
        return float(np.interp(fMHz, xs, ys))

    M_aut_logped = interp(df_aut_logped, freq_input)
    M_horn_logped = interp(df_horn_logped, freq_input)
    M_aut_horn = interp(df_aut_horn, freq_input)

    G_aut = (M_aut_horn + M_aut_logped - M_horn_logped) / 2.0

    st.subheader("Resultado")
    st.write(f"Frequência: **{freq_input:.4f} MHz**")
    st.write(f"M(AUT,ANT2) = {M_aut_logped:.6f} dB")
    st.write(f"M(ANT1,ANT2) = {M_horn_logped:.6f} dB")
    st.write(f"M(AUT,ANT1) = {M_aut_horn:.6f} dB")
    st.success(f"Ganho da AUT = **{G_aut:.6f} dB**")

    # plot das três curvas e linha vertical na frequência selecionada (labels atualizados)
    fig, ax = plt.subplots(figsize=(9,4))
    ax.plot(df_aut_logped["Frequência (MHz)"], df_aut_logped["S21 (dB)"], label="AUT + ANT2")
    ax.plot(df_horn_logped["Frequência (MHz)"], df_horn_logped["S21 (dB)"], label="ANT1 + ANT2")
    ax.plot(df_aut_horn["Frequência (MHz)"], df_aut_horn["S21 (dB)"], label="AUT + ANT1")
    ax.axvline(freq_input, color="red", linestyle="--", label=f"{freq_input} MHz")
    ax.set_xlabel("Frequência (MHz)")
    ax.set_ylabel("S21 (dB)")
    ax.legend()
    st.pyplot(fig)

    # --- Adicionado: botões para baixar o gráfico S21 e os dados do ganho (CSV) ---
    # PNG do gráfico S21
    buf_png = io.BytesIO()
    fig.savefig(buf_png, format="png", bbox_inches='tight')
    buf_png.seek(0)
    st.download_button(
        label="📈 Baixar gráfico S21 (PNG)",
        data=buf_png.getvalue(),
        file_name=f"grafico_s21_{freq_input:.4f}MHz.png",
        mime="image/png"
    )

    # CSV com os dados do ganho no ponto solicitado
    df_point = pd.DataFrame({
        "Frequência (MHz)": [freq_input],
        "M(AUT,ANT2)_dB": [M_aut_logped],
        "M(ANT1,ANT2)_dB": [M_horn_logped],
        "M(AUT,ANT1)_dB": [M_aut_horn],
        "G_AUT_dB": [G_aut]
    })
    csv_buf = io.StringIO()
    df_point.to_csv(csv_buf, index=False)
    st.download_button(
        label="📊 Baixar dados do ganho (CSV)",
        data=csv_buf.getvalue(),
        file_name=f"ganho_aut_{freq_input:.4f}MHz.csv",
        mime="text/csv"
    )
    # --- fim das adições ---

    # opcional: calcular e mostrar curva de ganho na faixa comum
    if st.checkbox("Gerar curva de ganho AUT na faixa comum"):
        f_min = max(df_aut_logped["Frequência (MHz)"].min(), df_horn_logped["Frequência (MHz)"].min(), df_aut_horn["Frequência (MHz)"].min())
        f_max = min(df_aut_logped["Frequência (MHz)"].max(), df_horn_logped["Frequência (MHz)"].max(), df_aut_horn["Frequência (MHz)"].max())
        if f_min >= f_max:
            st.error("Não existe faixa comum entre as três medições para gerar a curva de ganho.")
        else:
            grid = np.linspace(f_min, f_max, 600)
            M1 = np.interp(grid, df_aut_horn["Frequência (MHz)"].values, df_aut_horn["S21 (dB)"].values)
            M2 = np.interp(grid, df_aut_logped["Frequência (MHz)"].values, df_aut_logped["S21 (dB)"].values)
            M3 = np.interp(grid, df_horn_logped["Frequência (MHz)"].values, df_horn_logped["S21 (dB)"].values)
            Ggrid = (M1 + M2 - M3) / 2.0
            fig2, ax2 = plt.subplots(figsize=(9,4))
            ax2.plot(grid, Ggrid, label="Ganho AUT (3-antenas)")
            ax2.set_xlabel("Frequência (MHz)")
            ax2.set_ylabel("Ganho (dB)")
            ax2.legend()
            st.pyplot(fig2)

            # --- Adicionado: botões para baixar gráfico de ganho e CSV da curva ---
            buf_png2 = io.BytesIO()
            fig2.savefig(buf_png2, format="png", bbox_inches='tight')
            buf_png2.seek(0)
            st.download_button(
                label="📈 Baixar gráfico de ganho AUT (PNG)",
                data=buf_png2.getvalue(),
                file_name="grafico_ganho_aut.png",
                mime="image/png"
            )

            df_grid = pd.DataFrame({"Frequência (MHz)": grid, "G_AUT_dB": Ggrid})
            csv_buf2 = io.StringIO()
            df_grid.to_csv(csv_buf2, index=False)
            st.download_button(
                label="📊 Baixar curva de ganho (CSV)",
                data=csv_buf2.getvalue(),
                file_name="curva_ganho_aut.csv",
                mime="text/csv"
            )
            # --- fim das adições ---
else:
    st.info("Carregue os três arquivos e coloque uma frequência (MHz) para calcular o ganho.")
