import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
from datetime import date

# Auto-refresh every X seconds
refresh_interval = st.sidebar.slider(
    "Intervalo de atualização (segundos)", 5, 3600, 60)
st_autorefresh(interval=refresh_interval * 1000, key="refresh")

# Title
st.title("📊 Cotação em Tempo Quase Real + Histórico + Relatório")

# Ticker selection
tickers = ['PETR4', 'CMIG4', 'BBAS3', 'IVVB11']
coins = ['BTC-USD']
all_choices = tickers + coins

selected_option = st.sidebar.selectbox('Selecione o papel:', all_choices)

if selected_option in tickers:
    selected_option = f"{selected_option}.SA"

# Date selection
start_date = st.sidebar.date_input(
    "Data de início:", value=date(2024, 1, 1), min_value=date(2000, 1, 1), max_value=date.today()
)
end_date = st.sidebar.date_input(
    "Data de fim:", value=date.today(), min_value=start_date, max_value=date.today()
)

# Cotação atual
st.subheader(f"📈 Último preço de {selected_option}")
ticker = yf.Ticker(selected_option)
latest = ticker.history(period='1d', interval='1m')

if not latest.empty:
    current_price = latest['Close'].iloc[-1]
    st.metric(label="Preço atual", value=f"R$ {current_price:.2f}")
else:
    st.warning("Não foi possível obter a cotação em tempo quase real.")

# Validação de datas
if start_date >= end_date:
    st.error("A data de início deve ser anterior à data de fim.")
else:
    if selected_option in tickers:
        # Gráfico do IBOV
        st.subheader("Histórico do IBOVESPA")
        bvsp = yf.download('^BVSP', start=start_date, end=end_date)

        if not bvsp.empty:
            fig1, ax1 = plt.subplots()
            ax1.plot(bvsp['Close'], label='IBOV')
            ax1.set_title('IBOVESPA (^BVSP)')
            ax1.set_xlabel('Data')
            ax1.set_ylabel('Close')
            ax1.grid(True)
            st.pyplot(fig1)
        else:
            st.info("Sem dados históricos para o IBOVESPA no período selecionado.")

    # Gráfico do papel selecionado
    st.subheader(f"📉 Histórico de {selected_option} + Indicadores Técnicos")

    hist = yf.download(selected_option, start=start_date, end=end_date)

    if not hist.empty:
        # Indicadores
        hist['SMA20'] = hist['Close'].rolling(window=20).mean()

        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        hist['RSI'] = 100 - (100 / (1 + rs))

        # Gráfico de preço + média móvel
        fig_price, ax_price = plt.subplots()
        ax_price.plot(hist['Close'], label='Close', color='blue')
        ax_price.plot(hist['SMA20'], label='SMA 20', color='orange')
        ax_price.set_title(f'{selected_option} - Preço e Média Móvel')
        ax_price.set_xlabel('Data')
        ax_price.set_ylabel('Preço')
        ax_price.legend()
        ax_price.grid(True)
        st.pyplot(fig_price)

        # Gráfico do RSI
        fig_rsi, ax_rsi = plt.subplots()
        ax_rsi.plot(hist['RSI'], label='RSI', color='purple')
        ax_rsi.axhline(70, linestyle='--', color='red', label='Sobrecomprado')
        ax_rsi.axhline(30, linestyle='--', color='green', label='Sobrevendido')
        ax_rsi.set_title('Índice de Força Relativa (RSI)')
        ax_rsi.set_xlabel('Data')
        ax_rsi.set_ylabel('RSI')
        ax_rsi.legend()
        ax_rsi.grid(True)
        st.pyplot(fig_rsi)

        # 🔍 Geração do Relatório Técnico
        st.subheader("📋 Relatório Técnico")

        try:
            last_price = float(hist['Close'].dropna().iloc[-1])
            sma_value = float(hist['SMA20'].dropna().iloc[-1])
            rsi_value = float(hist['RSI'].dropna().iloc[-1])

            report = f"""
            **Resumo de Indicadores - {selected_option}**
            - 🔹 Último preço: R$ {last_price:.2f}
            - 🔸 Média Móvel 20 dias: R$ {sma_value:.2f}
            - 🟣 RSI (14 dias): {rsi_value:.2f}
            """

            st.markdown(report)

        except Exception as e:
            st.error(f"Erro ao gerar relatório: {e}")

        st.subheader("📋 Notícias importantes ")
        

    else:
        st.info(
            f"Sem dados históricos para {selected_option} no período selecionado.")
