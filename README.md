# Legal Lens

An AI-assisted **case-preparation and legal-orientation assistant** for Indian criminal law (central acts + Karnataka state law). A person describes what happened in plain language. Legal Lens interviews them and builds a structured case file: facts, claims, evidence, timeline. It then retrieves real statutory provisions with source citations, finds evidence gaps, argues the other side's case, and drafts documents. Every legal citation points to a real retrieved source.

> **Portfolio project. Not legal advice.** Legal Lens organizes information. It does not replace a lawyer, predict outcomes, or file anything. It is built and demonstrated with synthetic case data. Do not use it with real people's real legal matters, especially ongoing-abuse narratives involving minors. See [CLAUDE.md §18](CLAUDE.md) for why.

Everything runs **on your machine**. The LLM is a local model served by [Ollama](https://ollama.com), so no API key is needed and no case data leaves the device for model calls.

---

## What it does

| Stage | Features |
|---|---|
| **1. Interview** | Free-text narrative → Fact Extraction (each statement tagged `fact` / `assumption` / `opinion` / `allegation` / `unknown`). An adaptive interview picks the next most legally useful question, flags answers that contradict earlier ones, and stops on a 10-question cap (minimum 3). Builds a chronological timeline, listing undated events separately. |
| **2. Case Dashboard** | Claims and evidence (file upload with PDF text / image OCR plus a confidence rating). Evidence-gap analysis. Legal classification hypotheses with **real provisions retrieved from 13 statute PDFs**. Devil's-advocate weaknesses and opposing arguments. Ranked strategy options, shown only after the user acknowledges a disclaimer. Q&A preparation that answers only from known facts. |
| **3. Document Review** | Drafts complaints, legal notices, summaries, chronologies, evidence lists, statements and question sets. Case-strength view with no win-probability score. Append-only audit log. |

**"View in source"** opens the original government PDF with the cited section's own text highlighted. The server does the highlighting with PyMuPDF.

## Design principles

- **Retrieval is never optional.** Law Retrieval makes no LLM call at all. It queries ChromaDB and returns exactly what comes back, which can be nothing. Agents never cite section numbers from model memory.
- **Citation binding.** Legal Strategy and Document Generation report the `chunk_id`s they cited. The orchestrator checks these against what was actually retrieved, removes anything invented, and reports what it removed.
- **Deterministic where it matters.** Claim support status (`supported` / `partially_supported` / `disputed` / `unsupported`), the case-strength band, the interview budget and the timeline are plain code, not LLM output.
- **Surface, don't resolve.** If Legal Classification and Devil's Advocate disagree, both views are shown side by side. Neither agent overrides the other.
- **No naive scoring.** Case strength shows evidence coverage, contradictions, legal uncertainty and counterarguments, plus one coarse documentation-completeness band (`early-stage` / `partially-documented` / `well-documented`) with a disclaimer.
- **Old law vs. new law.** Every chunk carries `effective_from` / `effective_to` / `repealed_by` / `successor_of`. For example, BNS §103 is linked to its predecessor IPC §302, and IPC chunks end on 2024-06-30.

## Architecture

```
React + Vite + TS (localhost:5173)
        │  REST (25 endpoints)
        ▼
FastAPI  ──►  Orchestrator (hand-coded state machine; owns all Case Builder writes + audit log)
                 │
                 ├─ 10 specialist agents (each reads a slice of case state, returns JSON)
                 │    Fact Extraction · Legal Classification · Law Retrieval (no LLM)
                 │    Dynamic Interview · Evidence Gap Analysis · Devil's Advocate
                 │    Legal Strategy · Document Generation · Question Preparation · Claim Synthesis
                 │         │
                 │         └─► Ollama /api/chat (qwen2.5:7b-instruct, local)
                 │
                 ├─ SQLite (SQLAlchemy)  — cases, statements, events, claims, evidence,
                 │                          interview turns, drafts, audit log
                 ├─ ChromaDB (embedded)  — 2,761 section-level statute chunks
                 └─ data/evidence/       — uploaded files, Fernet-encrypted at rest
```

Agents never call each other. All communication goes through shared, structured case state held by the orchestrator ([`backend/app/orchestrator.py`](backend/app/orchestrator.py)). Each agent subclasses [`Agent`](backend/app/agents/base.py), which provides `_call_model()` and `_call_model_json()`. `_call_model_json()` strips code fences, checks that the reply is a JSON object, and retries once with a repair prompt if it isn't.

### Legal corpus

13 PDFs in [`data/raw/criminal-law/`](data/raw/criminal-law/MANIFEST.md), split by section, deduplicated against each PDF's table of contents, and embedded into ChromaDB:

| Tier | Documents |
|---|---|
| 1. Core legislation | BNS 2023, BNSS 2023, BSA 2023, and the IPC 1860, CrPC 1973 and Indian Evidence Act 1872 they replaced |
| 2. Central special laws | POCSO 2012, NDPS 1985, UAPA 1967, IT Act 2000 |
| 3. Karnataka | Karnataka Police Act 1963, KCOCA 2000, Goonda Act 1985 |

Each PDF's source URL and provenance are recorded in [`MANIFEST.md`](data/raw/criminal-law/MANIFEST.md). Ingestion stores a SHA-256 checksum per file and re-embeds only files that changed.

---

## Quick start

**Prerequisites:** Python 3.11+, Node.js, [Ollama](https://ollama.com), and optionally `tesseract` for image OCR (`brew install tesseract`).

```bash
ollama pull qwen2.5:7b-instruct   # one-time
python3 run.py                    # from the project root
```

Then open **http://localhost:5173**.

[`run.py`](run.py) is safe to re-run. It skips any step that is already done:
1. Creates `backend/.venv` and installs the backend.
2. Copies `backend/.env.example` to `.env`.
3. Checks that Ollama is up and the model is pulled. It only warns if not, because the non-LLM features still work.
4. Ingests the corpus into ChromaDB if the collection is empty.
5. Runs `npm install`.
6. Starts uvicorn (`:8000`) and Vite (`:5173`). Ctrl+C or `SIGTERM` stops both.

### Manual setup

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
python -m app.ingestion             # first run, or after changing data/raw/
uvicorn app.main:app --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev
```

Health checks: `curl localhost:8000/health` should return `{"status":"ok"}`, and `curl localhost:11434/api/tags` should list the model.

### Configuration (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Any pulled chat model |
| `DATABASE_URL` | `sqlite:///../data/db/legal_lens.db` | Case Builder DB |
| `VECTOR_STORE_DIR` | `../data/vector_store` | ChromaDB persistence |
| `EVIDENCE_STORE_DIR` | `../data/evidence` | Encrypted evidence files |
| `EVIDENCE_ENCRYPTION_KEY` | *(auto-generated)* | Fernet key. If unset, one is generated and saved to `data/.evidence_encryption_key` (gitignored) |

---

## Testing

```bash
cd backend && .venv/bin/python -m pytest -q     # 116 tests
```

Most tests mock `_call_model`, so they need no LLM. A few run against the **real** ingested corpus instead:
- `test_retrieval_accuracy.py`: a hand-checked set of scenario → correct-provision pairs.
- `test_citation_accuracy.py`: checks that every one of the 2,761 chunks' `section_number` matches the text at the start of that chunk.
- `test_adversarial.py`: a test that pins down a known, documented gap in citation binding.

[`backend/e2e_smoke.py`](backend/e2e_smoke.py) sends a realistic narrative through every stage against the live model and corpus, with nothing mocked. It needs Ollama running.

## Project layout

```
backend/
  app/
    main.py              FastAPI routes (25), global error handler with CORS
    orchestrator.py      State machine, citation binding, claim status, case strength, timeline
    models.py            SQLAlchemy Case Builder schema
    agents/              base.py + 10 agents (one system prompt each)
    ingestion.py         PDF → section chunks → ChromaDB (checksums, TOC dedup, effective dates)
    vector_store.py      ChromaDB client + query_provisions()
    pdf_highlight.py     Server-side highlighting for "view in source"
    evidence_extraction.py  pypdf text layer / Tesseract OCR + confidence
    encryption.py        Fernet encryption for evidence files
  tests/                 pytest suite
  e2e_smoke.py           Live end-to-end pipeline run
frontend/src/
  App.tsx                3-stage tab flow, case resume via localStorage, "Analyze the case"
  api.ts                 Typed client for every endpoint
  components/            One panel per feature + shared styles + error boundary
data/raw/criminal-law/   Statute PDFs + MANIFEST.md (db/, vector_store/, evidence/ are gitignored)
run.py                   One-command launcher
```

## Known limitations

- **Prose-level citation checking isn't built.** Citation binding checks the self-reported `citations` list. A made-up section number written directly into the drafted text is not caught (see `test_adversarial.py`).
- **Retrieval doesn't filter by date yet.** Effective-date metadata is stored on every chunk, but Law Retrieval doesn't yet choose old-law or new-law provisions based on the event date.
- **Some ranking weaknesses remain.** A few gold-set queries (and some POCSO/NDPS queries) return amendment notices or nearby sections instead of the main offence text. These are documented in the tests rather than hidden.
- **Chunking is section-level only.** Sub-sections, provisos and explanations stay inside their parent section's chunk.
- **There is no authentication.** Knowing a case ID is enough to access that case. SQLite and ChromaDB are not encrypted; only evidence files are.
- **There is no case deletion or retention policy.** The user chose to skip this.
- **Generated drafts carry no AI watermark.** It was removed at the user's explicit instruction ([CLAUDE.md §8.7](CLAUDE.md)).
- **No judicial precedents.** No affordable citator (a source tracking whether judgments were overruled or followed) exists, so precedent search is deferred.
- **Scanned PDFs uploaded as evidence aren't OCR'd.** Only PDFs with a text layer and image files are.

## Further reading

| Document | What's in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Master spec: vision, boundaries, every design decision with its date and reasoning |
| [`explanation.md`](explanation.md) | File-by-file walkthrough, every endpoint, constants table |
| [`PROJECT_REPORT.md`](PROJECT_REPORT.md) | Retrospective: architecture, timeline, real bugs found and fixed |
| [`COMPLETION.md`](COMPLETION.md) | Phase-by-phase tracker (0–9) |
| [`DEMO.md`](DEMO.md) | Live demo script with timings |
