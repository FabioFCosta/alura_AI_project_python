import yfinance as yf
import streamlit as st
import matplotlib.pyplot as plt
import json
import re
from datetime import datetime, date

from agents import orquestrar_agentes, criar_evento_google_calendar

#  helpers


@st.cache_data(ttl=300)
def get_agent_data(ticker_simples, data_hoje):
    return orquestrar_agentes(ticker=ticker_simples, data_de_hoje=data_hoje)


def parse_resumo(resumo_json_str):
    if isinstance(resumo_json_str, str):
        try:
            match = re.search(r'\{.*\}', resumo_json_str, re.DOTALL)
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            st.error("Erro ao interpretar o resumo financeiro.")
    elif isinstance(resumo_json_str, dict):
        return resumo_json_str
    else:
        st.error("Formato inesperado para o resumo financeiro.")
    return {}

# Gerar relatório


def gerar_relatorio(selected_option: str):
    st.subheader("📋 Notícias importantes")

    if 'relatorio_data' not in st.session_state:
        with st.spinner("Buscando as últimas notícias sobre o ativo..."):
            try:
                ticker_simples = selected_option.replace(".SA", "")
                data_hoje = datetime.today().strftime("%d/%m/%Y")

                resposta_agentes = get_agent_data(ticker_simples, data_hoje)
                resumo = parse_resumo(resposta_agentes.get('resumo'))

                st.session_state.relatorio_data = {
                    'resumo': resumo,
                    'resposta_agentes': resposta_agentes
                }

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o relatório: {e}")
                st.session_state.mostrar_relatorio = False
                return

    relatorio_data = st.session_state.relatorio_data
    resumo = relatorio_data['resumo']
    resposta_agentes = relatorio_data['resposta_agentes']

    informacoes = resumo.get('outros_pontos', [])
    for info in informacoes:
        st.write(f"- {info}")

    pagamentos = resumo.get("pagamentos_dividendos", [])
    if pagamentos:
        st.markdown("### 🗓 Pagamentos de Dividendos e JCP")
        for idx, pag in enumerate(pagamentos):
            titulo = f"Pagamento de {pag.get('tipo', 'dividendo')}"
            data_inicio = pag.get("data_pagamento")
            data_fim = data_inicio
            st.write(
                f"📌 {titulo} — {data_inicio} — Valor: {pag.get('valor', 'N/A')}")

            if st.button(f"📅 Add ao Google Calendar", key=f"cal_btn_{idx}"):
                try:
                    criar_evento_google_calendar(
                        titulo=titulo,
                        data_inicio=f"{data_inicio}T09:00:00",
                        data_fim=f"{data_fim}T10:00:00",
                    )
                    st.success("✅ Evento adicionado ao calendário!")
                except Exception as e:
                    st.error(f"Erro ao adicionar: {e}")

    resultados = resumo.get("resultados_divulgados", [])
    if resultados:
        st.markdown("### 📊 Resultados divulgados")
        for res in resultados:
            st.write(
                f"📌 Resultado {res.get('referente_a')} em {res.get('data', 'N/A')}, Lucro Líquido: {res.get('lucro_liquido', 'N/A')}")

    if resposta_agentes.get("relatorio"):
        st.subheader("📋 Relatórios")
        with st.expander("Ver relatório completo"):
            st.markdown(resposta_agentes.get("relatorio"))

    if resposta_agentes.get("resultados"):
        with st.expander("Ver últimos resultados"):
            st.markdown(resposta_agentes.get("resultados"))

# Seção principal


def main():
    st.title("📊 Cotação + Histórico + Relatório")

    tickers = ['PETR4', 'CMIG4', 'BBAS3', 'IVVB11']
    coins = ['BTC-USD']
    all_choices = [f"{ticker}.SA" for ticker in tickers] + coins
    selected_option = st.sidebar.selectbox('Selecione o papel:', all_choices)

    start_date = st.sidebar.date_input(
        "Data de início:", value=date(2024, 1, 1), min_value=date(2000, 1, 1), max_value=date.today()
    )
    end_date = st.sidebar.date_input(
        "Data de fim:", value=date.today(), min_value=start_date, max_value=date.today()
    )

    st.subheader(f"📈 Último preço de {selected_option}")
    ticker = yf.Ticker(selected_option)
    latest = ticker.history(period='1d', interval='1m')
    if not latest.empty:
        current_price = latest['Close'].iloc[-1]
        st.metric(label="Preço atual", value=f"R$ {current_price:.2f}")
    else:
        st.warning("Não foi possível obter a cotação em tempo real.")

    if start_date >= end_date:
        st.error("A data de início deve ser anterior à data de fim.")
        return

    if selected_option in [f"{t}.SA" for t in tickers]:
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

    st.subheader(f"📉 Histórico de {selected_option} + Indicadores Técnicos")
    hist = yf.download(selected_option, start=start_date, end=end_date)

    if not hist.empty:
        hist['SMA20'] = hist['Close'].rolling(window=20).mean()
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        hist['RSI'] = 100 - (100 / (1 + rs))

        fig_price, ax_price = plt.subplots()
        ax_price.plot(hist['Close'], label='Close', color='blue')
        ax_price.plot(hist['SMA20'], label='SMA 20', color='orange')
        ax_price.set_title(f'{selected_option} - Preço e Média Móvel')
        ax_price.legend()
        ax_price.grid(True)
        st.pyplot(fig_price)

        fig_rsi, ax_rsi = plt.subplots()
        ax_rsi.plot(hist['RSI'], label='RSI', color='purple')
        ax_rsi.axhline(70, linestyle='--', color='red', label='Sobrecomprado')
        ax_rsi.axhline(30, linestyle='--', color='green', label='Sobrevendido')
        ax_rsi.set_title('Índice de Força Relativa (RSI)')
        ax_rsi.legend()
        ax_rsi.grid(True)
        st.pyplot(fig_rsi)

        try:
            st.markdown(f"""
                **Resumo de Indicadores - {selected_option}**
                - 🔹 Último preço: R$ {hist['Close'].iloc[-1]:.2f}
                - 🔸 Média Móvel 20 dias: R$ {hist['SMA20'].iloc[-1]:.2f}
                - 🟣 RSI (14 dias): {hist['RSI'].iloc[-1]:.2f}
            """)
        except Exception as e:
            st.error(f"Erro ao gerar resumo de indicadores: {e}")

        if 'mostrar_relatorio' not in st.session_state:
            st.session_state.mostrar_relatorio = False

        if st.button(f'Gerar Relatório para {selected_option}'):
            st.session_state.mostrar_relatorio = True

        if st.session_state.mostrar_relatorio:
            gerar_relatorio(selected_option)

    else:
        st.info(
            f"Sem dados históricos para {selected_option} no período selecionado.")


# Execução
if __name__ == "__main__":
    main()
