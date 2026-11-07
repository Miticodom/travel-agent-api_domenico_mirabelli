import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_llm(temperature: float = 0.3) -> ChatGroq:
    """
    Unico punto del progetto che crea il modello di linguaggio.
    Tutti i tool e l'agente chiamano questa funzione: per cambiare
    provider o modello si modifica solo questo file (o il .env).
    """
    model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    print(f"[llm] creo il modello Groq: {model} (temperature={temperature})")
    return ChatGroq(model=model, temperature=temperature)