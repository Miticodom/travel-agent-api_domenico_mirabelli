# Travel Agent API

Progetto finale della Specializzazione Coding AI (Aulab Hackademy) — **Domenico Mirabelli**.

API backend di un assistente di viaggio, costruita con **FastAPI**, **LangChain** e **LangGraph**.
L'utente scrive in linguaggio naturale e un agente decide da solo quale tool usare: ricerca voli,
ricerca hotel, itinerario giorno per giorno, informazioni storico-culturali.
È pensata per il client web Laravel fornito col progetto (non incluso in questa repository).

## Come funziona

Il client manda la conversazione a `POST /chat/travel-agent`. L'agente (`create_react_agent` di LangGraph)
lavora a ciclo: il modello decide se rispondere o chiamare un tool, il risultato del tool torna al modello,
e si va avanti finché risponde senza altri tool. L'API restituisce tutti i messaggi
(`human`, `ai`, `tool`, `ai`), nel formato che il client si aspetta.

```
src/travel_agent_api/
├── main.py            # app FastAPI e CORS
├── config.py          # lettura di API_MODE (test/prod)
├── llm.py             # unico punto in cui si crea il modello (Groq)
├── routes/chat_router.py
├── services/agent_service.py   # agente, system prompt, tracing
└── tools/             # flights_finder, hotels_finder, chain_travel_plan, chain_historical_expert
```

## Avvio

Requisiti: Python 3.13 e Poetry 2 (testato su Windows, PowerShell).

```powershell
git clone https://github.com/Miticodom/travel-agent-api_domenico_mirabelli.git
cd travel-agent-api_domenico_mirabelli
poetry install
Copy-Item .env.example .env      # poi inserisci la tua GROQ_API_KEY nel .env
poetry run uvicorn travel_agent_api.main:app --reload --port 8080
```

Documentazione interattiva: http://127.0.0.1:8080/docs. Il client Laravel chiama la porta **8080**.

Variabili del `.env` (il file non viene mai versionato, nella repo c'è solo `.env.example`):
`GROQ_API_KEY` (obbligatoria), `GROQ_MODEL` (default `openai/gpt-oss-120b`),
`API_MODE` (`test` o `prod`), `SERPAPI_API_KEY` (solo per `prod`).

Esempio di richiesta a `POST /chat/travel-agent`:

```json
{"messages": [{"type": "human", "content": "Cerco un hotel 4 stelle a Barcellona per due adulti dal 13 al 19 dicembre 2026."}]}
```

## Modalità test e produzione

Non avendo una chiave SerpApi ho implementato `API_MODE`, che le guide citano ma non realizzano.
In **`test`** (default) voli e hotel sono dati di esempio generati dal codice, e l'agente avvisa l'utente
che non sono reali. In **`prod`** i tool chiamano SerpApi.
> Il ramo `prod` è implementato ma **non testato con una chiave reale**.

## Tracing

Il codice stampa sul terminale cosa viene eseguito. Esempio di una richiesta di voli:

```
[chat_completion] ricevuti 1 messaggi
[flights_finder] modalità=test | MXP -> BCN | 2026-12-13 / 2026-12-19 | adulti=2, bambini=0
[agent] il modello chiama il tool 'flights_finder' con argomenti: {...}
[agent] risposta finale del modello (729 caratteri)
[chat_completion] risposta pronta (4 messaggi)
```

## Cosa ho modificato rispetto alle guide

### Configurazione e modello
- **Groq al posto di OpenAI.** Il modello si crea in un solo punto, `llm.py` (`get_llm()`); tutti i tool e l'agente lo usano.
  Il nome del modello è nel `.env` (`GROQ_MODEL`), così cambiarlo non richiede di toccare il codice.
- **`API_MODE` test/prod** con `config.py` (vedi sopra).
- **Python:** `requires-python = ">=3.13,<4.0"`. Poetry 2 aveva scritto `>=3.13` senza limite superiore, e
  molte librerie di LangChain dichiarano `<4.0`.
- **Struttura `src/`:** Poetry 2 crea il pacchetto dentro `src/`, a differenza delle guide. Gli import non cambiano.

### Tool
- **Parametri piatti** in `flights_finder`, `hotels_finder` e `chain_travel_plan`: le guide avvolgono tutto in un
  oggetto `params`, che aggiunge un livello di annidamento e rende più facili gli errori del modello nelle chiamate.
- **`flights_finder`:** tolto il filtro `"stops": "1"`, che nella documentazione di SerpApi, da quanto ho letto,
  significa "solo voli diretti" mentre la guida lo descriveva come "massimo 1 scalo". Il risultato di SerpApi viene
  ridotto alle prime 5 opzioni con i soli campi utili, invece di restituire l'intero JSON.
- **`hotels_finder`:** `hotel_class` ora è opzionale e senza valore predefinito. Nella guida il default era 2,
  quindi senza indicazioni dell'utente cercava solo hotel a 2 stelle. Il filtro si applica solo se l'utente chiede le stelle.
  Anche qui il JSON di SerpApi viene ridotto ai campi utili.
- **`chain_historical_expert`:** aggiunto `StrOutputParser`. Nella guida la funzione dichiarava di ritornare `str`
  ma ritornava l'oggetto messaggio completo.
- **`chain_travel_plan`:** nella guida si usava `PydanticOutputParser` senza dire al modello in che formato rispondere.
  Ora le istruzioni sul formato vengono generate dallo schema con `get_format_instructions()` e inserite nel prompt.
  Inoltre il **numero di giorni è calcolato dal codice** e comunicato al modello, mentre **giorno e data di ogni tappa
  li scrive il codice** (con `timedelta`), non il modello. `budget` ha ora un valore predefinito.
- Tutti i tool restituiscono un campo `error` in caso di problemi, invece di sollevare eccezioni che interromperebbero l'agente.

### Agente
- **`prompt=`** invece di inserire il system message nella lista dei messaggi (e poi tagliarlo con `[1:]`).
- **`recursion_limit=15`:** un tetto ai passaggi del ciclo agente-tool, per evitare loop infiniti.
- **System prompt con regole esplicite:** non inventare prezzi, orari o strutture; chiedere i dati mancanti prima di
  chiamare un tool; scrivere le date in formato `YYYY-MM-DD`; avvisare quando i dati sono `mock`; spiegare in modo semplice
  quando un tool restituisce un errore.
- **Template di output** riscritti in italiano e con segnaposto (`<compagnia>`, `<prezzo>`) al posto di valori d'esempio
  che il modello avrebbe potuto copiare.
- **Tracing** della sequenza di esecuzione (vedi sopra).

### API
- Corretto il refuso `ChatComplentionRequest` -> `ChatCompletionRequest`.
- Gestione degli errori nel router: eccezione -> HTTP 500 con messaggio leggibile.
- Aggiunta la rotta `GET /` di controllo.

## Problemi incontrati

- **Il modello `llama-3.3-70b-versatile` non esiste più su Groq** (errore 404 `model_not_found`): è stato spento
  il 16 agosto 2026. Ho elencato i modelli del mio account con `Groq().models.list()` e scelto `openai/gpt-oss-120b`.
  Per questo il nome del modello sta nel `.env`.
- **`ModuleNotFoundError: travel_agent_api`** al primo avvio: `poetry add` non installa il progetto stesso, è servito `poetry install`.

## Test eseguiti

Tutti manuali, in modalità `test`, da `/docs` e dal client Laravel.

| Richiesta | Tool chiamato | Esito |
|---|---|---|
| Voli MXP -> BCN, 2 adulti, 13-19 dicembre 2026 | `flights_finder` | Argomenti corretti, avviso sui dati di esempio |
| Hotel 4 stelle a Barcellona | `hotels_finder` | `hotel_class=4` dedotto dalla frase |
| Itinerario a Roma, 13-15 dicembre, budget 1500 | `chain_travel_plan` | 3 giorni con le date corrette |
| Storia del Colosseo | `chain_historical_expert` | Testo restituito correttamente |
| "Vorrei andare a Barcellona." | nessuno | L'agente chiede i dati mancanti |
| Voli dal client Laravel | `flights_finder` | Risposta mostrata nella chat |

<!-- Inserisci qui i tuoi screenshot, es. ![Client Laravel](docs/img/client-voli.png) -->

## Limiti e possibili miglioramenti

- La modalità `prod` (SerpApi) non è stata testata con una chiave reale.
- Non ci sono test automatici: la cartella `tests/` è vuota.
- La risposta include anche campi interni del modello (es. `reasoning_content`) che il client rimanda a ogni turno:
  si potrebbero filtrare. In Swagger la risposta appare come `"string"` perché manca un `response_model`.