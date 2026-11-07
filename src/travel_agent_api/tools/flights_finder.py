import os
import time
from typing import Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent_api.config import get_api_mode, is_test_mode

load_dotenv()


class FlightsInput(BaseModel):
    departure_airport: str = Field(description="Codice IATA dell'aeroporto di partenza, es. MXP.")
    arrival_airport: str = Field(description="Codice IATA dell'aeroporto di arrivo, es. BCN.")
    outbound_date: str = Field(description="Data di andata (YYYY-MM-DD), es. 2026-12-13.")
    return_date: str = Field(description="Data di ritorno (YYYY-MM-DD), es. 2026-12-19.")
    adults: Optional[int] = Field(1, description="Numero di adulti. Default 1.")
    children: Optional[int] = Field(0, description="Numero di bambini. Default 0.")


def _mock_flights(dep: str, arr: str, outbound: str, ret: str, adults: int, children: int) -> dict:
    """Dati di esempio per la modalità test: non sono voli reali."""
    passengers = adults + children
    options = [
        ("Ryanair", 89, "07:15", "09:05", "17:40", "19:30", "1h 50m"),
        ("Vueling", 118, "11:30", "13:20", "15:10", "17:00", "1h 50m"),
        ("ITA Airways", 142, "18:05", "19:55", "09:00", "10:50", "1h 50m"),
    ]
    return {
        "source": "mock (API_MODE=test): dati di esempio, NON reali",
        "route": f"{dep} -> {arr}",
        "options": [
            {
                "airline": airline,
                "outbound": {"date": outbound, "departure_time": d1, "arrival_time": a1, "duration": dur, "stops": 0},
                "return": {"date": ret, "departure_time": d2, "arrival_time": a2, "duration": dur, "stops": 0},
                "price_eur_total": per_person * passengers,
                "passengers": passengers,
            }
            for airline, per_person, d1, a1, d2, a2, dur in options
        ],
        "booking_link": "https://www.google.com/travel/flights",
    }


def _serpapi_flights(dep: str, arr: str, outbound: str, ret: str, adults: int, children: int) -> dict:
    """Ricerca reale con SerpApi (modalità prod). Riduce il JSON ai soli campi utili."""
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key or api_key.startswith("YOUR_"):
        return {"error": "SERPAPI_API_KEY non configurata: imposta una chiave valida nel .env o usa API_MODE=test."}

    from serpapi import GoogleSearch

    data = GoogleSearch({
        "api_key": api_key,
        "engine": "google_flights",
        "hl": "it", "gl": "it", "currency": "EUR",
        "departure_id": dep, "arrival_id": arr,
        "outbound_date": outbound, "return_date": ret,
        "adults": adults, "children": children,
    }).get_dict()

    if "error" in data:
        return {"error": data["error"]}

    found = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    options = []
    for opt in found[:5]:
        options.append({
            "price_eur": opt.get("price"),
            "total_duration_min": opt.get("total_duration"),
            "legs": [
                {
                    "airline": leg.get("airline"),
                    "flight_number": leg.get("flight_number"),
                    "from": leg.get("departure_airport", {}).get("id"),
                    "departure_time": leg.get("departure_airport", {}).get("time"),
                    "to": leg.get("arrival_airport", {}).get("id"),
                    "arrival_time": leg.get("arrival_airport", {}).get("time"),
                }
                for leg in opt.get("flights", [])
            ],
        })
    return {
        "source": "serpapi",
        "options": options,
        "booking_link": data.get("search_metadata", {}).get("google_flights_url"),
    }


@tool(args_schema=FlightsInput)
def flights_finder(
    departure_airport: str,
    arrival_airport: str,
    outbound_date: str,
    return_date: str,
    adults: Optional[int] = 1,
    children: Optional[int] = 0,
):
    """
    Cerca voli di andata e ritorno tra due aeroporti (codici IATA) nelle date indicate.
    Restituisce le opzioni con compagnia, orari, durata e prezzo.
    """
    print("*" * 80)
    print(f"[flights_finder] modalità={get_api_mode()} | {departure_airport} -> {arrival_airport} "
          f"| {outbound_date} / {return_date} | adulti={adults}, bambini={children}")
    start = time.perf_counter()

    try:
        args = (departure_airport, arrival_airport, outbound_date, return_date, adults or 1, children or 0)
        result = _mock_flights(*args) if is_test_mode() else _serpapi_flights(*args)
    except Exception as e:
        print(f"[flights_finder] ERRORE: {e}")
        result = {"error": str(e)}

    print(f"[flights_finder] completato in {time.perf_counter() - start:.2f}s")
    print("*" * 80)
    return result