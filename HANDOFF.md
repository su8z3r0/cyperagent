# CyperAgent — Handoff

Ultimo aggiornamento: 2026-11-26
Repo: https://github.com/su8z3r0/cyperagent (pubblico, branch `main`)
Ultimo commit prima di questo: `44c182e` — "Initial commit" (solo `.gitignore` + vecchio main.py)
Working tree: `main.py` modificato; `engine.py`, `static/`, `test/`, `old_engine.py`,
`error.py`, `HANDOFF.md` non ancora committati. `.env` ignorato.

## 1. Obiettivo
TUI da terminale (Textual) per chattare con modelli locali serviti da LM Studio
(API OpenAI-compatibile). Separazione netta:
- `main.py` = UI (Textual)
- `engine.py` = modello, agent, stato della conversazione
La UI non importa LangChain; l'engine non importa Textual.

## 2. Cosa funziona oggi
- Layout: Header, trascrizione (`VerticalScroll#transcript`), `Static#status`,
  `Input#prompt`, Footer.
- Streaming token-per-token dentro un widget `AssistantMessage` (Static aggiornato).
- Storia conversazione in `Engine.messages`, aggiornata a fine turno con l'ultimo
  stato `values` di `agent.astream`.
- ESC interrompe il worker: il testo parziale resta e viene marcato " interrotto"
  (`AssistantMessage.stop_message`).
- Errori mostrati come blocco `.error` nella trascrizione (`ErrorMessage`).
- Binding: `ctrl+q` esce, `escape` interrompe.
- Modello attuale in `.env`: `granite-3.0-8b-instruct` (non-thinking).

## 3. Ambiente (PC di sviluppo attuale)
- Windows, Python 3.14 (`C:\Python314`) → warning "pydantic v1 non compatibile",
  non bloccante. Su un altro PC meglio venv con Python 3.12/3.13.
- Pacchetti verificati: langchain 1.5.2, langchain-openai 1.8.5,
  langgraph 4.3.2, textual 8.2.8, openai 3.59.0, python-dotenv.
- LM Studio: server OpenAI-compatibile su `http://127.0.0.1:1235/v1`.
  Modelli in `F:\lmmodels\lmstudio`. Il modello viene caricato JIT al primo request
  (prima risposta lenta).
- Modelli SENZA thinking verificati: `qwen2.5-coder-7b-instruct`,
  `granite-3.0-8b-instruct`, `nvidia-nemotron-3.5-bolt-e4b`, `google/gemma-4-e4b`.
- Modelli CON `reasoning_content` separato: `arex-2`, `twil-8b@q4_k_m`,
  `qwen3.5-4b`. Con questi, `chunk.text` di LangChain resta vuoto durante il
  pensiero.

## 4. File
- `main.py` — TUI ChatApp, widget UserMessage/AssistantMessage/ErrorMessage.
- `engine.py` — `Engine`, `create_engine`.
- `static/styles.css` — attualmente solo `.error { color: red; }`.
- `.env` — NON committato (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL).
- `.gitignore` — esclude `.env*`, `__pycache__/`, `*.py[cod]`, `.venv/`, `*.sqlite*`, `*.db`.
- `old_engine.py` — vecchia CLI (riferimento storico; NON committare).
- `test/textual-dev.py` — vecchio esperimento (da rimuovere).
- `error.py` — vuoto (scratch).

## 5. Architettura e flusso
- `ChatApp(engine)` riceve l'engine già costruito (`create_engine()`).
- `on_input_submitted`: se un worker è in esecuzione → ignora; altrimenti incrementa
  `_turn_seq`, disabilita l'input, avvia `run_turn(text, seq)` con
  `@work(exclusive=True)` e salva il Worker in `_current_turn`.
- `run_turn`: recupera i widget con `query_one` PRIMA di ogni `await`; crea
  `AssistantMessage` prima del primo `await`; monta UserMessage e AssistantMessage;
  status "✻ Thinking…"; `async for token in engine.stream_turn(text)` →
  `assistant.add_token`; a fine turno pulizia.
  - `except asyncio.CancelledError`: `assistant.stop_message()`, poi `raise`.
  - `except Exception`: monta `ErrorMessage(e)`.
  - `finally`: status vuoto, input riabilitato, focus (oggi incondizionato).
- `engine.create_engine()`: legge `.env` con `dotenv_values` (path da `__file__`),
  crea `ChatOpenAI(base_url, api_key, model, temperature=0.1)`,
  `create_agent(model=llm, tools=[], system_prompt=...)`, restituisce `Engine(agent)`.
- `Engine.stream_turn`: appende il messaggio utente, usa
  `agent.astream(..., stream_mode=["messages","values"])`, fa `yield` di
  `chunk.text` per gli `AIMessageChunk`, e aggiorna `self.messages` con l'ultimo
  payload `values`.

## 6. Debito tecnico / problemi noti (in ordine di priorità)
1. `finally` NON condizionato al proprietario: manca il confronto `seq == self._turn_seq`
   e l'azzeramento di `_current_turn`. Rischio race: un turno vecchio può riabilitare
   l'input di un turno nuovo.
2. `action_quit_turn`: bare `except` + `return False` inutile; nessuna guardia su
   `None`/`worker.is_running`.
3. `check_action` assente: la voce "Quit current turn" resta nel Footer anche a riposo.
4. `engine.py`: nessun `try/finally` attorno all'`astream` → dopo uno stop la storia
   resta con il messaggio utente senza risposta. Manca l'assistant sintetico
   "[interrotto]"/"[errore]".
5. Import duplicato di `AIMessageChunk`; `AIMessage`/`ToolMessage` inutilizzati.
6. UI: `transcript` interrogato due volte; `status.update("")` a ogni token;
   `add_token` aggiorna il widget a ogni token (nessun throttle);
   `AssistantMessage.text()` inutilizzato.
7. `error.py` vuoto; `test/` e `old_engine.py` da ripulire.
8. `.error` usa `red` invece della variabile di tema `$error` (cosmetico).

## 7. Prossimi passi
- Step 3d: `action_quit_turn` con guardia esplicita; `check_action` per il Footer.
- Step 4 (engine): `try/finally` sull'`astream`; a interruzione/errore appendere un
  assistant sintetico con il parziale + marcatore; chiudere lo stream; pulire import.
- Step 5 (UI): unica `query_one` per transcript; status aggiornato solo al primo
  token; throttle su `add_token` con update finale; rimozione `text()`; CSS `$error`.
- Poi, in ordine di valore: Markdown a fine turno; tool events compatti nello status;
  reasoning; checkpointer SQLite (`SqliteSaver`) + lista thread; history prompt
  (up/down); comando `clear`.
- Reasoning (se serve): `langchain-openai` 1.8.5 **scarta** `reasoning_content`.
  `langchain_core` però lo espone in `content_blocks` se presente in
  `additional_kwargs["reasoning_content"]`. Soluzione: sottoclasse di `ChatOpenAI`
  che fa override di `_convert_chunk_to_generation_chunk` (riceve il dict SSE,
  legge `choices[0].delta.reasoning_content`) e lo aggiunge agli `additional_kwargs`
  del messaggio-chunk. La fusione dei chunk concatena le stringhe. Nota: il reasoning
  NON viene rispedito al server (la conversione messaggi ignora i campi extra).

## 8. Decisioni di design già prese
- Stop del turno: marcare la risposta parziale "[interrotto]" (UI e storia).
- Errori: blocco persistente nella trascrizione, non solo log.
- Proprietario del turno: contatore di generazione (`_turn_seq`), non identità Worker.
- Submit mentre un turno gira: ignorato.

## 9. Setup su un altro PC
1. `git clone https://github.com/su8z3r0/cyperagent.git`
2. `cd cyperagent` e creare/attivare un venv (consigliato Python 3.12/3.13).
3. `python -m pip install langchain langchain-openai python-dotenv textual`
4. Creare `.env` (NON committare):

       LLM_BASE_URL=http://127.0.0.1:1235/v1
       LLM_API_KEY=lm-studio
       LLM_MODEL=granite-3.0-8b-instruct

5. Avviare in LM Studio il server locale OpenAI-compatibile (porta 1235) e caricare
   un modello non-thinking.
6. `python main.py`

## 10. Cosa NON committare
`.env`, `__pycache__/`, `*.sqlite*`, `.venv/`, `old_engine.py`, `test/`, `error.py`.

## 11. Verifica rapida
- Avvio TUI e focus sull'input.
- Prompt → testo che cresce in streaming.
- ESC durante lo streaming → parziale + " interrotto", input attivo.
- Server spento/modello inesistente → blocco errore nella chat, app viva.
- Turno completato → nessun marcatore, input attivo.
- Due prompt consecutivi → il secondo parte correttamente.

## 12. Comandi git suggeriti
    git add HANDOFF.md main.py engine.py static/styles.css .gitignore
    git commit -m "wip: textual chat UI + engine scaffold + handoff"
    git push origin main
