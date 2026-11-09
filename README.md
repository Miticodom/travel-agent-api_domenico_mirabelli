# Travel Agent API

Progetto finale della Specializzazione Coding AI (Aulab Hackademy) — **Domenico Mirabelli**.

API di un assistente di viaggio con **FastAPI**, **LangChain** e **LangGraph**: un agente sceglie da solo
il tool da usare (voli, hotel, itinerario, informazioni storiche). Pensata per il client Laravel del corso (non incluso).

## Come funziona

`POST /chat/travel-agent` riceve la conversazione. L'agente (`create_react_agent`) decide se rispondere o chiamare
un tool, e ripete finché ha la risposta. L'API restituisce tutti i messaggi (`human`, `ai`, `tool`, `ai`).

```
src/travel_agent_api/
├── main.py                     # app FastAPI e CORS
├── config.py                   # lettura di API_MODE (test/prod)
├── llm.py                      # unico punto in cui si crea il modello (OpenAI o Groq)
├── routes/chat_router.py       # endpoint
├── services/agent_service.py   # agente, system prompt, tracing
└── tools/                      # flights_finder, hotels_finder, chain_travel_plan, chain_historical_expert
```

## Avvio

Requisiti: Python 3.13 e Poetry 2 (testato su Windows, PowerShell).

```powershell
git clone https://github.com/Miticodom/travel-agent-api_domenico_mirabelli.git
cd travel-agent-api_domenico_mirabelli
poetry install
Copy-Item .env.example .env      # poi inserisci la tua chiave (OPENAI_API_KEY oppure GROQ_API_KEY)
poetry run uvicorn travel_agent_api.main:app --reload --port 8080
```

Documentazione e prove: http://127.0.0.1:8080/docs (il client Laravel chiama la porta 8080).

Variabili del `.env` (non viene versionato; nella repo c'è solo `.env.example`). Basta la chiave di **un solo** provider:

| Variabile | Descrizione |
|---|---|
| `OPENAI_API_KEY`, `OPENAI_MODEL` | **OpenAI**. Modello di default: `gpt-4o`. |
| `GROQ_API_KEY`, `GROQ_MODEL` | **Groq**. Modello di default: `openai/gpt-oss-120b`. |
| `LLM_PROVIDER` | Opzionale: `openai` o `groq`. Se manca, usa OpenAI se c'è una `OPENAI_API_KEY` valida, altrimenti Groq. |
| `API_MODE` | `test` (dati di esempio, default) o `prod` (SerpApi). |
| `SERPAPI_API_KEY` | Solo per `prod`. |

Senza una chiave SerpApi i voli e gli hotel sono **dati di esempio** generati dal codice, e l'agente avvisa l'utente che non sono reali.

## Cosa ho modificato rispetto alle guide

- **OpenAI e Groq.** Le guide usavano solo OpenAI (`ChatOpenAI`, `gpt-4o`); io avevo sviluppato il progetto con Groq perché non avevo
  una chiave OpenAI, e dopo il feedback del docente l'ho reso compatibile con entrambi. `llm.py` (`get_llm()`) sceglie provider e modello
  dal `.env`, e tutti i tool e l'agente usano quella funzione. Il nome del modello sta nel `.env` perché il primo modello Groq che avevo
  scelto (`llama-3.3-70b-versatile`) è stato spento. Per i modelli OpenAI che non accettano `temperature` (serie `o` e `gpt-5`) il parametro viene omesso.
- **`API_MODE` test/prod**, citata dalle guide ma non realizzata.
- **Python** `>=3.13,<4.0` (Poetry aveva scritto `>=3.13` senza tetto, e le librerie di LangChain dichiarano `<4.0`); struttura `src/`.
- **Tool:** parametri piatti invece dell'oggetto `params`; in `flights_finder` tolto `"stops": "1"` (in SerpApi, da quanto ho letto, significa "solo voli diretti")
  e risultati ridotti ai campi utili; in `hotels_finder` `hotel_class` opzionale (nella guida il default era 2 stelle); in `chain_historical_expert` aggiunto
  `StrOutputParser` (la guida restituiva l'oggetto messaggio); in `chain_travel_plan` istruzioni sul formato con `get_format_instructions()`, e numero di giorni
  e date calcolati dal codice, non dal modello. Tutti i tool restituiscono un campo `error` invece di sollevare eccezioni.
- **Agente:** `prompt=` al posto del system message nella lista dei messaggi, `recursion_limit=15` contro i loop, regole nel system prompt
  (non inventare dati, chiedere quelli mancanti, avvisare quando sono di esempio), template di output con segnaposto.
- **API:** corretto il refuso `ChatComplentionRequest`, errori gestiti con HTTP 500 leggibile, rotta di controllo `GET /`.
- **Tracing:** `print` nel router, in ogni tool e nell'agente (tool chiamato, argomenti, tempi, lunghezza delle risposte).

## Test eseguiti

Con Groq, in modalità `test`, da `/docs` e dal client Laravel: voli, hotel, itinerario e storia chiamano il tool giusto con argomenti corretti;
con una richiesta incompleta ("Vorrei andare a Barcellona.") l'agente non chiama nessun tool e chiede i dati mancanti.

## Limiti

- La modalità `prod` (SerpApi) non è stata testata con una chiave reale.
- **Il supporto a OpenAI non è stato provato con una chiave OpenAI reale**: l'ho verificato con un server simulato che imita le API di OpenAI
  (chiamata al tool, risposta finale, secondo turno con la cronologia), seguendo le impostazioni delle guide.
- Non ci sono test automatici (`tests/` è vuota).
- La risposta include campi interni del modello (es. `reasoning_content`) che il client rimanda a ogni turno; in Swagger la risposta appare come `"string"` perché manca un `response_model`.