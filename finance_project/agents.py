import uuid
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle


def criar_evento_google_calendar(titulo, data_inicio, data_fim):
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    service = build('calendar', 'v3', credentials=creds)
    
    event = {
        'summary': titulo,
        'start': {
            'dateTime': data_inicio,
            'timeZone': 'America/Sao_Paulo',
        },
        'end': {
            'dateTime': data_fim,
            'timeZone': 'America/Sao_Paulo',
        },
    }
    
    event = service.events().insert(calendarId='primary', body=event).execute()
    return event.get('htmlLink')

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")


def call_agent(agent: Agent, message_text: str, user_id: str, session_id: str) -> str:
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name=agent.name,
        user_id=user_id,
        session_id=session_id
    )
    runner = Runner(agent=agent, app_name=agent.name,
                    session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=message_text)])

    final_response = ""
    try:
        for event in runner.run(user_id=user_id, session_id=session_id, new_message=content):
            if event.is_final_response():
                for part in event.content.parts:
                    if part.text is not None:
                        final_response += part.text
                        final_response += "\n"
        return final_response
    except Exception as e:
        return f"Erro ao processar o agente {agent.name}: {str(e)}"


def agente_buscador_financeiro(ativo: str, data_de_hoje: str, user_id: str, session_id: str):
    buscador = Agent(
        name='agente_buscador_financeiro',
        model='gemini-2.0-flash',
        description='Agente que busca notícias financeiras recentes sobre um ativo.',
        tools=[google_search],
        instruction="""
            Você é um assistente financeiro de pesquisa. Use a ferramenta google_search
            para encontrar as últimas notícias relevantes (até 30 dias) sobre o ativo informado.
            Foque em aspectos como: variações importantes, decisões corporativas, anúncios de dividendos, fusões, etc.
            Retorne um resumo dos eventos mais impactantes sobre esse ativo.
            Inclua todas as datas completas (dia, mês e ano) que encontrar, para os eventos de dividendos, anúncio de resultados e fatos relevantes.
        """
    )
    entrada = f"Ativo: {ativo}\nData atual: {data_de_hoje}"
    return call_agent(buscador, entrada, user_id, session_id)


def agente_analista_fundamentalista(ativo: str, noticias: str, user_id: str, session_id: str):
    planejador = Agent(
        name="agente_analista_fundamentalista",
        model="gemini-2.0-flash",
        instruction="""
            Você é um analista fundamentalista. Sua função é, com base nas últimas notícias e histórico recente do ativo,
            listar os fatores que mais impactaram o preço. Aponte se o ativo está em tendência de alta/baixa,
            se há riscos associados e pontos de atenção para investidores.
            Busque também por datas de eventos como divulgação de resultados, pagamento e valor de dividendos e evolução na dívida e no lucro.
            Inclua todas as datas completas (dia, mês e ano) que encontrar, para os eventos de dividendos, anúncio de resultados e fatos relevantes.

        """,
        description="Agente que analisa fundamentos e notícias de ativos",
        tools=[google_search]
    )

    entrada = f"Ativo: {ativo}\nNotícias recentes: {noticias}"
    return call_agent(planejador, entrada, user_id, session_id)


def agente_redator_financeiro(ativo: str, analise: str, user_id: str, session_id: str):
    redator = Agent(
        name="agente_redator_financeiro",
        model="gemini-2.0-flash",
        instruction="""
            Você é um redator de relatórios financeiros. Com base na análise fornecida, escreva um relatório
            claro e profissional sobre o ativo, incluindo:
            - Breve resumo do ativo;
            - Fatos recentes e como impactaram o preço;
            - Interpretação do comportamento do mercado;
            - Dados importantes como evolução do lucro, dividendos em valores, datas de pagamento de dividendos e de anuncio de resultados;
            - Conclusão e possíveis próximos passos;
            O texto deve ter tom informativo, evitando linguagem emocional, e ser voltado para investidores iniciantes.
            Inclua todas as datas completas (dia, mês e ano) que encontrar, para os eventos de dividendos, anúncio de resultados e fatos relevantes.
        """,
        description="Agente redator de relatórios financeiros"
    )
    entrada = f"Ativo: {ativo}\nAnálise: {analise}"
    return call_agent(redator, entrada, user_id, session_id)


def agente_revisor_financeiro(ativo: str, relatorio: str, user_id: str, session_id: str):
    revisor = Agent(
        name="agente_revisor_financeiro",
        model="gemini-2.0-flash",
        instruction="""
            Você é um revisor financeiro. Verifique o texto abaixo com foco em:
            - Clareza na explicação dos conceitos;
            - Coerência e correção técnica;
            - Gramática e ortografia.
            Se estiver tudo certo, retorne o relatório completo.
            Caso contrário, realize os ajustes necessários e retorne o novo relatório.
            Inclua todas as datas completas (dia, mês e ano) que encontrar, para os eventos de dividendos, anúncio de resultados e fatos relevantes.
        """,
        description="Agente revisor técnico de relatórios financeiros"
    )
    entrada = f"Ativo: {ativo}\nRelatório: {relatorio}"
    return call_agent(revisor, entrada, user_id, session_id)


def agente_resumo(relatorio: str, user_id: str, session_id: str):
    resumidor = Agent(
        name="agente_resumo",
        model="gemini-2.0-flash",
        instruction="""
            Você é um especialista financeiro focado em extrair informações chave de relatórios financeiros,
            voltadas para investidores iniciantes.

            Leia o texto abaixo e retorne um JSON contendo os seguintes campos, se disponíveis:

            - "dividend_yield": número ou string com o valor percentual do dividend yield;
            - "resultados_divulgados": lista de objetos no formato:
                [
                    {
                        "data": "YYYY-MM-DD",
                        "referente_a": "Trimestre X de XXXX" ou outro identificador,
                        "lucro_liquido": valor, se mencionado
                    },
                    ...
                ];
            - "pagamentos_dividendos": lista de objetos no formato:
                [
                    {
                        "data_pagamento": "YYYY-MM-DD",
                        "valor": "R$ X,XX",
                        "tipo": "juros sobre capital" ou "dividendo" ou outro
                    },
                    ...
                ];
            - "divida_liquida": valor da dívida líquida;
            - "outros_pontos": lista de strings com outras informações relevantes.

            Retorne **apenas o JSON**, sem texto adicional ou explicações.
            Para as datas, só retorne o valor se tiver a informação completa (dia, mês e ano). Se não, retorne 'N/A' para esses campos.
        """,
        description="Agente que resume relatórios financeiros em formato estruturado com múltiplos eventos"
    )
    entrada = f"Relatório: {relatorio}"
    
    return call_agent(resumidor, entrada, user_id, session_id)


def orquestrar_agentes(ticker: str, data_de_hoje: str):
    user_id = f"user-{uuid.uuid4()}"
    session_id = f"session-{uuid.uuid4()}"

    noticias = agente_buscador_financeiro(
        ticker, data_de_hoje, user_id, session_id)
    analise = agente_analista_fundamentalista(
        ticker, noticias, user_id, session_id)
    relatorio = agente_redator_financeiro(ticker, analise, user_id, session_id)
    revisao = agente_revisor_financeiro(ticker, relatorio, user_id, session_id)
    resumo = agente_resumo(revisao, user_id, session_id)
    resultados = agente_buscador_relatorio(
        ticker, data_de_hoje, user_id, session_id)

    return {"relatorio": revisao, "resumo": resumo, "resultados": resultados}


def agente_buscador_relatorio(ativo: str, data_de_hoje: str, user_id: str, session_id: str):
    buscador = Agent(
        name='agente_buscador_relatorio',
        model='gemini-2.0-flash',
        description='Agente que busca os últimos relatórios de resultados de um ativo.',
        tools=[google_search],
        instruction="""
            Você é um assistente financeiro de pesquisa. Use a ferramenta google_search
            para encontrar os últimos relatórios de resultados do ativo informado.
            Compare os resultados e traga as evoluções indicadas nesses relatórios bem como o 
            link do site da empresa onde encontra os relatórios.          
        """
    )
    entrada = f"Ativo: {ativo}\nData atual: {data_de_hoje}"
    return call_agent(buscador, entrada, user_id, session_id)



