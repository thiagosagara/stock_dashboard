import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid


def load_ticker_list():
    """Carrega a lista de tickers do arquivo CSV."""
    return pd.read_csv("tickers_ibra.csv", index_col=0)


def fetch_stock_data(tickers, start_date, end_date):
    """Baixa os dados históricos dos tickers e retorna os preços ajustados ou de fechamento."""
    data = yf.download(tickers, start=start_date, end=end_date)

    if "Adj Close" in data:
        prices = data["Adj Close"]
    elif "Close" in data:
        prices = data["Close"]
    else:
        st.error("Os dados retornados não contêm preços válidos.")
        return None

    if isinstance(prices, pd.Series):  # Caso um único ticker seja selecionado
        prices = prices.to_frame()

    prices.columns = prices.columns.str.rstrip(".SA")
    return prices


def fetch_ibov_data(start_date, end_date):
    """Baixa os dados históricos do IBOV e retorna os preços ajustados ou de fechamento."""
    ibov_data = yf.download("^BVSP", start=start_date, end=end_date)

    if "Adj Close" in ibov_data:
        return ibov_data["Adj Close"]
    elif "Close" in ibov_data:
        return ibov_data["Close"]

    st.warning("Não foi possível obter os dados do IBOV.")
    return None


def build_sidebar():
    """Cria a barra lateral do Streamlit com seleção de ativos e período."""
    st.image("images/logo-250-100-transparente.png")

    ticker_list = load_ticker_list()
    selected_tickers = st.multiselect("Selecione as Empresas", options=ticker_list, placeholder="Códigos")
    tickers = [t + ".SA" for t in selected_tickers]

    start_date = st.date_input("De", value=datetime(2023, 1, 2), format="DD/MM/YYYY")
    end_date = st.date_input("Até", value=datetime.today(), format="DD/MM/YYYY")

    if not tickers:
        return None, None

    prices = fetch_stock_data(tickers, start_date, end_date)
    if prices is None:
        return None, None

    ibov_prices = fetch_ibov_data(start_date, end_date)
    if ibov_prices is not None:
        prices["IBOV"] = ibov_prices

    return tickers, prices

def build_main(tickers, prices):
    """Constrói a visualização principal da aplicação."""
    weights = np.ones(len(tickers)) / len(tickers)
    prices["portfolio"] = prices.drop("IBOV", axis=1) @ weights

    norm_prices = 100 * prices / prices.iloc[0]
    returns = prices.pct_change()[1:]
    vols = returns.std() * np.sqrt(252)
    rets = (norm_prices.iloc[-1] - 100) / 100

    # Criando um grid para organizar os ativos
    grid_layout = grid(5, 5, 5, 5, 5, 5, vertical_align="top")

    for ticker in prices.columns:
        container = grid_layout.container(border=True)  # Mantém estrutura organizada

        # 🚀 Criando um layout com imagem e título lado a lado
        col_img, col_title = container.columns([1, 2])

        # Define os ícones corretos ao lado do título
        if ticker == "portfolio":
            col_img.image("images/pie-chart-dollar-svgrepo-com.svg", use_column_width=True)
        elif ticker == "IBOV":
            col_img.image("images/pie-chart-svgrepo-com.svg", use_column_width=True)
        else:
            col_img.image(
                f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png",
                use_column_width=True)

        col_title.subheader(ticker)  # Nome do ativo ao lado do ícone

        # 🚀 Mantendo o Grid e organizando Retorno e Volatilidade no mesmo container
        col_b = container.columns([1])[0]  # Única coluna para métricas

        # 🚀 Empilhando Retorno e Volatilidade no mesmo bloco dentro de col_b
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

    st.subheader("Análises")

    # 🚀 Mantendo os gráficos no grid para maior responsividade
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


# Configuração do Streamlit
st.set_page_config(
    page_title="Meu Dashboard",  # Define o título da aba do navegador
    page_icon="📊",  # Define o ícone da aba do navegador
    layout="wide"  # Usa o layout mais largo
)
# Constrói a interface
with st.sidebar:
    tickers, prices = build_sidebar()

st.title("Python para Investidores")

if tickers:
    build_main(tickers, prices)
