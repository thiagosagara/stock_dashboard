import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.grid import grid
from scipy.stats import linregress

def get_price_target(ticker):
    """
    Obtém o preço atual e o preço alvo médio de uma ação.
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    current_price = info.get('regularMarketPrice', None)
    target_price = info.get('targetMeanPrice', None)

    if current_price is None or target_price is None:
        return None, None, "sem dados"

    if current_price < target_price:
        classification = "reversão"
    else:
        classification = "acima"

    return current_price, target_price, classification

def load_ticker_list():
    return pd.read_csv("tickers_ibra.csv", index_col=0)

def fetch_stock_data(tickers, start_date, end_date):
    data = yf.download(tickers, start=start_date, end=end_date)

    if "Adj Close" in data:
        prices = data["Adj Close"]
    elif "Close" in data:
        prices = data["Close"]
    else:
        st.error("Os dados retornados não contêm preços válidos.")
        return None

    if isinstance(prices, pd.Series):
        prices = prices.to_frame()

    prices.columns = prices.columns.str.rstrip(".SA")
    return prices

def fetch_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info

    try:
        return {
            'PE': info.get('trailingPE', None),
            'PEG': info.get('pegRatio', None),
            'EV_EBITDA': info.get('enterpriseToEbitda', None),
            'PB': info.get('priceToBook', None),
            'NET_MARGIN': info.get('profitMargins', None) * 100 if info.get('profitMargins') else None,
            'DIV_YIELD': info.get('dividendYield', None) * 100 if info.get('dividendYield') else None,
            'ROE': info.get('returnOnEquity', None) * 100 if info.get('returnOnEquity') else None,
            'CURRENT_PRICE': info.get('regularMarketPrice', None)
        }
    except:
        return {
            'PE': None, 'PEG': None, 'EV_EBITDA': None,
            'NET_MARGIN': None, 'DIV_YIELD': None
        }

def get_metric_classification(metric, value):
    """
    Retorna a classificação para cada métrica.
    """
    if value is None:
        return "N/A"

    classifications = {
        'PE': lambda x: "bom" if x < 10 else "estavel" if x <= 25 else "avaliar",
        'PEG': lambda x: "bom" if x < 1 else "avaliar",
        'EV_EBITDA': lambda x: "bom" if x < 6 else "estavel" if x <= 12 else "avaliar",
        'PB': lambda x: "bom" if x < 1 else "estavel" if x <= 3 else "avaliar",
        'DIV_YIELD': lambda x: "bom" if x > 5 else "estavel" if x >= 2 else "avaliar",
        'ROE': lambda x: "bom" if x > 20 else "estavel" if x >= 10 else "avaliar",
        'NET_MARGIN': lambda x: "bom" if x > 15 else "estavel" if x >= 5 else "avaliar"
    }

    return classifications.get(metric, lambda x: "N/A")(value)

def get_metric_help(metric):
    """
    Retorna o texto de ajuda para cada métrica.
    """
    helps = {
        'P/L': "Preço Ação/Lucro. Resultado mostra quanto tempo (anos) o investidor recebera seu investimento. Menor melhor",
        'PEG': "Preco/Taxa de crescimento esperado. Resultado menor que 1 mostra uma ação esta subvalor, pois seu retorno vai ser mais rapido. Menor melhor",
        'EV/EBITDA': "Valor de mercado / lucro operacional. Resultado mostra quantas vezes o valor de uma empresa tem do ebitda. Menor melhor.",
        'P/VPA': "Preço/valor patrimonial ação. Resultado mostra quantas vezes do valor contabio o mercado esta disposto a pagar por ação. Menor melhor.",
        'ROE': "Retorno sobre o patrimonio liquido. Quandos % uma empresa gera de lucro liquido. Maior melhor",
        'Margem Líq.': "Quando uma empresa teve de margem de lucro. Maior melhor.",
        'Div. Yield': "Quando uma empresa paga de dividendos para os acionistas. Maior melhor."
    }
    return helps.get(metric, "")

    classifications = {
        'PE': lambda x: "baixo" if x < 10 else "estável" if x <= 25 else "alto",
        'PEG': lambda x: "baixo" if x < 1 else "alto",
        'EV_EBITDA': lambda x: "baixo" if x < 6 else "estável" if x <= 12 else "alto",
        'PB': lambda x: "baixo" if x < 1 else "estável" if x <= 3 else "alto",
        'DIV_YIELD': lambda x: "alto" if x > 5 else "estável" if x >= 2 else "baixo",
        'ROE': lambda x: "alto" if x > 20 else "estável" if x >= 10 else "baixo",
        'NET_MARGIN': lambda x: "alto" if x > 15 else "estável" if x >= 5 else "baixo"
    }

    return classifications.get(metric, lambda x: "N/A")(value)

def fetch_ibov_data(start_date, end_date):
    ibov_data = yf.download("^BVSP", start=start_date, end=end_date)

    if "Adj Close" in ibov_data:
        return ibov_data["Adj Close"]
    elif "Close" in ibov_data:
        return ibov_data["Close"]

    st.warning("Não foi possível obter os dados do IBOV.")
    return None

def build_sidebar():
    st.image("images/logo-250-100-transparente.png")

    ticker_list = load_ticker_list()
    selected_tickers = st.multiselect("Selecione as Empresas", options=ticker_list, placeholder="Códigos")
    tickers = [t + ".SA" for t in selected_tickers]

    start_date = st.date_input("De", value=datetime(2023, 1, 2), format="DD/MM/YYYY")
    end_date = st.date_input("Até", value=datetime.today(), format="DD/MM/YYYY")

    if not tickers:
        return None, None, None

    prices = fetch_stock_data(tickers, start_date, end_date)
    if prices is None:
        return None, None, None

    fundamentals = {ticker: fetch_fundamentals(ticker) for ticker in tickers}

    ibov_prices = fetch_ibov_data(start_date, end_date)
    if ibov_prices is not None:
        prices["IBOV"] = ibov_prices

    return tickers, prices, fundamentals

def build_main(tickers, prices, fundamentals):
    weights = np.ones(len(tickers)) / len(tickers)
    prices["portfolio"] = prices.drop("IBOV", axis=1) @ weights

    norm_prices = 100 * prices / prices.iloc[0]
    returns = prices.pct_change()[1:]
    vols = returns.std() * np.sqrt(252)
    rets = (norm_prices.iloc[-1] - 100) / 100

    grid_layout = grid(5, 5, 5, 5, 5, 5, vertical_align="top")

    for ticker in prices.columns:
        container = grid_layout.container(border=True)
        col_img, col_title = container.columns([1, 2])

        if ticker == "portfolio":
            col_img.image("images/pie-chart-dollar-svgrepo-com.svg", use_column_width=True)
        elif ticker == "IBOV":
            col_img.image("images/pie-chart-svgrepo-com.svg", use_column_width=True)
        else:
            col_img.image(
                f"https://raw.githubusercontent.com/thefintz/icones-b3/main/icones/{ticker}.png",
                use_column_width=True)

        col_title.subheader(ticker, divider="red")

        col_b = container.columns([1])[0]

        with col_b:
            # Retorno e Volatilidade
            st.markdown(
                f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                f"<span style='font-size:14px; font-weight:bold;'>Retorno:</span>"
                f"<span style='font-size:18px; color:red; font-weight:bold;'>{rets[ticker]:.2%}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Coeficiente de Hurst
            if ticker not in ["portfolio", "IBOV"]:
                current_price, target_price, price_class = get_price_target(ticker + ".SA")
                if current_price and target_price:
                    color = "green" if price_class == "reversão" else "red"
                    st.markdown(
                        f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                        f"<span style='font-size:14px; font-weight:bold;'>Preço Atual/Alvo:</span>"
                        f"<span style='font-size:18px; color:{color}; font-weight:bold;'>{current_price:.2f}/{target_price:.2f} ({price_class})</span>"
                        f"</div>",
                    unsafe_allow_html=True
                )

                # Dados Fundamentalistas
                fund = fundamentals.get(ticker + ".SA", {})
                metrics = [
                    ('P/L', fund['PE'], 'PE'),
                    ('PEG', fund['PEG'], 'PEG'),
                    ('EV/EBITDA', fund['EV_EBITDA'], 'EV_EBITDA'),
                    ('P/VPA', fund['PB'], 'PB'),
                    ('ROE', fund['ROE'], 'ROE'),
                    ('Margem Líq.', fund['NET_MARGIN'], 'NET_MARGIN'),
                    ('Div. Yield', fund['DIV_YIELD'], 'DIV_YIELD')
                ]

                for label, value, metric_type in metrics:
                    if value is not None:
                        classification = get_metric_classification(metric_type, value) if metric_type else ""
                        classification_text = f" ({classification})" if classification != "N/A" else ""
                        color = "red" if "avaliar" in classification_text else "green" if "bom" in classification_text else "orange"

                        # Adiciona o container com tooltip e força largura total
                        help_text = get_metric_help(label)
                        st.markdown(
                            f"""
                            <style>
                                [data-testid="stMarkdownContainer"] {{
                                    width: 100%;
                                }}
                            </style>
                            <div style='display:flex; justify-content:space-between; width:100%;'>
                                <div style='font-size:14px; font-weight:bold;'>{label}:</div>
                                <div style='font-size:18px; color:{color}; font-weight:bold; margin-left:auto;'>{value:.2f}{classification_text}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                            help=help_text
                        )

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

st.set_page_config(
    page_title="Meu Dashboard",
    page_icon="📊",
    layout="wide"
)

with st.sidebar:
    tickers, prices, fundamentals = build_sidebar()

st.title("Python para Investidores")

if tickers:
    build_main(tickers, prices, fundamentals)
