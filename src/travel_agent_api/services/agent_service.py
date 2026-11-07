from datetime import datetime

from langgraph.prebuilt import create_react_agent

from travel_agent_api.llm import get_llm
from travel_agent_api.tools.chain_historical_expert import chain_historical_expert
from travel_agent_api.tools.chain_travel_plan import chain_travel_plan
from travel_agent_api.tools.flights_finder import flights_finder
from travel_agent_api.tools.hotels_finder import hotels_finder

FLIGHTS_OUTPUT = """
format: markdown
## ✈️ Miglior opzione

### Andata
- Compagnia aerea: <compagnia>
- Data di partenza: <YYYY-MM-DD>
- Orari: <ora partenza> → <ora arrivo>
- Durata del volo: <durata>

### Ritorno
- Compagnia aerea: <compagnia>
- Data di ritorno: <YYYY-MM-DD>
- Orari: <ora partenza> → <ora arrivo>
- Durata del volo: <durata>

**Prezzo totale:** <prezzo> € per <n> passeggeri

Inserisci il link di prenotazione se disponibile.

#### Altre opzioni disponibili
- <compagnia>: andata <ora>, ritorno <ora>, <prezzo> €
"""

HOTELS_OUTPUT = """
format: markdown
#### 🏨 <nome hotel> (<stelle> stelle)

Inserisci la foto dell'hotel se disponibile.

*Descrizione:* <descrizione>
*Prezzo per notte:* <prezzo> €
*Prezzo totale:* <prezzo> € per <n> notti
*Check-in:* <ora>, *Check-out:* <ora>
*Valutazione complessiva:* <voto> su 5
*Servizi inclusi:* <servizi>
"""

TRAVEL_PLAN_OUTPUT = """
format: markdown
### 🗺️ Itinerario

### Giorno 1 - <YYYY-MM-DD>
*Mattina:* <attività>
*Pomeriggio:* <attività>
*Sera:* <attività>

### Giorno 2 - <YYYY-MM-DD>
...
"""

SYSTEM_PROMPT = """
Sei un travel planner. Il tuo compito è organizzare il viaggio per l'utente.
Rispondi sempre in italiano e aggiungi qualche emoji per rendere l'output più piacevole.
La data di oggi è {today}.

Regole:
- Per voli, hotel e itinerari usa i tool a disposizione: non inventare mai prezzi, orari o strutture.
- Se mancano informazioni indispensabili (aeroporti, date, numero di viaggiatori),
  chiedile all'utente prima di chiamare un tool.
- Nelle chiamate ai tool scrivi le date nel formato YYYY-MM-DD, calcolandole rispetto alla data di oggi.
- Se il risultato di un tool ha un campo "source" che inizia con "mock", avvisa l'utente
  che i dati sono di esempio e non reali.
- Se un tool restituisce un campo "error", spiega il problema all'utente in modo semplice.

Usa i seguenti formati per l'output.

Esempio output voli:
{flights}

Esempio output hotel:
{hotels}

Esempio output viaggio:
{plan}
"""


class Agent:
    def __init__(self):
        self.current_datetime = datetime.now()
        self.model = get_llm(temperature=0.2)
        self.tools = [
            chain_historical_expert,
            flights_finder,
            hotels_finder,
            chain_travel_plan,
        ]
        # Il system prompt si passa con prompt=: non finisce nella lista dei messaggi
        self.agent_executor = create_react_agent(
            self.model, self.tools, prompt=self._build_system_prompt()
        )

    def _build_system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            today=self.current_datetime.strftime("%Y-%m-%d (%A)"),
            flights=FLIGHTS_OUTPUT,
            hotels=HOTELS_OUTPUT,
            plan=TRAVEL_PLAN_OUTPUT,
        )

    def run(self, messages: list):
        print(f"[agent] avvio con {len(messages)} messaggi in ingresso")

        # recursion_limit: tetto ai passaggi del ciclo agente <-> tool, evita loop infiniti
        result = self.agent_executor.invoke(
            {"messages": messages}, config={"recursion_limit": 15}
        )

        all_messages = result["messages"]
        self._trace(all_messages[len(messages):])  # traccia solo i messaggi nuovi
        return all_messages

    @staticmethod
    def _trace(new_messages: list):
        print("-" * 80)
        print("[agent] sequenza di esecuzione:")
        for msg in new_messages:
            if msg.type == "ai" and getattr(msg, "tool_calls", None):
                for call in msg.tool_calls:
                    print(f"[agent] il modello chiama il tool '{call['name']}' con argomenti: {call['args']}")
            elif msg.type == "tool":
                print(f"[agent] risposta del tool '{msg.name}' ({len(str(msg.content))} caratteri)")
            elif msg.type == "ai":
                print(f"[agent] risposta finale del modello ({len(str(msg.content))} caratteri)")
        print("-" * 80)