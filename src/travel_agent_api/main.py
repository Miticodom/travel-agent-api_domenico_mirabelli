from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from travel_agent_api.routes import chat_router

app = FastAPI(
    title="Travel Agent API",
    description="Assistente di viaggio con FastAPI, LangChain e LangGraph",
    version="0.1.0",
)

# Domini che possono chiamare l'API (il client Laravel gira sulla porta 8000)
origins = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router, tags=["Chat"], prefix="/chat")


@app.get("/")
def health_check():
    """Controllo rapido per verificare che il server sia attivo."""
    return {"status": "ok"}