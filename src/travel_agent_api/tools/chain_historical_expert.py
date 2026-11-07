import time

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from travel_agent_api.llm import get_llm

SYSTEM_PROMPT = """
Sei un esperto di storia e cultura dei luoghi di viaggio.
Il tuo compito è fornire contenuti approfonditi sull'argomento richiesto
e rispondere alle domande come un assistente.
Rispondi in italiano, in modo accurato e amichevole, usando qualche emoji.
"""


@tool
def chain_historical_expert(input_text: str) -> str:
    """
    Fornisce informazioni storiche e culturali approfondite su un argomento,
    un luogo o una destinazione di viaggio.

    Args:
        input_text (str): L'argomento storico o culturale da approfondire.

    Returns:
        str: Il contenuto generato dal modello.
    """
    print("*" * 80)
    print(f"[chain_historical_expert] input: {input_text}")
    start = time.perf_counter()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            ("human", "{input}"),
        ]
    )

    # prompt -> modello -> parser che estrae solo il testo
    chain = prompt | get_llm() | StrOutputParser()

    result = chain.invoke({"system_prompt": SYSTEM_PROMPT, "input": input_text})

    print(f"[chain_historical_expert] completato in {time.perf_counter() - start:.1f}s")
    print("*" * 80)
    return result