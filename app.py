import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="Scanner Semanal TOP 3", layout="wide")

# ---------------------------------------------------
# PARÂMETROS DO USUÁRIO (SEU SETUP)
# ---------------------------------------------------
ATIVOS = ["BOVA11", "BBAS3", "PETR4", "VALE3", "ITUB4"]

TAXA = 0.15
TAXAS_B3 = 0.0003

META_SEMANAL = 0.005  # 0,50%

# ---------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------

def calcular_retorno_liquido(premio, capital):
    bruto = premio / capital
    liquido = (bruto - TAXAS_B3) * (1 - TAXA)
    return liquido


def calcular_score(retorno, distancia):
    """
    Score de equilíbrio:
    - maior retorno = melhor
    - menor distância = melhor
    """
    return (retorno * 100) - (distancia * 10)


def gerar_dados_exemplo():
    """
    ⚠️ Substituir futuramente por dados reais
    """
    np.random.seed(42)

    dados = []

    for ativo in ATIVOS:
        preco = np.random.uniform(20, 150)

        for i in range(10):

            # PUT
            strike_put = preco * np.random.uniform(0.90, 0.98)
            premio_put = np.random.uniform(0.2, 1.2)

            ret_put = calcular_retorno_liquido(premio_put, strike_put)
            dist_put = (preco - strike_put) / preco

            score_put = calcular_score(ret_put, dist_put)

            dados.append({
                "Ativo": ativo,
                "Tipo": "PUT",
                "Preço": preco,
                "Strike": strike_put,
                "Prêmio": premio_put,
                "Retorno": ret_put,
                "Distância": dist_put,
                "Score": score_put
            })

            # CALL
            strike_call = preco * np.random.uniform(1.02, 1.10)
            premio_call = np.random.uniform(0.2, 1.0)

            ret_call = calcular_retorno_liquido(premio_call, preco)
            dist_call = (strike_call - preco) / preco

            score_call = calcular_score(ret_call, dist_call)

            dados.append({
                "Ativo": ativo,
                "Tipo": "CALL",
                "Preço": preco,
                "Strike": strike_call,
                "Prêmio": premio_call,
                "Retorno": ret_call,
                "Distância": dist_call,
                "Score": score_call
            })

    return pd.DataFrame(dados)


def processar():
    df = gerar_dados_exemplo()

    # filtro meta mínima
    df = df[df["Retorno"] >= META_SEMANAL]

    if df.empty:
        return df

    # ordenação
    df = df.sort_values(by="Score", ascending=False)

    # top 3
    df = df.head(3)

    return df


# ---------------------------------------------------
# APP
# ---------------------------------------------------

def main():

    st.title("📈 Scanner Semanal TOP 3")
    st.caption("Wheel Strategy | PUT + CALL | Meta ≥ 0,50% líquido")

    df = processar()

    if df.empty:
        st.warning("Nenhuma oportunidade dentro da meta hoje.")
        return

    # formatação
    df_exibir = df.copy()

    df_exibir["Preço"] = df_exibir["Preço"].map(lambda x: f"R$ {x:.2f}")
    df_exibir["Strike"] = df_exibir["Strike"].map(lambda x: f"R$ {x:.2f}")
    df_exibir["Prêmio"] = df_exibir["Prêmio"].map(lambda x: f"R$ {x:.2f}")
    df_exibir["Retorno"] = df_exibir["Retorno"].map(lambda x: f"{x*100:.2f}%")
    df_exibir["Distância"] = df_exibir["Distância"].map(lambda x: f"{x*100:.2f}%")
    df_exibir["Score"] = df_exibir["Score"].map(lambda x: f"{x:.2f}")

    st.subheader("🏆 TOP 3 Oportunidades")

    st.dataframe(df_exibir, use_container_width=True)

    st.info("Filtro aplicado: ≥ 0,50% líquido semanal")


if __name__ == "__main__":
    main()
