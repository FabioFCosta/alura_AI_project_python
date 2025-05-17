import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
from datetime import date

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

def call_agent(agent: Agent, message_text: str) -> str:
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name=agent.name, user_id="user1", session_id="session1")
    runner = Runner(agent=agent, app_name=agent.name,
                    session_service=session_service)
    content = types.Content(role="user", parts=[types.Part(text=message_text)])

    final_response = ""
    for event in runner.run(user_id="user1", session_id="session1", new_message=content):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text is not None:
                    final_response += part.text
                    final_response += "\n"
    return final_response


def agente_buscador_financeiro(ativo: str, data_de_hoje: str):
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
    return call_agent(buscador, entrada)

def agente_analista_fundamentalista(ativo: str, noticias: str):
    planejador = Agent(
        name="agente_analista_fundamentalista",
        model="gemini-2.0-flash",
        instruction="""
            Você é um analista fundamentalista. Sua função é, com base nas últimas notícias e histórico recente do ativo,
            listar os fatores que mais impactaram o preço. Aponte se o ativo está em tendência de alta/baixa,
            se há riscos associados e pontos de atenção para investidores.
        """,
        description="Agente que analisa fundamentos e notícias de ativos",
        tools=[google_search]
    )

    entrada = f"Ativo: {ativo}\nNotícias recentes: {noticias}"
    return call_agent(planejador, entrada)

def agente_redator_financeiro(ativo: str, analise: str):
    redator = Agent(
        name="agente_redator_financeiro",
        model="gemini-2.0-flash",
        instruction="""
            Você é um redator de relatórios financeiros. Com base na análise fornecida, escreva um relatório
            claro e profissional sobre o ativo, incluindo:
            - Breve resumo do ativo;
            - Fatos recentes e como impactaram o preço;
            - Interpretação do comportamento do mercado;
            - Conclusão e possíveis próximos passos.
            O texto deve ter tom informativo, evitando linguagem emocional, e ser voltado para investidores iniciantes.
        """,
        description="Agente redator de relatórios financeiros"
    )
    entrada = f"Ativo: {ativo}\nAnálise: {analise}"
    return call_agent(redator, entrada)

def agente_revisor_financeiro(ativo: str, relatorio: str):
    revisor = Agent(
        name="agente_revisor_financeiro",
        model="gemini-2.0-flash",
        instruction="""
            Você é um revisor financeiro. Verifique o texto abaixo com foco em:
            - Clareza na explicação dos conceitos;
            - Coerência e correção técnica;
            - Gramática e ortografia.
            Se estiver tudo certo, diga: 'O relatório está tecnicamente adequado.'
            Caso contrário, aponte os ajustes necessários.
        """,
        description="Agente revisor técnico de relatórios financeiros"
    )
    entrada = f"Ativo: {ativo}\nRelatório: {relatorio}"
    return call_agent(revisor, entrada)

data_de_hoje = date.today().strftime("%d/%m/%Y")
ativo = input("Digite o código do ativo (ex: PETR4): ").upper()

if not ativo:
    print("⚠️ Código do ativo não informado.")
else:
    print(f"🔎 Gerando relatório sobre {ativo}...")

    noticias = agente_buscador_financeiro(ativo, data_de_hoje)
    analise = agente_analista_fundamentalista(ativo, noticias)
    relatorio = agente_redator_financeiro(ativo, analise)
    revisao = agente_revisor_financeiro(ativo, relatorio)

    print("\n📄 RELATÓRIO FINAL:")
    print(revisao)
