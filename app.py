import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid


# ==========================
# 🔹 FUNÇÕES AUXILIARES
# ==========================

def load_ticker_list():
    """Carrega a lista de tickers do arquivo CSV para exibição no menu lateral."""
    return pd.read_csv("tickers_ibra.csv", index_col=0)


def fetch_stock_data(tickers, start_date, end_date):
    """
    Baixa os dados históricos dos tickers fornecidos a partir do Yahoo Finance.
    Retorna os preços ajustados ("Adj Close") se disponíveis, senão usa "Close".
    """
    data = yf.download(tickers, start=start_date, end=end_date)

    # Verifica se "Adj Close" existe, senão usa "Close"
    if "Adj Close" in data:
        prices = data["Adj Close"]
    elif "Close" in data:
        prices = data["Close"]
    else:
        st.error("Os dados retornados não contêm preços válidos.")
        return None

    # Se apenas um ticker foi selecionado, converte Series para DataFrame
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    # Remove a extensão ".SA" dos tickers para exibição mais limpa
    prices.columns = prices.columns.str.rstrip(".SA")

    return prices


def fetch_ibov_data(start_date, end_date):
    """
    Baixa os dados históricos do IBOV (Índice Bovespa) do Yahoo Finance.
    Retorna os preços ajustados ("Adj Close") se disponíveis, senão usa "Close".
    """
    ibov_data = yf.download("^BVSP", start=start_date, end=end_date)

    if "Adj Close" in ibov_data:
        return ibov_data["Adj Close"]
    elif "Close" in ibov_data:
        return ibov_data["Close"]

    st.warning("Não foi possível obter os dados do IBOV.")
    return None


# ==========================
# 🔹 BARRA LATERAL (MENU)
# ==========================

def build_sidebar():
    """
    Cria a barra lateral do Streamlit.
    Permite ao usuário selecionar ativos e definir um intervalo de datas.
    """
    # Exibe o logotipo da aplicação
    st.image("images/logo-250-100-transparente.png")

    # Carrega a lista de tickers disponíveis
    ticker_list = load_ticker_list()

    # Menu para seleção de múltiplos tickers
    selected_tickers = st.multiselect("Selecione as Empresas", options=ticker_list, placeholder="Códigos")
    tickers = [t + ".SA" for t in selected_tickers]  # Adiciona ".SA" para identificar ações da B3

    # Campos para seleção de período de análise
    start_date = st.date_input("De", value=datetime(2023, 1, 2), format="DD/MM/YYYY")
    end_date = st.date_input("Até", value=datetime.today(), format="DD/MM/YYYY")

    if not tickers:
        return None, None

    # Baixa os dados das ações selecionadas
    prices = fetch_stock_data(tickers, start_date, end_date)
    if prices is None:
        return None, None

    # Baixa os dados do IBOV e adiciona ao DataFrame
    ibov_prices = fetch_ibov_data(start_date, end_date)
    if ibov_prices is not None:
        prices["IBOV"] = ibov_prices

    return tickers, prices


# ==========================
# 🔹 CONSTRUÇÃO DO DASHBOARD PRINCIPAL
# ==========================

def build_main(tickers, prices):
    """
    Constrói a interface principal da aplicação.
    Exibe os ativos selecionados e gráficos de desempenho.
    """
    # Criação de um portfólio igualitário (pesos iguais para cada ativo)
    weights = np.ones(len(tickers)) / len(tickers)

    # Adiciona uma coluna "portfolio" que representa a média ponderada dos ativos selecionados
    prices["portfolio"] = prices.drop("IBOV", axis=1) @ weights

    # Normaliza os preços para facilitar a comparação percentual
    norm_prices = 100 * prices / prices.iloc[0]

    # Calcula os retornos percentuais diários (exceto o primeiro dia)
    returns = prices.pct_change()[1:]

    # Calcula volatilidade anualizada e retorno acumulado
    vols = returns.std() * np.sqrt(252)
    rets = (norm_prices.iloc[-1] - 100) / 100

    # 🚀 Criando um GRID para exibir os ativos com métricas associadas
    grid_layout = grid(5, 5, 5, 5, 5, 5, vertical_align="top")

    for ticker in prices.columns:
        container = grid_layout.container(border=True)  # Mantém estrutura organizada

        # 🔹 Criando layout com imagem e título lado a lado
        col_img, col_title = container.columns([1, 2])

        # Define os ícones corretos ao lado do título
        if ticker == "portfolio":
            col_img.image("images/pie-chart-dollar-svgrepo-com.svg", use_column_width=True)
        elif ticker == "IBOV":
            col_img.image("images/pie-chart-svgrepo-com.svg", use_column_width=True)
        else:
            col_img.image(
                f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png",
                use_column_width=True
            )

        col_title.subheader(ticker)  # Exibe o nome do ativo ao lado do ícone

        # 🔹 Criando um bloco único para exibir Retorno e Volatilidade
        col_b = container.columns([1])[0]

        with col_b:
            with st.container():
                st.markdown(
                    f"<p style='font-size:14px; font-weight:bold;'>Retorno:</p>"
                    f"<p style='font-size:18px; color:green; font-weight:bold;'>{rets[ticker]:.2%}</p>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"<p style='font-size:14px; font-weight:bold;'>Volatilidade:</p>"
                    f"<p style='font-size:18px; color:red; font-weight:bold;'>{vols[ticker]:.2%}</p>",
                    unsafe_allow_html=True
                )

    # 🔹 Criando os gráficos de análise
    st.subheader("Análises")
    col1, col2 = st.columns([2, 3], gap="large")

    with col1:
        st.subheader("Desempenho Relativo")
        st.line_chart(norm_prices, height=600)

    with col2:
        st.subheader("Risco-Retorno")
        fig = px.scatter(
            x=vols,
            y=rets,
            text=vols.index,
            color=rets / vols,
            color_continuous_scale=px.colors.sequential.Bluered_r
        )

        fig.update_traces(
            textfont_color="white",
            marker=dict(size=45),
            textfont_size=10,
        )

        fig.layout.yaxis.title = "Retorno Total"
        fig.layout.xaxis.title = "Volatilidade (anualizada)"
        fig.layout.height = 600
        fig.layout.xaxis.tickformat = ".0%"
        fig.layout.yaxis.tickformat = ".0%"
        fig.layout.coloraxis.colorbar.title = "Sharpe"

        st.plotly_chart(fig, use_container_width=True)


# ==========================
# 🔹 CONFIGURAÇÃO DO STREAMLIT
# ==========================

st.set_page_config(page_title="Meu Dashboard", page_icon="📊", layout="wide")

# Constrói a interface do menu lateral
with st.sidebar:
    tickers, prices = build_sidebar()

# Exibe o título principal do dashboard
st.title("Python para Investidores")

# Se houver tickers selecionados, constrói a interface principal
if tickers:
    build_main(tickers, prices)
