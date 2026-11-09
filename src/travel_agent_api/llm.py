import os

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

# Modelli OpenAI che accettano una temperature personalizzata. Gli altri (serie o, gpt-5, gpt-6...)
# la rifiutano o la ignorano: per loro non si passa e si usa il valore predefinito.
_TEMPERATURE_PREFIXES = ("gpt-4", "gpt-3.5")


def _has_key(name: str) -> bool:
    """True se la variabile esiste nel .env e non è ancora il segnaposto YOUR_..."""
    value = os.getenv(name, "").strip()
    return bool(value) and not value.upper().startswith("YOUR_")


def get_provider() -> str:
    """
    Sceglie il provider: LLM_PROVIDER ha la precedenza. Se non è impostato,
    usa OpenAI quando c'è una OPENAI_API_KEY valida, altrimenti Groq.
    """
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider:
        if provider not in ("openai", "groq"):
            raise ValueError(f"LLM_PROVIDER non valido: '{provider}'. Usa 'openai' oppure 'groq'.")
        return provider
    if _has_key("OPENAI_API_KEY"):
        return "openai"
    if _has_key("GROQ_API_KEY"):
        return "groq"
    raise ValueError("Nessuna chiave trovata: imposta OPENAI_API_KEY oppure GROQ_API_KEY nel file .env.")


def get_llm(temperature: float = 0.3) -> BaseChatModel:
    """
    Unico punto del progetto che crea il modello di linguaggio.
    Tutti i tool e l'agente chiamano questa funzione: per cambiare provider
    o modello si modifica solo il file .env.
    """
    provider = get_provider()

    if provider == "openai":
        if not _has_key("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY mancante o non valida nel file .env.")
        from langchain_openai import ChatOpenAI

        model = os.getenv("OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL
        kwargs = {}
        if model.startswith(_TEMPERATURE_PREFIXES):
            kwargs["temperature"] = temperature
        print(f"[llm] provider=openai | modello={model} | temperature={kwargs.get('temperature', 'default')}")
        return ChatOpenAI(model=model, **kwargs)

    if not _has_key("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY mancante o non valida nel file .env.")
    from langchain_groq import ChatGroq

    model = os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL
    print(f"[llm] provider=groq | modello={model} | temperature={temperature}")
    return ChatGroq(model=model, temperature=temperature)