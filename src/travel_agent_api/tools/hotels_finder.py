import os
import time
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from travel_agent_api.config import get_api_mode, is_test_mode

load_dotenv()


class HotelsInput(BaseModel):
    q: str = Field(description="Località dove cercare l'hotel, es. Barcellona.")
    check_in_date: str = Field(description="Data di check-in (YYYY-MM-DD), es. 2026-12-13.")
    check_out_date: str = Field(description="Data di check-out (YYYY-MM-DD), es. 2026-12-19.")
    adults: Optional[int] = Field(1, description="Numero di adulti. Default 1.")
    children: Optional[int] = Field(0, description="Numero di bambini. Default 0.")
    hotel_class: Optional[int] = Field(
        None, ge=2, le=5,
        description="Stelle dell'hotel (da 2 a 5). Da indicare SOLO se l'utente lo chiede.",
    )


def _nights(check_in: str, check_out: str) -> int:
    try:
        return max((date.fromisoformat(check_out) - date.fromisoformat(check_in)).days, 1)
    except ValueError:
        return 1


def _mock_hotels(q: str, check_in: str, check_out: str, hotel_class: Optional[int]) -> dict:
    """Dati di esempio per la modalità test: non sono hotel reali."""
    nights = _nights(check_in, check_out)
    stars = hotel_class or 3
    base = {2: 60, 3: 95, 4: 150, 5: 280}[stars]
    hotels = [
        (f"Hotel Centrale {q}", base, 4.3, ["Wi-Fi gratuito", "Colazione inclusa"]),
        (f"Grand Hotel {q}", int(base * 1.3), 4.6, ["Spa", "Piscina", "Parcheggio gratuito"]),
        (f"Residenza Aurora {q}", int(base * 0.85), 4.1, ["Wi-Fi gratuito", "Aria condizionata"]),
    ]
    return {
        "source": "mock (API_MODE=test): dati di esempio, NON reali",
        "location": q,
        "hotels": [
            {
                "name": name,
                "stars": stars,
                "description": f"Struttura di esempio a {q}, comoda per visitare il centro.",
                "price_per_night_eur": price,
                "price_total_eur": price * nights,
                "nights": nights,
                "check_in": "15:00",
                "check_out": "11:00",
                "rating": rating,
                "amenities": amenities,
                "photo": None,
                "link": None,
            }
            for name, price, rating, amenities in hotels
        ],
    }


def _serpapi_hotels(q: str, check_in: str, check_out: str, adults: int, children: int,
                    hotel_class: Optional[int]) -> dict:
    """Ricerca reale con SerpApi (modalità prod). Riduce il JSON ai soli campi utili."""
    api_key = os.getenv("SERPAPI_API_KEY", "")
    if not api_key or api_key.startswith("YOUR_"):
        return {"error": "SERPAPI_API_KEY non configurata: imposta una chiave valida nel .env o usa API_MODE=test."}

    from serpapi import GoogleSearch

    params = {
        "api_key": api_key,
        "engine": "google_hotels",
        "hl": "it", "gl": "it", "currency": "EUR",
        "q": q,
        "check_in_date": check_in, "check_out_date": check_out,
        "adults": adults, "children": children,
    }
    if hotel_class:  # il filtro stelle solo se richiesto
        params["hotel_class"] = hotel_class

    data = GoogleSearch(params).get_dict()
    if "error" in data:
        return {"error": data["error"]}

    hotels = []
    for p in (data.get("properties") or [])[:5]:
        images = p.get("images") or []
        hotels.append({
            "name": p.get("name"),
            "description": p.get("description"),
            "price_per_night_eur": (p.get("rate_per_night") or {}).get("lowest"),
            "price_total_eur": (p.get("total_rate") or {}).get("lowest"),
            "check_in": p.get("check_in_time"),
            "check_out": p.get("check_out_time"),
            "rating": p.get("overall_rating"),
            "amenities": (p.get("amenities") or [])[:6],
            "photo": images[0].get("thumbnail") if images else None,
            "link": p.get("link"),
        })
    return {"source": "serpapi", "location": q, "hotels": hotels}


@tool(args_schema=HotelsInput)
def hotels_finder(
    q: str,
    check_in_date: str,
    check_out_date: str,
    adults: Optional[int] = 1,
    children: Optional[int] = 0,
    hotel_class: Optional[int] = None,
):
    """
    Cerca hotel in una località per le date indicate.
    Restituisce nome, descrizione, prezzi, orari, valutazione e servizi.
    """
    print("*" * 80)
    print(f"[hotels_finder] modalità={get_api_mode()} | {q} | {check_in_date} -> {check_out_date} "
          f"| adulti={adults}, bambini={children}, stelle={hotel_class}")
    start = time.perf_counter()

    try:
        if is_test_mode():
            result = _mock_hotels(q, check_in_date, check_out_date, hotel_class)
        else:
            result = _serpapi_hotels(q, check_in_date, check_out_date, adults or 1, children or 0, hotel_class)
    except Exception as e:
        print(f"[hotels_finder] ERRORE: {e}")
        result = {"error": str(e)}

    print(f"[hotels_finder] completato in {time.perf_counter() - start:.2f}s")
    print("*" * 80)
    return result