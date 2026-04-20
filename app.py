import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
from datetime import datetime, timedelta

# Configurações iniciais da página
st.set_page_config(page_title="BOVA11 Expert - Wheel Strategy", layout="wide")

def calculate_probability(S, K, T, r, sigma, option_type='call'):
    """Calcula a probabilidade de exercício (Delta aproximado)"""
    if T <= 0: return 0
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if option_type == 'call':
        return norm.cdf(d1)  # Probabilidade de fechar acima do Strike
    else:
        return 1 - norm.cdf(d2) # Probabilidade de fechar abaixo do Strike

def main():
    st.title("🎯 BOVA11 Strategy: Venda Coberta & Put")
    st.subheader("Foco: Máxima Probabilidade de Exercício (Semanais)")

    # Sidebar para parâmetros
    st.sidebar.header("Parâmetros da Estratégia")
    target_monthly_net = 0.02  # 2% ao mês
    tax_rate = 0.15 # 15% IR
    b3_fees = 0.0003 # Estimativa de taxas B3 (Emolumentos)

    op_type = st.sidebar.selectbox("Tipo de Operação", ["Venda de PUT (Lançamento Sintético)", "Venda de CALL (Lançamento Coberto)"])
    
    # Carregando dados do ativo
    asset = yf.Ticker("BOVA11.SA")
    try:
        current_price = asset.history(period="1d")['Close'].iloc[-1]
    except:
        st.error("Erro ao carregar preço do BOVA11. Verifique a conexão.")
        return

    st.metric("Preço Atual BOVA11", f"R$ {current_price:.2f}")

    # Seleção de Vencimentos (Filtro para Semanais)
    expirations = asset.options
    today = datetime.now()
    
    # Filtrar apenas vencimentos próximos (semanais/próximos meses entre 4 e 15 dias úteis)
    weekly_expirations = []
    for exp in expirations:
        days_to_exp = (datetime.strptime(exp, '%Y-%m-%d') - today).days
        if 3 < days_to_exp < 20:
            weekly_expirations.append(exp)

    if not weekly_expirations:
        st.warning("Nenhuma opção semanal/curta encontrada no momento.")
        return

    selected_exp = st.selectbox("Selecione o Vencimento (Foco em Curtos)", weekly_expirations)
    
    # Processamento da Grade de Opções
    opt_chain = asset.option_chain(selected_exp)
    options = opt_chain.puts if "PUT" in op_type else opt_chain.calls
    
    data = []
    T = (datetime.strptime(selected_exp, '%Y-%m-%d') - today).days / 365.0
    r = 0.1075 # Taxa Selic (ajuste conforme o momento)
    sigma = 0.20 # Volatilidade implícita média histórica do BOVA11 (estimada)

    for index, row in options.iterrows():
        strike = row['strike']
        premium = row['lastPrice']
        
        if premium <= 0: continue

        # Cálculo de Retorno Bruto e Líquido
        # Para PUT, o capital garantido é o strike. Para CALL, é o preço atual do ativo.
        capital_base = strike if "PUT" in op_type else current_price
        raw_return = (premium / capital_base)
        
        # Deduzindo taxas e IR
        net_return = (raw_return - b3_fees) * (1 - tax_rate)
        
        # Estimativa de Probabilidade de Exercício
        prob = calculate_probability(
            current_price, strike, T, r, sigma, 
            'call' if "CALL" in op_type else 'put'
        )

        data.append({
            "Símbolo": row['contractSymbol'],
            "Strike": strike,
            "Prêmio": f"R$ {premium:.2f}",
            "Retorno Líquido (%)": net_return * 100,
            "Prob. Exercício": prob * 100
        })

    df = pd.DataFrame(data)
    
    if not df.empty:
        # Ordenar da MAIOR para a MENOR probabilidade
        df = df.sort_values(by="Prob. Exercício", ascending=False)

        # Filtro de Meta: 2% ao mês equivale a aproximadamente 0.5% na semana
        min_weekly_target = 0.005 
        
        st.write("### Ranking de Opções (Maior Probabilidade de Exercício)")
        
        def highlight_target(val):
            color = 'lightgreen' if val >= (min_weekly_target * 100) else 'white'
            return f'background-color: {color}'

        st.dataframe(
            df.style.format({
                "Retorno Líquido (%)": "{:.2f}%",
                "Prob. Exercício": "{:.2f}%"
            }).applymap(highlight_target, subset=['Retorno Líquido (%)']),
            use_container_width=True
        )
        
        st.info(f"💡 Destaque em verde: Opções com retorno líquido superior a 0,50% na semana (Meta de ~2% mês).")
    else:
        st.info("Aguardando dados de mercado para processar a grade.")

if __name__ == "__main__":
    main()
