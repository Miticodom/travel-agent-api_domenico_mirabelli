from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from travel_agent_api.services.agent_service import Agent

router = APIRouter()


class ChatCompletionRequest(BaseModel):
    # La lista dei messaggi che compongono la conversazione
    messages: list

    # Esempio mostrato nella pagina /docs
    model_config = {
        "json_schema_extra": {
            "example": {
                "messages": [
                    {"type": "human", "content": "Vorrei organizzare un viaggio a Roma"}
                ]
            }
        }
    }


@router.post("/travel-agent")
def chat_completion(request: ChatCompletionRequest):
    """
    Riceve la conversazione e restituisce la risposta dell'agente di viaggio.
    Se qualcosa va storto risponde con un errore HTTP 500 leggibile.
    """
    print("*" * 80)
    print(f"[chat_completion] ricevuti {len(request.messages)} messaggi")

    try:
        agent = Agent()
        response = agent.run(messages=request.messages)
    except Exception as e:
        print(f"[chat_completion] ERRORE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    print(f"[chat_completion] risposta pronta ({len(response)} messaggi)")
    print("*" * 80)
    return response