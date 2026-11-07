import os

from dotenv import load_dotenv

load_dotenv()


def get_api_mode() -> str:
    """Legge API_MODE dal .env. Se manca o è strana, usa 'test' (nessuna chiamata a servizi a pagamento)."""
    mode = os.getenv("API_MODE", "test").strip().lower()
    return mode if mode in ("test", "prod") else "test"


def is_test_mode() -> bool:
    return get_api_mode() == "test"