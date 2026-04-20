import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="BOVA11 Expert - Wheel Strategy",
    layout="wide"
)

# ---------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------
def calculate_probability(S, K, T, r, sigma, option_type="call"):
    """
    Aproximação Black-Scholes para chance de exercício
    """
    try:
        if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
            return 0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            return norm.cdf(d2)
        else:
            return norm.cdf(-d2)

    except:
        return 0


def get_current_price():
    """
    Busca preço atual BOVA11
    """
    try:
        asset = yf.Ticker("BOVA11.SA")
        hist = asset.history(period="5d")

        if hist.empty:
            return None

        return float(hist["Close"].dropna().iloc[-1])

    except:
        return None


def get_expirations():
    """
    Busca vencimentos disponíveis
    """
    try:
        asset = yf.Ticker("BOVA11.SA")
        exps = asset.options
        return list(exps)
    except:
        return []


def get_chain(exp):
    """
    Busca chain
    """
    try:
        asset = yf.Ticker("BOVA11.SA")
        return asset.option_chain(exp)
    except:
        return None


# ---------------------------------------------------
# APP
# ---------------------------------------------------
def main():

    st.title("🎯 BOVA11 Expert - Wheel Strategy")
    st.subheader("Venda Coberta / Venda de PUT")

    st.sidebar.header("Configurações")

    op_type = st.sidebar.selectbox(
        "Tipo de Operação",
        [
            "Venda de PUT",
            "Venda de CALL"
        ]
    )

    tax_rate = 0.15
    fees = 0.0003
    r = 0.1075
    sigma = 0.20

    # ---------------------------------------------------
    # PREÇO
    # ---------------------------------------------------
    current_price = get_current_price()

    if current_price is None:
        st.error("Não foi possível carregar preço do BOVA11.")
        return

    st.metric("Preço Atual BOVA11", f"R$ {current_price:.2f}")

    # ---------------------------------------------------
    # VENCIMENTOS
    # ---------------------------------------------------
    expirations = get_expirations()

    if not expirations:
        st.error("Yahoo não retornou vencimentos hoje.")
        return

    today = datetime.now()

    valid_exp = []

    for exp in expirations:
        try:
            d = datetime.strptime(exp, "%Y-%m-%d")
            days = (d - today).days

            # faixa ampliada
            if 1 <= days <= 45:
                valid_exp.append(exp)

        except:
            pass

    if not valid_exp:
        st.warning("Nenhum vencimento encontrado entre 1 e 45 dias.")
        st.write("Vencimentos disponíveis:", expirations)
        return

    selected_exp = st.selectbox("Escolha vencimento", valid_exp)

    # ---------------------------------------------------
    # CHAIN
    # ---------------------------------------------------
    chain = get_chain(selected_exp)

    if chain is None:
        st.error("Falha ao carregar opções.")
        return

    if op_type == "Venda de PUT":
        options = chain.puts.copy()
        option_side = "put"
    else:
        options = chain.calls.copy()
        option_side = "call"

    if options.empty:
        st.warning("Sem opções disponíveis.")
        return

    # ---------------------------------------------------
    # PROCESSAMENTO
    # ---------------------------------------------------
    T = (datetime.strptime(selected_exp, "%Y-%m-%d") - today).days / 365

    rows = []

    for _, row in options.iterrows():

        try:
            strike = float(row["strike"])

            bid = float(row["bid"]) if pd.notna(row["bid"]) else 0
            ask = float(row["ask"]) if pd.notna(row["ask"]) else 0
            last = float(row["lastPrice"]) if pd.notna(row["lastPrice"]) else 0

            # melhor prêmio possível
            premium = 0

            if bid > 0:
                premium = bid
            elif last > 0:
                premium = last
            elif ask > 0:
                premium = ask

            if premium <= 0:
                continue

            capital = strike if option_side == "put" else current_price

            bruto = premium / capital
            liquido = (bruto - fees) * (1 - tax_rate)

            prob = calculate_probability(
                current_price,
                strike,
                T,
                r,
                sigma,
                option_side
            )

            rows.append(
                {
                    "Contrato": row["contractSymbol"],
                    "Strike": strike,
                    "Prêmio": premium,
                    "Retorno Líquido (%)": liquido * 100,
                    "Prob. Exercício (%)": prob * 100,
                }
            )

        except:
            pass

    # ---------------------------------------------------
    # RESULTADO
    # ---------------------------------------------------
    if not rows:
        st.warning("Nenhuma opção líquida encontrada hoje.")
        return

    df = pd.DataFrame(rows)

    df = df.sort_values(
        by=["Prob. Exercício (%)", "Retorno Líquido (%)"],
        ascending=False
    )

    meta = 0.50

    def color_target(v):
        if v >= meta:
            return "background-color: lightgreen"
        return ""

    st.write("### Ranking das Melhores Oportunidades")

    styled = df.style.format(
        {
            "Strike": "R$ {:.2f}",
            "Prêmio": "R$ {:.2f}",
            "Retorno Líquido (%)": "{:.2f}%",
            "Prob. Exercício (%)": "{:.2f}%"
        }
    ).applymap(
        color_target,
        subset=["Retorno Líquido (%)"]
    )

    st.dataframe(styled, use_container_width=True)

    st.info("Verde = retorno líquido acima de 0,50%.")

    with st.expander("Debug"):
        st.write("Vencimentos encontrados:", expirations)
        st.write("Total de opções processadas:", len(df))


if __name__ == "__main__":
    main()
