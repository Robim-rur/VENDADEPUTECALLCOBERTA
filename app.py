import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime

# ---------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------
st.set_page_config(
    page_title="BOVA11 Wheel Strategy Pro",
    layout="wide"
)

# ---------------------------------------------------
# PARÂMETROS FIXOS
# ---------------------------------------------------
IR = 0.15
TAXAS = 0.0003
SELIC = 0.1075
VOL = 0.20
META_SEMANAL = 0.005   # 0,50%
TICKER = "BOVA11.SA"

# ---------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------

def prob_exercicio(S, K, T, r, sigma, tipo):
    try:
        if T <= 0:
            return 0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if tipo == "CALL":
            return norm.cdf(d2)
        else:
            return norm.cdf(-d2)

    except:
        return 0


def preco_atual():
    try:
        ativo = yf.Ticker(TICKER)
        hist = ativo.history(period="5d")
        return float(hist["Close"].dropna().iloc[-1])
    except:
        return None


def vencimentos():
    try:
        ativo = yf.Ticker(TICKER)
        return list(ativo.options)
    except:
        return []


def buscar_chain(venc):
    try:
        ativo = yf.Ticker(TICKER)
        return ativo.option_chain(venc)
    except:
        return None


def retorno_liquido(premio, capital):
    bruto = premio / capital
    liquido = (bruto - TAXAS) * (1 - IR)
    return liquido


def score_operacao(retorno, prob):
    return (retorno * 100) + (prob * 100)


# ---------------------------------------------------
# APP
# ---------------------------------------------------

def main():

    st.title("📈 BOVA11 Wheel Strategy Pro")
    st.caption("Somente BOVA11 | PUT e CALL semanal | Meta líquida 0,50%")

    operacao = st.sidebar.selectbox(
        "Tipo de Operação",
        ["PUT", "CALL"]
    )

    # ---------------------------------------------------
    # PREÇO ATUAL
    # ---------------------------------------------------
    preco = preco_atual()

    if preco is None:
        st.error("Erro ao buscar preço do BOVA11.")
        return

    st.metric("Preço Atual BOVA11", f"R$ {preco:.2f}")

    # ---------------------------------------------------
    # VENCIMENTOS
    # ---------------------------------------------------
    exps = vencimentos()

    if not exps:
        st.error("Yahoo Finance não retornou vencimentos hoje.")
        return

    hoje = datetime.now()

    validos = []

    for v in exps:
        try:
            data_v = datetime.strptime(v, "%Y-%m-%d")
            dias = (data_v - hoje).days

            if 1 <= dias <= 15:
                validos.append(v)

        except:
            pass

    if not validos:
        st.warning("Nenhum vencimento semanal encontrado.")
        return

    venc = st.selectbox("Escolha o vencimento", validos)

    # ---------------------------------------------------
    # OPTION CHAIN
    # ---------------------------------------------------
    chain = buscar_chain(venc)

    if chain is None:
        st.error("Erro ao carregar opções.")
        return

    if operacao == "PUT":
        tabela = chain.puts.copy()
    else:
        tabela = chain.calls.copy()

    if tabela.empty:
        st.warning("Sem opções disponíveis.")
        return

    # ---------------------------------------------------
    # PROCESSAMENTO
    # ---------------------------------------------------
    T = (datetime.strptime(venc, "%Y-%m-%d") - hoje).days / 365

    lista = []

    for _, row in tabela.iterrows():

        try:
            strike = float(row["strike"])

            bid = float(row["bid"]) if pd.notna(row["bid"]) else 0
            ask = float(row["ask"]) if pd.notna(row["ask"]) else 0
            last = float(row["lastPrice"]) if pd.notna(row["lastPrice"]) else 0

            premio = 0

            if bid > 0:
                premio = bid
            elif last > 0:
                premio = last
            elif ask > 0:
                premio = ask

            if premio <= 0:
                continue

            capital = strike if operacao == "PUT" else preco

            retorno = retorno_liquido(premio, capital)

            if retorno < META_SEMANAL:
                continue

            prob = prob_exercicio(
                preco,
                strike,
                T,
                SELIC,
                VOL,
                operacao
            )

            score = score_operacao(retorno, prob)

            lista.append({
                "Contrato": row["contractSymbol"],
                "Strike": strike,
                "Prêmio": premio,
                "Retorno Líquido (%)": retorno * 100,
                "Probabilidade (%)": prob * 100,
                "Score": score
            })

        except:
            pass

    # ---------------------------------------------------
    # RESULTADO
    # ---------------------------------------------------
    if not lista:
        st.warning("Nenhuma operação dentro da meta hoje.")
        return

    df = pd.DataFrame(lista)

    df = df.sort_values(by="Score", ascending=False).head(3)

    df["Strike"] = df["Strike"].map(lambda x: f"R$ {x:.2f}")
    df["Prêmio"] = df["Prêmio"].map(lambda x: f"R$ {x:.2f}")
    df["Retorno Líquido (%)"] = df["Retorno Líquido (%)"].map(lambda x: f"{x:.2f}%")
    df["Probabilidade (%)"] = df["Probabilidade (%)"].map(lambda x: f"{x:.2f}%")
    df["Score"] = df["Score"].map(lambda x: f"{x:.2f}")

    st.subheader("🏆 TOP 3 Oportunidades")

    st.dataframe(df, use_container_width=True)

    st.success("Atualiza automaticamente ao abrir.")

    with st.expander("Debug"):
        st.write("Vencimentos encontrados:", exps)


if __name__ == "__main__":
    main()
