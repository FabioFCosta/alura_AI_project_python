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
            if data_inicio and data_inicio != "N/A":
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
        for idx, res in enumerate(resultados):
            titulo = f"Divulgação de resultado referente a {res.get('referente_a', '')}"
            data_inicio = res.get("data")
            if data_inicio and data_inicio != "N/A":
                data_fim = data_inicio
                st.write(
                    f"📌 Resultado {res.get('referente_a')} em {res.get('data', 'N/A')}, Lucro Líquido: {res.get('lucro_liquido', 'N/A')}")

                if st.button(f"📅 Add ao Google Calendar", key=f"cal_btt_{idx}"):
                    try:
                        criar_evento_google_calendar(
                            titulo=titulo,
                            data_inicio=f"{data_inicio}T09:00:00",
                            data_fim=f"{data_fim}T10:00:00",
                        )
                        st.success("✅ Evento adicionado ao calendário!")
                    except Exception as e:
                        st.error(f"Erro ao adicionar: {e}")

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

    if 'mostrar_relatorio' not in st.session_state:
        st.session_state.mostrar_relatorio = False

    selected_option = st.sidebar.text_input(
        'Informe o código da ação:', placeholder="EX. PETR4")

    start_date = st.sidebar.date_input(
        "Data de início:", value=date(2024, 1, 1),
        min_value=date(2000, 1, 1),
        max_value=date.today()
    )
    end_date = st.sidebar.date_input(
        "Data de fim:", value=date.today(),
        min_value=start_date,
        max_value=date.today()
    )

    if not selected_option:
        st.markdown(
            "Informe o código da ação na barra lateral para começar a avaliação")
        return

    try:
        # Clean and format ticker symbol
        ticker_code = selected_option.upper().replace(".SA", "")
        ticker_symbol = f"{ticker_code}.SA"
        ticker = yf.Ticker(ticker_symbol)

        # Display current price
        st.subheader(f"📈 Último preço de {ticker_code}")
        latest = ticker.history(period='1d', interval='1m')
        if not latest.empty:
            current_price = latest['Close'].iloc[-1]
            st.metric(label="Preço atual", value=f"R$ {current_price:.2f}")
        else:
            st.warning("Não foi possível obter a cotação em tempo real.")
            return

        if start_date >= end_date:
            st.error("A data de início deve ser anterior à data de fim.")
            return

        hist = yf.download(ticker_symbol, start=start_date, end=end_date)

        if hist.empty:
            st.info(
                f"Sem dados históricos para {ticker_code} no período selecionado.")
            return

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
            plt.close(fig1)

        st.subheader(f"📉 Histórico de {ticker_code} + Indicadores Técnicos")

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
        ax_price.set_title(f'{ticker_code} - Preço e Média Móvel')
        ax_price.legend()
        ax_price.grid(True)
        st.pyplot(fig_price)
        plt.close(fig_price)

        fig_rsi, ax_rsi = plt.subplots()
        ax_rsi.plot(hist['RSI'], label='RSI', color='purple')
        ax_rsi.axhline(70, linestyle='--', color='red', label='Sobrecomprado')
        ax_rsi.axhline(30, linestyle='--', color='green', label='Sobrevendido')
        ax_rsi.set_title('Índice de Força Relativa (RSI)')
        ax_rsi.legend()
        ax_rsi.grid(True)
        st.pyplot(fig_rsi)
        plt.close(fig_rsi)

        try:
            # Corrigindo o resumo de indicadores
            ultimo_preco = float(hist['Close'].iloc[-1]) if not hist.empty else 0
            sma20 = float(hist['SMA20'].iloc[-1]) if not hist.empty and 'SMA20' in hist else 0
            rsi = float(hist['RSI'].iloc[-1]) if not hist.empty and 'RSI' in hist else 0
            
            st.markdown(f"""
                **Resumo de Indicadores - {ticker_code}**
                - 🔹 Último preço: R$ {ultimo_preco:.2f}
                - 🔸 Média Móvel 20 dias: R$ {sma20:.2f}
                - 🟣 RSI (14 dias): {rsi:.2f}
            """)
        except Exception as e:
            st.error(f"Erro ao gerar resumo de indicadores: {str(e)}")

        # Report section
        if st.button(f'Gerar Relatório para {ticker_code}'):
            st.session_state.mostrar_relatorio = not st.session_state.mostrar_relatorio

        if st.session_state.mostrar_relatorio:
            gerar_relatorio(ticker_symbol)

    except Exception as e:
        st.error(f"Erro ao processar a ação {selected_option}: {str(e)}")


# Execução
if __name__ == "__main__":
    main()
