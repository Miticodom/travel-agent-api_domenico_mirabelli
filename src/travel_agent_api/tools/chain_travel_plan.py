import time
from datetime import date, timedelta
from typing import Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent_api.llm import get_llm


class TravelPlanInput(BaseModel):
    start_date: str = Field(description="Data di inizio del viaggio (YYYY-MM-DD), es. 2026-12-13.")
    end_date: str = Field(description="Data di fine del viaggio (YYYY-MM-DD), es. 2026-12-19.")
    destination: str = Field(description="Destinazione del viaggio.")
    adults: Optional[int] = Field(1, description="Numero di adulti. Default 1.")
    children: Optional[int] = Field(0, description="Numero di bambini. Default 0.")
    travel_style: str = Field("cultura", description="Stile di viaggio: avventura, relax, cultura, backpacking, lusso, famiglia.")
    budget: Optional[int] = Field(None, description="Budget totale in euro. Opzionale.")
    activities: str = Field("cultura e cibo locale", description="Attività preferite: cultura, natura, cibo, shopping...")
    food_restriction: str = Field("nessuna", description="Restrizioni alimentari: vegetariano, senza glutine, nessuna...")


class TravelDayOutput(BaseModel):
    morning: str = Field(description="Attività della mattina.")
    afternoon: str = Field(description="Attività del pomeriggio.")
    evening: str = Field(description="Attività della sera.")


class TravelPlanOutput(BaseModel):
    travel_plan: list[TravelDayOutput] = Field(
        description="Un elemento per ogni giorno del viaggio, in ordine cronologico."
    )


SYSTEM_PROMPT = """
Sei un esperto di pianificazione di viaggi.
Crea un itinerario giorno per giorno con queste informazioni:
- Destinazione: {destination}
- Date: dal {start_date} al {end_date} ({days} giorni: genera esattamente {days} giorni)
- Adulti: {adults}, bambini: {children}
- Stile di viaggio: {travel_style}
- Budget totale: {budget}
- Attività preferite: {activities}
- Restrizioni alimentari: {food_restriction}

Per ogni giorno descrivi mattina, pomeriggio e sera.
Scrivi in italiano e usa qualche emoji per rendere il testo più amichevole.

{format_instructions}
"""


@tool(args_schema=TravelPlanInput)
def chain_travel_plan(
    start_date: str,
    end_date: str,
    destination: str,
    adults: Optional[int] = 1,
    children: Optional[int] = 0,
    travel_style: str = "cultura",
    budget: Optional[int] = None,
    activities: str = "cultura e cibo locale",
    food_restriction: str = "nessuna",
):
    """
    Genera un itinerario di viaggio giorno per giorno (mattina, pomeriggio, sera)
    in base a destinazione, date, viaggiatori, stile, budget, attività e restrizioni alimentari.
    """
    print("*" * 80)
    print(f"[chain_travel_plan] {destination} | {start_date} -> {end_date} | stile={travel_style} | budget={budget}")
    start = time.perf_counter()

    try:
        first_day = date.fromisoformat(start_date)
        days = (date.fromisoformat(end_date) - first_day).days + 1
        if days < 1:
            return {"error": "La data di fine deve essere uguale o successiva alla data di inizio."}
    except ValueError:
        return {"error": "Date non valide: usa il formato YYYY-MM-DD."}

    # Il parser genera le istruzioni sul formato JSON a partire dallo schema Pydantic
    parser = PydanticOutputParser(pydantic_object=TravelPlanOutput)
    prompt = ChatPromptTemplate.from_messages([("human", SYSTEM_PROMPT)])

    # prompt -> modello -> parser (JSON -> oggetto Pydantic)
    chain = prompt | get_llm(temperature=0.5) | parser

    try:
        result = chain.invoke({
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "adults": adults,
            "children": children,
            "travel_style": travel_style,
            "budget": f"{budget} euro" if budget else "non specificato",
            "activities": activities,
            "food_restriction": food_restriction,
            "format_instructions": parser.get_format_instructions(),
        })
    except Exception as e:
        print(f"[chain_travel_plan] ERRORE: {e}")
        return {"error": f"Impossibile generare l'itinerario: {e}"}

    # Giorno e data li calcola il codice, non il modello
    plan = [
        {"day": i + 1, "date": (first_day + timedelta(days=i)).isoformat(), **day.model_dump()}
        for i, day in enumerate(result.travel_plan)
    ]

    print(f"[chain_travel_plan] generati {len(plan)} giorni su {days} richiesti "
          f"in {time.perf_counter() - start:.1f}s")
    print("*" * 80)
    return {"destination": destination, "travel_plan": plan}