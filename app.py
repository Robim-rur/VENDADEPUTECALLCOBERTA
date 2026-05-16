import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import ta
import plotly.graph_objects as go

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="Crypto Probability Engine",
    layout="wide"
)

# =========================================================
# TITLE
# =========================================================

st.title("🧠 Crypto Probability Engine")

st.markdown("""
Motor probabilístico estrutural para:

- BNB
- XRP
- LINK
- SOLANA
- ETHEREUM

O sistema mede:

- tendência
- força
- momentum
- compressão
- volatilidade
- comportamento histórico semelhante

E responde:

# 👉 Qual a chance matemática do ativo subir +X%?
""")

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("⚙️ Configurações")

ativos = {
    "Ethereum (ETH)": "ETH-USD",
    "Solana (SOL)": "SOL-USD",
    "BNB": "BNB-USD",
    "XRP": "XRP-USD",
    "Chainlink (LINK)": "LINK-USD"
}

ativo_nome = st.sidebar.selectbox(
    "Escolha o ativo",
    list(ativos.keys())
)

ticker = ativos[ativo_nome]

period = st.sidebar.selectbox(
    "Histórico",
    ["2y", "5y", "10y"],
    index=2
)

target_gain = st.sidebar.slider(
    "Gain alvo (%)",
    1.0,
    15.0,
    3.0,
    0.5
)

future_bars = st.sidebar.slider(
    "Máximo candles futuros",
    1,
    30,
    10
)

# =========================================================
# DATA
# =========================================================

@st.cache_data
def load_data(ticker_symbol, period_selected):

    df = yf.download(
        ticker_symbol,
        period=period_selected,
        interval="1d",
        auto_adjust=True,
        progress=False
    )

    # Corrige MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    cols = ["Open", "High", "Low", "Close", "Volume"]

    df = df[cols].copy()

    # Conversão numérica
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df.dropna(inplace=True)

    # Reset index
    df.reset_index(inplace=True)

    return df

df = load_data(ticker, period)

# =========================================================
# VALIDAÇÃO
# =========================================================

if len(df) < 250:

    st.error("Poucos dados para análise.")

    st.stop()

# =========================================================
# INDICADORES
# =========================================================

close = df["Close"].astype(float)
high = df["High"].astype(float)
low = df["Low"].astype(float)
volume = df["Volume"].astype(float)

# =========================================================
# EMAS
# =========================================================

df["EMA21"] = ta.trend.ema_indicator(close, window=21)
df["EMA50"] = ta.trend.ema_indicator(close, window=50)
df["EMA200"] = ta.trend.ema_indicator(close, window=200)

# =========================================================
# ADX
# =========================================================

try:

    adx = ta.trend.ADXIndicator(
        high=high,
        low=low,
        close=close,
        window=14
    )

    df["ADX"] = adx.adx()
    df["DI_POS"] = adx.adx_pos()
    df["DI_NEG"] = adx.adx_neg()

except Exception as e:

    st.error(f"Erro no ADX: {e}")

    df["ADX"] = np.nan
    df["DI_POS"] = np.nan
    df["DI_NEG"] = np.nan

# =========================================================
# ATR
# =========================================================

atr = ta.volatility.AverageTrueRange(
    high=high,
    low=low,
    close=close,
    window=14
)

df["ATR"] = atr.average_true_range()

# =========================================================
# RSI
# =========================================================

df["RSI"] = ta.momentum.rsi(close, window=14)

# =========================================================
# BOLLINGER
# =========================================================

bb = ta.volatility.BollingerBands(
    close=close,
    window=20,
    window_dev=2
)

df["BB_WIDTH"] = (
    (bb.bollinger_hband() - bb.bollinger_lband())
    / close
)

# =========================================================
# VOLUME MÉDIA
# =========================================================

df["VOL_MA20"] = volume.rolling(20).mean()

# =========================================================
# REMOVE NAN
# =========================================================

df.dropna(inplace=True)

# =========================================================
# CURRENT STRUCTURE
# =========================================================

latest = df.iloc[-1]

# =========================================================
# SCORE
# =========================================================

score = 0

details = []

# =========================================================
# TENDÊNCIA
# =========================================================

if latest["Close"] > latest["EMA21"]:
    score += 10
    details.append(("Preço acima EMA21", "✅ +10"))
else:
    details.append(("Preço acima EMA21", "❌"))

if latest["EMA21"] > latest["EMA50"]:
    score += 15
    details.append(("EMA21 acima EMA50", "✅ +15"))
else:
    details.append(("EMA21 acima EMA50", "❌"))

if latest["EMA50"] > latest["EMA200"]:
    score += 20
    details.append(("EMA50 acima EMA200", "✅ +20"))
else:
    details.append(("EMA50 acima EMA200", "❌"))

# =========================================================
# FORÇA
# =========================================================

if latest["ADX"] > 22:
    score += 15
    details.append(("ADX forte", "✅ +15"))
else:
    details.append(("ADX forte", "❌"))

if latest["DI_POS"] > latest["DI_NEG"]:
    score += 10
    details.append(("DI+ acima DI−", "✅ +10"))
else:
    details.append(("DI+ acima DI−", "❌"))

# =========================================================
# MOMENTUM
# =========================================================

if latest["RSI"] > 55:
    score += 10
    details.append(("RSI momentum", "✅ +10"))
else:
    details.append(("RSI momentum", "❌"))

# =========================================================
# VOLUME
# =========================================================

if latest["Volume"] > latest["VOL_MA20"]:
    score += 10
    details.append(("Volume acima média", "✅ +10"))
else:
    details.append(("Volume acima média", "❌"))

# =========================================================
# COMPRESSÃO
# =========================================================

bb_mean = df["BB_WIDTH"].rolling(50).mean().iloc[-1]

if latest["BB_WIDTH"] < bb_mean:
    score += 10
    details.append(("Compressão volatilidade", "✅ +10"))
else:
    details.append(("Compressão volatilidade", "❌"))

# =========================================================
# HISTORICAL MATCH ENGINE
# =========================================================

historical = []

for i in range(250, len(df) - future_bars):

    row = df.iloc[i]

    local_score = 0

    if row["Close"] > row["EMA21"]:
        local_score += 10

    if row["EMA21"] > row["EMA50"]:
        local_score += 15

    if row["EMA50"] > row["EMA200"]:
        local_score += 20

    if row["ADX"] > 22:
        local_score += 15

    if row["DI_POS"] > row["DI_NEG"]:
        local_score += 10

    if row["RSI"] > 55:
        local_score += 10

    if row["Volume"] > row["VOL_MA20"]:
        local_score += 10

    local_bb_mean = (
        df["BB_WIDTH"]
        .rolling(50)
        .mean()
        .iloc[i]
    )

    if row["BB_WIDTH"] < local_bb_mean:
        local_score += 10

    similarity = abs(local_score - score)

    future = df.iloc[i + 1:i + 1 + future_bars]

    target = row["Close"] * (1 + target_gain / 100)

    hit = (future["High"] >= target).any()

    historical.append({
        "score": local_score,
        "similarity": similarity,
        "hit": hit
    })

hist_df = pd.DataFrame(historical)

# =========================================================
# FILTRO SIMILARIDADE
# =========================================================

similar_df = hist_df[
    hist_df["similarity"] <= 5
].copy()

total_cases = len(similar_df)

wins = similar_df["hit"].sum()

if total_cases > 0:
    probability = (wins / total_cases) * 100
else:
    probability = 0

# =========================================================
# DASHBOARD
# =========================================================

st.header(f"🎯 Resultado Atual — {ativo_nome}")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Score Estrutural",
    f"{score}/100"
)

col2.metric(
    "Casos Similares",
    total_cases
)

col3.metric(
    f"Chance de +{target_gain:.1f}%",
    f"{probability:.2f}%"
)

# =========================================================
# INTERPRETAÇÃO
# =========================================================

st.header("🧠 Interpretação")

if probability >= 70:

    st.success(f"""
Estrutura historicamente MUITO forte.

Chance histórica de atingir +{target_gain:.1f}%:
{probability:.1f}%
""")

elif probability >= 60:

    st.warning(f"""
Estrutura moderadamente positiva.

Existe vantagem estatística.
""")

else:

    st.error(f"""
Estrutura estatisticamente fraca no momento.
""")

# =========================================================
# DETALHES
# =========================================================

st.header("📋 Componentes da Estrutura")

details_df = pd.DataFrame(
    details,
    columns=["Fator", "Status"]
)

st.dataframe(
    details_df,
    use_container_width=True,
    hide_index=True
)

# =========================================================
# GRÁFICO
# =========================================================

st.header("📈 Gráfico")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Date"],
    y=df["Close"],
    name="Preço"
))

fig.add_trace(go.Scatter(
    x=df["Date"],
    y=df["EMA21"],
    name="EMA21"
))

fig.add_trace(go.Scatter(
    x=df["Date"],
    y=df["EMA50"],
    name="EMA50"
))

fig.add_trace(go.Scatter(
    x=df["Date"],
    y=df["EMA200"],
    name="EMA200"
))

fig.update_layout(
    height=700
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# =========================================================
# WARNING
# =========================================================

st.markdown("---")

st.warning("""
IMPORTANTE:

Este modelo NÃO prevê o futuro.

Ele mede:

- estruturas históricas semelhantes
- comportamento posterior
- probabilidade condicional

Ou seja:

é um motor estatístico,
não uma previsão absoluta.
""")
