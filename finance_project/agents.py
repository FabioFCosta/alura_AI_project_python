import uuid
import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

def call_agent(agent: Agent, message_text: str, user_id: str, session_id: str) -> str:
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name=agent.name,
        user_id=user_id,
        session_id=session_id
    )
    runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
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
            Você é um especialista financeiro focado em resumir relatórios para investidores iniciantes com as informações mastigadas (incluindo os valores).
            Leia o texto abaixo e retorne de 10 a 20 pontos mais relevantes resumidos em tópicos.
            Dê preferencia a informações como Dividend Yield, data de relatório de resultados, dívidas, lucro e afins.
            Sua resposta deve conter somente bullet point dos principais pontos}}.
        """,
        description="Agente revisor técnico de relatórios financeiros"
    )
    entrada = f"Relatório: {relatorio}"
    return call_agent(resumidor, entrada, user_id, session_id)

def orquestrar_agentes(ticker: str, data_de_hoje: str):
    user_id = f"user-{uuid.uuid4()}"
    session_id = f"session-{uuid.uuid4()}"

    noticias = agente_buscador_financeiro(ticker, data_de_hoje, user_id, session_id)
    analise = agente_analista_fundamentalista(ticker, noticias, user_id, session_id)
    relatorio = agente_redator_financeiro(ticker, analise, user_id, session_id)
    revisao = agente_revisor_financeiro(ticker, relatorio, user_id, session_id)
    resumo = agente_resumo(revisao, user_id,session_id)
    resultados = agente_buscador_relatorio(ticker, data_de_hoje, user_id, session_id)

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
            Compare os resultados e traga as evoluções indicadas nesses relatórios bem como o link para baixar os relatórios.          
        """
    )
    entrada = f"Ativo: {ativo}\nData atual: {data_de_hoje}"
    return call_agent(buscador, entrada, user_id, session_id)
                    