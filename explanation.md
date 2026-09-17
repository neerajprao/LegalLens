# Legal Lens — Complete Project Explanation

> **Purpose of this document:** this is the single file to read before presenting Legal Lens as a semester-end project. It covers, for **every file that exists in the repository**: what it is, why it exists, what it does internally, and every parameter/constant/threshold a person would need to know to say "I built this" convincingly in a viva. Read top to bottom once, then use the Table of Contents to jump back to any file during Q&A.

---

## Table of Contents

1. [What Legal Lens Is, In One Paragraph](#1-what-legal-lens-is-in-one-paragraph)
2. [System Architecture Diagram](#2-system-architecture-diagram)
3. [Complete File Tree](#3-complete-file-tree)
4. [Root-Level Documents](#4-root-level-documents)
5. [Backend — Configuration & Infrastructure](#5-backend--configuration--infrastructure)
6. [Backend — Database Models (the Case Builder schema)](#6-backend--database-models-the-case-builder-schema)
7. [Backend — The Orchestrator (the brain)](#7-backend--the-orchestrator-the-brain)
8. [Backend — The 9 AI Agents](#8-backend--the-9-ai-agents)
9. [Backend — The RAG / Legal Knowledge Pipeline](#9-backend--the-rag--legal-knowledge-pipeline)
10. [Backend — Evidence Handling & Encryption](#10-backend--evidence-handling--encryption)
11. [Backend — API Layer (main.py)](#11-backend--api-layer-mainpy)
12. [Backend — Test Suite](#12-backend--test-suite)
13. [Data Directory](#13-data-directory)
14. [Frontend](#14-frontend)
15. [Every Important Constant / Hyperparameter, In One Table](#15-every-important-constant--hyperparameter-in-one-table)
16. [Key Design Decisions & The Reasoning Behind Them](#16-key-design-decisions--the-reasoning-behind-them)
17. [Known Limitations — Deliberately Left Incomplete](#17-known-limitations--deliberately-left-incomplete)
18. [How To Run This Project](#18-how-to-run-this-project)
19. [Viva / Presentation Cheat Sheet (Q&A prep)](#19-viva--presentation-cheat-sheet-qa-prep)

---

## 1. What Legal Lens Is, In One Paragraph

Legal Lens is an AI-assisted **legal case-preparation and orientation platform** for people facing a legal situation in **criminal law, under Karnataka/Indian jurisdiction**, who don't necessarily know any legal terminology. It is explicitly **not** a lawyer-replacement — it does not give legal advice, predict outcomes, or file anything. Instead it takes a person's plain-language narrative, extracts structured facts from it, asks follow-up questions, classifies which legal categories might apply, retrieves the *actual* relevant statute sections from a real ingested legal corpus (never inventing citations), finds weaknesses in the case ("devil's advocate"), suggests possible next steps, drafts documents (complaints, notices, chronologies), and presents an honest, multi-dimensional "case strength" summary — never a single win-probability number. Every legal claim shown to the user must trace back to a real retrieved chunk from real government legislation PDFs that were downloaded and ingested into a vector database; the system is built around the principle that it is better to say "I don't know" than to fabricate a confident-sounding but wrong answer.

It is a **portfolio project** (not a production system), built to demonstrate multi-agent system design, RAG (Retrieval-Augmented Generation) pipeline construction, and disciplined engineering trade-off decisions — not to serve real users with real legal problems.

---

## 2. System Architecture Diagram

```mermaid
flowchart TD
    subgraph Frontend["Frontend — React + TypeScript + Vite"]
        UI["App.tsx (single-page flow)"]
        Panels["9 feature panels\n(Interview, Timeline, Claims&Evidence,\nClassification, Devil's Advocate,\nStrategy, Documents, Case Strength, Audit Log)"]
        APIClient["api.ts — typed fetch client"]
    end

    subgraph Backend["Backend — Python + FastAPI"]
        Main["main.py\n(REST endpoints)"]
        Orchestrator["orchestrator.py\nHAND-CODED STATE MACHINE\n(the brain — owns all Case Builder logic,\ninvokes agents, binds citations,\ncomputes deterministic values)"]

        subgraph Agents["9 Specialist Agents (backend/app/agents/)"]
            FE["Fact Extraction"]
            LC["Legal Classification"]
            LR["Law Retrieval\n(NO LLM call — pure DB query)"]
            EGA["Evidence Gap Analysis"]
            DA["Devil's Advocate"]
            LS["Legal Strategy"]
            DG["Document Generation"]
            DI["Dynamic Interview"]
            QP["Question Preparation"]
        end

        Enc["encryption.py\n(Fernet, evidence files)"]
        Extract["evidence_extraction.py\n(pypdf + pytesseract OCR)"]
        Ingest["ingestion.py\n(PDF → chunks → embeddings)"]
    end

    subgraph Storage["Storage"]
        SQLite[("SQLite\ndata/db/legal_lens.db\nCase Builder state")]
        Chroma[("ChromaDB\ndata/vector_store/\n2,761 embedded legal-text chunks")]
        Files[("data/evidence/\nFernet-encrypted evidence files")]
        RawPDFs[("data/raw/criminal-law/\n13 real government legislation PDFs")]
    end

    subgraph Local["Local Inference (no network/API)"]
        Ollama["Ollama daemon\nhttp://localhost:11434\nmodel: qwen2.5:7b-instruct"]
    end

    UI --> Panels --> APIClient
    APIClient <-->|"REST / JSON\nhttp://localhost:8000"| Main
    Main --> Orchestrator
    Orchestrator --> FE & LC & LR & EGA & DA & LS & DG & DI & QP
    FE & LC & EGA & DA & LS & DG & DI & QP -->|"httpx POST /api/chat\n(think: false)"| Ollama
    LR -->|"query_provisions()"| Chroma
    Orchestrator <--> SQLite
    Orchestrator --> Enc --> Files
    Orchestrator --> Extract
    RawPDFs --> Ingest --> Chroma
```

**In words, one request's journey (e.g. "submit narrative"):**
`Browser → api.ts → POST /cases/{id}/narrative → main.py → Orchestrator.submit_narrative() → FactExtractionAgent.run() → local Ollama /api/chat call → JSON parsed → Statement/Event rows written to SQLite → AuditLogEntry written → jurisdiction-mismatch keyword check → response returned as JSON → api.ts → React state update → UI re-renders`.

> **Provider history (3 stages):** Anthropic Claude API (original v1 decision) → Google Gemini's free tier (switched 2026-08-26 after the Anthropic account had no funded credit balance) → **fully local, no API/network dependency at all** (switched again the same day, at the user's explicit request). The local model is Qwen3.5 9B (Q4 quantization) running via Ollama on the developer's own machine — verified to genuinely fit real hardware (MacBook Pro, Apple M3 Pro, 18GB unified memory) before being adopted, not assumed. Each swap was contained entirely to `app/agents/base.py`'s `_call_model()` internals — every agent's prompt/logic and every test was unaffected each time, since `_call_model`'s signature and return type never changed across any of the three providers. See §16 for the full reasoning behind each switch.

---

## 3. Complete File Tree

```
LegalLens/
├── CLAUDE.md                          ← master planning/decision-log document (huge, living doc)
├── COMPLETION.md                      ← phase-by-phase task tracker (what's done, what's deferred, why)
├── explanation.md                     ← THIS FILE
├── PROJECT_REPORT.md                  ← retrospective: objectives, timeline, key bugs found and fixed
├── DEMO.md                            ← live-presentation script
├── run.py                             ← one-command launcher: sets up + starts the whole stack
│
├── backend/                           ← Python + FastAPI backend
│   ├── pyproject.toml                 ← dependency list, project metadata
│   ├── e2e_smoke.py                   ← live, no-mocking, real-model end-to-end pipeline smoke test
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    ← FastAPI app, all REST endpoints
│   │   ├── config.py                  ← Settings (env vars, defaults)
│   │   ├── db.py                      ← SQLAlchemy engine/session setup
│   │   ├── models.py                  ← ORM models = the "Case Builder" schema
│   │   ├── orchestrator.py            ← THE BRAIN: hand-coded state machine
│   │   ├── vector_store.py            ← ChromaDB wrapper (embed/query)
│   │   ├── ingestion.py               ← PDF → text → chunks → ChromaDB pipeline
│   │   ├── pdf_highlight.py           ← bakes a real highlight annotation onto a source PDF (2026-09-17)
│   │   ├── evidence_extraction.py     ← OCR/PDF text extraction for uploaded evidence
│   │   ├── encryption.py              ← Fernet encryption for evidence files
│   │   └── agents/
│   │       ├── __init__.py
│   │       ├── base.py                ← Agent abstract base class, local-LLM call helpers
│   │       ├── fact_extraction.py     ← Agent 1
│   │       ├── legal_classification.py← Agent 2
│   │       ├── law_retrieval.py       ← Agent 3 (no LLM — pure retrieval)
│   │       ├── evidence_gap_analysis.py← Agent 4
│   │       ├── devils_advocate.py     ← Agent 5
│   │       ├── legal_strategy.py      ← Agent 6
│   │       ├── document_generation.py ← Agent 7
│   │       ├── dynamic_interview.py   ← Agent 8
│   │       ├── question_preparation.py← Agent 9
│   │       └── claim_synthesis.py     ← Agent 10 (proposes grounded claims from known facts, not in CLAUDE.md's original §8 roster — added later, see §16)
│   └── tests/                         ← 116 automated tests across 28 files
│       ├── conftest.py                ← isolated in-memory test DB setup
│       ├── test_health.py
│       ├── test_ingestion.py
│       ├── test_ingestion_change_detection.py
│       ├── test_retrieval_accuracy.py     ← runs against the REAL ingested corpus
│       ├── test_citation_accuracy.py      ← runs against the REAL ingested corpus
│       ├── test_pdf_highlight.py          ← runs against the REAL ingested corpus (2026-09-17)
│       ├── test_document_serving.py       ← `/documents/{filename}`, including the highlight query params
│       ├── test_jurisdiction.py
│       ├── test_fact_extraction_retry.py
│       ├── test_legal_classification_retry.py
│       ├── test_code_fence_stripping.py    ← markdown-fence stripping (found via a live model, not mocked)
│       ├── test_retrieved_provisions_capping.py  ← dedup/cap fix for the real Document Generation bug
│       ├── test_evidence_upload.py
│       ├── test_evidence_gap_analysis.py
│       ├── test_evidence_dispute.py
│       ├── test_encryption.py
│       ├── test_devils_advocate.py
│       ├── test_legal_strategy.py
│       ├── test_document_generation.py
│       ├── test_dynamic_interview.py
│       ├── test_question_preparation.py
│       ├── test_claims.py
│       ├── test_timeline.py
│       ├── test_audit_log.py
│       ├── test_case_strength.py
│       ├── test_adversarial.py
│       └── test_error_handling.py
│
├── data/                              ← all runtime + source data (mostly gitignored)
│   ├── raw/criminal-law/              ← the actual legal knowledge base source documents
│   │   ├── MANIFEST.md                ← provenance record: where every PDF came from
│   │   ├── .ingestion_checksums.json  ← SHA-256 per file, for change detection
│   │   ├── 01-core-legislation/       ← 6 PDFs (BNS, BNSS, BSA, IPC, CrPC, Evidence Act)
│   │   ├── 02-central-special-laws/   ← 4 PDFs (POCSO, NDPS, UAPA, IT Act)
│   │   └── 03-karnataka-state-laws/   ← 3 PDFs (Police Act, KCOCA, Goonda Act)
│   ├── db/legal_lens.db               ← SQLite database file (gitignored, regenerated)
│   ├── vector_store/                  ← ChromaDB's on-disk index (gitignored, regenerated)
│   ├── evidence/                      ← uploaded evidence files, Fernet-encrypted (gitignored)
│   └── .evidence_encryption_key       ← auto-generated encryption key (gitignored, secret)
│
└── frontend/                          ← React + TypeScript + Vite frontend
    ├── package.json                   ← npm dependencies/scripts
    ├── vite.config.ts                 ← Vite bundler config
    ├── tsconfig*.json                 ← TypeScript compiler configs
    ├── .oxlintrc.json                 ← linter config
    ├── index.html                     ← the single HTML page
    └── src/
        ├── main.tsx                   ← React entry point
        ├── App.tsx                    ← top-level page: 3-stage tab flow (Interview / Dashboard / Review)
        ├── index.css                  ← styling (App.css removed 2026-08-26 — dead default-Vite-template CSS)
        ├── api.ts                     ← typed fetch client for every backend endpoint
        └── components/
            ├── shared.ts               ← shared style constants
            ├── PanelHeader.tsx         ← shared panel title/subtitle header
            ├── ChatPanel.tsx           ← narrative intake + interview Q&A (renamed from InterviewPanel.tsx)
            ├── TimelinePanel.tsx
            ├── ClaimsEvidencePanel.tsx
            ├── ClassificationPanel.tsx ← also builds the highlighted-source-PDF link (see §11's `/documents` entry)
            ├── DevilsAdvocatePanel.tsx
            ├── StrategyPanel.tsx
            ├── QuestionPreparationPanel.tsx
            ├── DocumentsPanel.tsx
            ├── CaseStrengthPanel.tsx
            └── AuditLogPanel.tsx
```

---

## 4. Root-Level Documents

### `CLAUDE.md`
The **master planning document**. This is not code — it's a living design document that records every architectural decision made during the project, tagged with `DECISION`, `OPEN QUESTION`, or `ASSUMPTION TO VALIDATE`, plus a full dated change log at the bottom. It is the single source of truth for *why* the system is built the way it is. Sections 1–23 cover: vision, problem statement, target personas, functional requirements, the multi-agent architecture spec (§8, one subsection per agent), the interview system design (§9), the Case Builder data model sketch (§10), evidence/RAG architecture (§11–12), case-strength presentation philosophy (§15), privacy/security posture (§18), tech stack (§19), and risks (§21).

### `COMPLETION.md`
The **task tracker**. A phase-by-phase checklist (Phase 0 "Project Definition" through Phase 9 "Final Validation") where every line is either `[x]` (done), `[~]` (partially done, with an honest note on what's missing), or `[ ]` (not done, with a reason — either "blocked" or "deliberately deferred"). This file is what proves the project was built with discipline: nothing is marked done unless it's verifiably done, and every skipped item has a stated reason rather than being silently dropped.

### `PROJECT_REPORT.md`
A **retrospective**, narrative rather than reference — objectives, architecture summary, a phase-by-phase implementation timeline, and a "key technical challenges" section naming the real bugs found across the project's life (the CrPC chunking regex bug, the CORS-masking exception handler, the local-model reasoning-token/markdown-fence issues, the Document Generation noisy-context bug). The natural document to hand someone who wants the story of the project, not the file-by-file mechanics.

### `DEMO.md`
A **live-presentation script** — a stage-by-stage walkthrough of the running app with talking points, explicit about what's instant/local vs. what needs a real model call, plus a fallback plan (run the test suite live) if a demo audience has no patience for ~15-20 second local-model calls.

### `run.py`
A **one-command launcher** for the whole project — `python3 run.py` from the project root. Idempotent: each setup step checks whether it's already done and skips it if so, so it's safe to run every time rather than only on a fresh checkout.

| Step | What it does | How it checks "already done" |
|---|---|---|
| 1. Backend venv | Creates `backend/.venv` (via `python3.13`/`.12`/`.11` if found, else falls back to `sys.executable`) and runs `pip install -e .` | `backend/.venv/bin/python` exists; `import fastapi` succeeds in it |
| 2. `.env` file | Copies `backend/.env.example` → `backend/.env` | file already exists |
| 3. Ollama check | Queries `http://localhost:11434/api/tags`, checks the configured model (read from `.env`'s `OLLAMA_MODEL`, default `qwen2.5:7b-instruct`) is in the list | **Never hard-fails** — warns and continues, since claims/evidence CRUD, timeline, audit log, and Law Retrieval all work with zero LLM calls |
| 4. Corpus ingestion | Runs `python -m app.ingestion` | Queries ChromaDB's chunk count via the venv's Python; skips if > 0 |
| 5. Frontend deps | Runs `npm install` | `frontend/node_modules/` exists |
| 6. Launch | Starts `uvicorn app.main:app --port 8000` and `npm run dev -- --port 5173` as subprocesses, polls both `/health` and the frontend root until they respond (30s timeout each), prints both URLs | — |

**Shutdown**: both `Ctrl+C` (`SIGINT`) and `kill <pid>` (`SIGTERM`) are handled — `SIGTERM` is explicitly converted to the same `KeyboardInterrupt` path, since `SIGTERM` doesn't raise one on its own and without that handling a `kill` would leave both subprocesses orphaned. Verified live: sent `SIGTERM` to a running instance and confirmed both the backend (graceful Uvicorn shutdown log) and frontend processes actually exited, with no leftover processes.

One deliberate stdout detail: `sys.stdout.reconfigure(line_buffering=True)` is called at import time. Without it, `print()` output is fully-buffered (not flushed) whenever stdout isn't a live terminal — e.g. if the script is redirected to a log file or run under `nohup` — so every one of the script's own status messages would sit invisible in a buffer until process exit, even though the backend/frontend subprocesses' own output (a separate, unbuffered inherited file descriptor) would appear immediately. This was caught by testing the script with its output redirected to a file, not by inspection — the setup-step messages were silently missing from the log until the fix.

---

## 5. Backend — Configuration & Infrastructure

### `backend/pyproject.toml`
Standard Python packaging file (PEP 621 format). Declares the project as `legal-lens-backend`, requires Python ≥3.11, and lists dependencies:

| Dependency | Purpose |
|---|---|
| `fastapi` | web framework for the REST API |
| `uvicorn[standard]` | ASGI server that actually runs FastAPI |
| `sqlalchemy` | ORM — turns Python classes into SQL tables |
| `pydantic` / `pydantic-settings` | request/response validation + typed settings from env vars |
| `httpx` | HTTP client — used to call the local Ollama daemon's native `/api/chat` endpoint directly (see §16 for the provider-switch history; the `openai` and `anthropic` SDKs used by earlier providers were both removed as dependencies) |
| `chromadb` | embedded vector database for the legal-text RAG corpus |
| `python-multipart` | required by FastAPI to accept file uploads |
| `pypdf` | extracts text from PDF files (both the legal corpus and uploaded evidence) |
| `pillow` | image handling (for OCR) |
| `pytesseract` | Python wrapper around the Tesseract OCR engine |
| `cryptography` | provides `Fernet` symmetric encryption for evidence files |
| `pymupdf` (added 2026-09-17) | source-PDF text search and highlight-annotation rendering (`pdf_highlight.py`) |
| (dev) `pytest`, `httpx` | test runner and HTTP client used by FastAPI's `TestClient` |

### `backend/app/config.py`
A `pydantic_settings.BaseSettings` subclass. This is where every environment-variable-configurable value lives, with sane local-dev defaults:

```python
ollama_base_url: str = "http://localhost:11434"
ollama_model: str = "qwen2.5:7b-instruct"
database_url: str = "sqlite:///../data/db/legal_lens.db"
vector_store_dir: str = "../data/vector_store"
evidence_store_dir: str = "../data/evidence"
evidence_encryption_key: str = ""
```
Values are read from a `.env` file (via `model_config = SettingsConfigDict(env_file=".env")`) — `.env` no longer needs any LLM API key at all now that the provider is fully local. `ollama_model` is set once for the whole app (a deliberate v1 decision — no per-agent model differentiation). These two `ollama_*` settings replaced `gemini_api_key`/`gemini_model`/`gemini_base_url`, which had themselves replaced `anthropic_api_key`/`anthropic_model` earlier the same day — two provider switches in one session (see §16).

### `backend/app/db.py`
Sets up SQLAlchemy: creates the `engine` (pointed at the SQLite file from `settings.database_url`), a `SessionLocal` sessionmaker, a `Base` declarative class every ORM model inherits from, and a `get_db()` FastAPI dependency (a generator that yields a session and always closes it in a `finally` block — the standard FastAPI-with-SQLAlchemy pattern). `connect_args={"check_same_thread": False}` is required because SQLite normally refuses to be used across threads, but FastAPI's request handling can hand off to different threads.

### `backend/app/vector_store.py`
A thin wrapper around ChromaDB. `get_collection()` returns (or creates) a single persistent collection named `criminal_law_provisions`, backed by a `chromadb.PersistentClient` pointed at `settings.vector_store_dir`. `query_provisions(query_text, n_results=5)` runs a semantic-similarity query and returns a clean list of `{chunk_id, text, metadata, distance}` dicts — if the collection is empty it returns `[]` immediately rather than erroring. **No LLM is involved in this file at all** — this is deliberate (see §8, Law Retrieval Agent).

### `backend/app/pdf_highlight.py` (added 2026-09-17)
Renders a copy of a source statute PDF with the retrieved provision's own text highlighted, using PyMuPDF. `render_highlighted_pdf(pdf_path, page_number, section_number)` re-extracts the target page's text with PyMuPDF (deliberately *not* reusing the chunk text ChromaDB already has, which was extracted by `pypdf` — the two extractors disagree on minor formatting closely enough to silently drop matches), re-applies the same section-header pattern `ingestion.py` uses to find that section's own span on the page, highlights each line of it via `page.search_for(...)`, and restricts each search to the vertical band between that section's header and the next one (`clip=`) so a short, generic phrase from the target section (e.g. "to fine.") can't spuriously highlight identical wording in a *different* section further down the same page — a real false positive caught and fixed via a rendered-page visual check, not just inferred. Returns `None` (never raises) if the section can't be located on the given page, so a caller always has a safe fallback to the plain, unhighlighted document.

Replaces the previous approach of a `"#page=N&search=term"` URL fragment, which only worked in Chromium's built-in PDF viewer and only ever highlighted the short section-title string via the browser's own "find in page" — not the actual explanatory passage.

---

## 6. Backend — Database Models (the Case Builder schema)

**File: `backend/app/models.py`** — this is the relational schema for what CLAUDE.md calls the "Case Builder": the single structured representation of a user's legal situation that every agent reads from and writes to. Built with SQLAlchemy 2.0's typed `Mapped[...]` style.

### Enums
| Enum | Values | Used by |
|---|---|---|
| `StatementClassification` | `fact`, `assumption`, `opinion`, `allegation`, `unknown` | `Statement.classification` |
| `PartyRole` | `user`, `opposing`, `witness`, `third_party`, `authority` | `Party.role` |
| `ClaimStatus` | `unsupported`, `partially_supported`, `supported`, `disputed` | `Claim.status` |
| `DocumentDraftType` | `complaint`, `legal_notice`, `case_summary`, `chronology`, `evidence_list`, `statement`, `question_set` | `DocumentDraft.draft_type` |

### Tables

**`Case`** — the root entity. `id` (UUID string), `status` (default `"active"`), `jurisdiction` (default `"India - Karnataka"`), `summary`, `created_at`/`updated_at`. Has cascading relationships to every child table below (`cascade="all, delete-orphan"` — deleting a Case would delete everything under it in one query, though the actual `DELETE /cases/{id}` endpoint was **deliberately not built**, see §17).

**`Party`** — a person/org involved (`role`, `name_or_identifier`, `relationship_to_user`).

**`Event`** — something that happened (`description`, `occurred_at` as free text, `is_approximate_date` bool, `source`, `confidence`).

**`Statement`** — one raw assertion extracted from user text, tagged with `StatementClassification`. Can link to an `Event`/`Party`. `interview_turn_ref` links it back to the interview answer it came from, if any.

**`Claim`** — an allegation/claim, with a `status: ClaimStatus` field that is **computed deterministically**, never by the LLM (see `Orchestrator._compute_claim_statuses()` in §7).

**`Evidence`** — an evidence item. `evidence_type`, `file_path` (empty for metadata-only evidence), `description`, `extracted_text`, `extraction_confidence` (`"high"|"medium"|"low"|"none"`, never a bare number), `linked_claim_id`, and `disputed: bool` (default `False` — only ever set via an explicit `PATCH` call, never inferred).

**`DocumentDraft`** — a generated document (`draft_type`, `content`, `generated_at`, `review_status` defaulting to `"ai_draft"`).

**`InterviewTurn`** — one question/answer pair from the dynamic interview. Not in the original CLAUDE.md §10.2 sketch (added later, documented as such). `contradicts_ref` is a **deliberate non-foreign-key polymorphic string reference** — it can point at either a `Statement.id` or another `InterviewTurn.id`, because a contradiction can be against either kind of prior record.

**`AuditLogEntry`** — an append-only log row: `event_type` (a short string like `"claim_added"`), `summary` (human-readable), `payload` (JSON string with full context), `created_at`. This one table does **double duty**: it satisfies both the "audit logging" requirement (CLAUDE.md §7) *and* the "should Case Builder state be versioned" question (§10.2) — instead of building a separate event-sourcing system, replaying `AuditLogEntry` rows in order reconstructs "what did the system know at time T." Explicitly documented limitation: this means reconstructing state is a *replay*, not a single lookup.

---

## 7. Backend — The Orchestrator (the brain)

**File: `backend/app/orchestrator.py`** — the single largest and most important backend file. This is a **hand-coded state machine**, not an LLM-driven planner — a deliberate architecture decision (CLAUDE.md §8.1) because a legal-risk product needs a debuggable, predictable control flow, not an agent that decides its own next steps.

### `CaseStage` enum
`intake → fact_extraction → legal_classification → law_retrieval → evidence_gap_analysis → complete`. This names the conceptual pipeline stages (used more as documentation of intent than a strictly enforced state machine, since most endpoints can be called independently once a case exists).

### The `Orchestrator` class — one method per feature, called directly by `main.py`

| Method | What it does |
|---|---|
| `submit_narrative(case, narrative)` | Calls `FactExtractionAgent`, persists `Event`/`Statement` rows, logs to audit log, runs the jurisdiction-mismatch keyword check |
| `classify_and_retrieve(case)` | Calls `LegalClassificationAgent` then `LawRetrievalAgent`. **Short-circuits** (skips the classification LLM call entirely) if the case has zero statements/events — a bug that was found and fixed multiple times across different callers, then finally centralized here so every caller benefits |
| `_compute_claim_statuses(case)` | **Deterministic, no LLM.** For every claim: no linked evidence → `unsupported`; any linked evidence flagged `disputed` → `disputed`; any linked evidence has low/no extraction confidence → `partially_supported`; otherwise → `supported`. This directly enforces the "facts vs. evidence vs. evidence-backed facts" three-way distinction from CLAUDE.md §11.2 *in code*, not just in prompts |
| `evidence_gap_analysis(case)` | Computes statuses (above), then asks `EvidenceGapAnalysisAgent` only for the "what evidence type would typically help" suggestion — never for the status itself |
| `devils_advocate(case)` | Calls `DevilsAdvocateAgent` with the same fact/claim base every other agent sees |
| `_flatten_retrieved_provisions(retrieval_result)` | Turns the `{category: [hits]}` shape from Law Retrieval into a flat list of `{chunk_id, act_name, section_number, text, effective_from, effective_to, repealed_by}` — deduplicates by `chunk_id` and caps both the count (8) and each provision's text (800 chars) before any agent sees them, fixing a real bug where 15 noisy/overlapping provisions caused Document Generation to lose track of its task entirely (§16, decision 11) |
| `_bind_citations(options, retrieved_provisions)` | **The citation-binding mechanism.** Checks every self-reported `citations` list against the real retrieved `chunk_id`s. Anything that doesn't match a real chunk is silently stripped and returned separately as `unverified_citations_dropped` — this is how the system prevents the LLM from fabricating a citation and having it presented as verified |
| `legal_strategy(case, acknowledged)` | **Gated behind an explicit acknowledgment flag.** If `acknowledged=False`, returns only a disclaimer, no content at all. If `True`, runs classification+retrieval, calls `LegalStrategyAgent`, and binds citations |
| `generate_document(case, draft_type)` | Calls `DocumentGenerationAgent`, persists a `DocumentDraft` row, and (for `complaint`/`legal_notice` only, since those are the types that cite statutes) binds citations the same way as Legal Strategy |
| `next_interview_question(case)` | Checks `INTERVIEW_QUESTION_BUDGET` (hard cap = **10**) first; if under budget, calls `LegalClassificationAgent` (only if facts exist) then `DynamicInterviewAgent` |
| `submit_interview_answer(case, turn_id, answer)` | Persists the answer as a `Statement` (tagged `"unknown"`, not re-run through Fact Extraction — a deliberate scope trade-off), then runs a second LLM call to check for contradictions against every prior statement/answer |
| `add_claim`, `add_evidence`, `add_evidence_with_file` | CRUD for claims/evidence. `add_evidence_with_file` is the one that does OCR/extraction (§10) *before* encrypting and writing to disk |
| `set_evidence_disputed(case, evidence_id, disputed)` | Flips the `Evidence.disputed` flag, logs it, and recomputes claim statuses |
| `list_evidence(case)` | Returns the full evidence inventory (type, description, claim link, confidence, disputed, whether a file exists) for the "organize evidence" UI |
| `audit_log(case)` | Returns every `AuditLogEntry` for a case, in order |
| `_aggregate_band(...)` | **Pure function, no LLM.** Computes one of 3 bands from counts alone (see §15 in this doc for exact thresholds) |
| `case_strength(case)` | Assembles the full non-scored, multi-dimensional case-strength summary: evidence coverage, disputed facts, legal uncertainty, counterarguments, the aggregate band, and flagged inter-agent conflicts |
| `_flag_agent_conflicts(hypotheses, counterarguments)` | **"Surface, don't silently resolve."** If Legal Classification produced hypotheses AND Devil's Advocate produced a `"strong"`-severity weakness, both are shown together as an unresolved tension — no agent's output is ever treated as more authoritative than another's |
| `_try_parse_date(raw)` | Best-effort date parser (tries `%Y-%m-%d`, `%Y-%m`, `%Y`, `%d %B %Y`, `%B %Y`, `%d/%m/%Y`) — unparseable dates are never guessed at, just surfaced separately |
| `timeline(case)` | Sorts events with a parseable date chronologically; everything else goes into a separate `undated_events` list |
| `prepare_questions(case)` | Calls `QuestionPreparationAgent` with the same claim/status payload every other agent gets |

### Jurisdiction-mismatch heuristic
A hardcoded set of ~24 keywords (`"mumbai", "maharashtra", "delhi", "chennai", "tamil nadu", ...` — other Indian states/cities) — `_detect_jurisdiction_mismatch()` scans a submitted narrative for any of these and returns a **non-binding warning** if found, but never auto-changes the case's jurisdiction. Deliberately crude (not NER, not a geocoder) — false positives are accepted because the only effect is a warning.

---

## 8. Backend — The 9 AI Agents

All agents live in `backend/app/agents/` and inherit from `Agent` (`base.py`). Every agent follows the exact same shape: a module-level `SYSTEM_PROMPT` string, a class with `name` and a `run(case_state: dict) -> dict` method that (1) builds a JSON `user_content` payload from the relevant slice of case state, (2) calls the model, (3) parses the JSON response, (4) falls back to a safe empty/error shape if parsing fails.

### `base.py` — the shared foundation
```python
class Agent(ABC):
    def __init__(self):
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=120.0)

    def _call_model(self, system, user_content, max_tokens=2048) -> str:
        response = self._client.post(
            "/api/chat",
            json={
                "model": settings.ollama_model,   # "qwen2.5:7b-instruct"
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "think": False,
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return _strip_code_fence(content or "")
```
**Provider note (3 stages)**: this file originally called Anthropic's Claude API directly. Switched to Google's Gemini free tier (via its OpenAI-compatible endpoint and the `openai` SDK) after the Anthropic key had no funded credit balance. Switched again, same day, to a **fully local model** (Qwen3.5 9B via Ollama) at the user's explicit request to remove all API/network dependency — verified against real, checked hardware first (MacBook Pro, Apple M3 Pro, 18GB unified memory), not assumed to be adequate. Talks to Ollama's **native** `/api/chat` endpoint via `httpx` directly, not the OpenAI-compatible layer — deliberately (see below for why). Because `_call_model`'s signature and return type (a plain string) never changed across any of the three providers, **every one of the 10 agents' prompts/logic and every test needed zero changes each time** — only this file, `config.py`, `pyproject.toml`, and `.env` were touched, each swap.

**Real integration issues found by actually calling each live model, not by reading documentation:**
1. **Both `gemini-3.6-flash` and the original local model, Qwen3.5 9B, are reasoning models.** Each spends hidden "thinking" tokens — counted against the output budget — before producing a visible answer. For Gemini, observed consuming ~70% of a 2048-token budget on one realistic prompt (a truncated response comes back as `finish_reason: "length"` with **empty** content, not an error — easy to misdiagnose as a bug elsewhere); fixed there with `reasoning_effort="low"` (~4x fewer tokens, no quality loss). For local Qwen3.5, the failure was more severe — a 200-token test budget was **entirely** consumed by reasoning with zero visible answer. Neither `reasoning_effort` nor `extra_body={"think": False}` was honored through Ollama's OpenAI-compatible endpoint for this model; only Ollama's **native** endpoint's top-level `"think": false` field actually worked — verified live: a trivial prompt dropped from a botched 200-token truncation to a correct 4-token answer in ~0.5s. This is *why* `base.py` calls Ollama's native API directly via `httpx` instead of going through the `openai` SDK, unlike the Gemini stage.
2. **(2026-09-16) Swapped again, same local setup, for speed: Qwen3.5 9B → `qwen2.5:7b-instruct`.** Warm-call latency dropped from ~15-25s to ~3-4s on the same M3 Pro hardware for a comparable fact-extraction call, verified live. `qwen2.5:7b-instruct` is *not* a reasoning model, so `base.py`'s `"think": false` field is simply ignored by Ollama for it — a harmless no-op, confirmed live, left in place since it's still needed if a reasoning model is configured again later. `Agent._call_model()`'s call shape is otherwise unchanged, so this swap — like the two before it — needed zero changes to any agent's prompt/logic or any test.
2. **Both providers sometimes wrap JSON output in a ` ```json ` markdown fence** despite every system prompt explicitly forbidding it — observed directly with both, not hypothetical. A bare `json.loads()` on a fenced string raises `JSONDecodeError`. Fixed once at the shared source: `_strip_code_fence()` runs inside `_call_model()` itself, so every agent is covered regardless of which parsing pattern it uses.
3. **A syntactically-valid-but-wrong-shaped JSON response can still crash a caller.** Running the full pipeline live against the local model, `document_generation.py` crashed with `AttributeError: 'list' object has no attribute 'setdefault'` — the model had returned a valid JSON *array* where every agent's contract requires a JSON *object*, and `json.loads()` alone doesn't catch that. Fixed in `_call_model_json()` with an `isinstance(parsed, dict)` check, treating a wrong-shaped response the same as invalid JSON (triggers the same repair-retry). This is also *why* the 6 agents that used to do a bare `try: json.loads(raw) except json.JSONDecodeError` were all migrated to `_call_model_json()` the same session — they had the identical latent exposure.

`_call_model_json(system, user_content, max_tokens=2048, retries=1)` calls the model, tries `json.loads` **and** validates the result is a `dict`, and if either check fails, **retries once** with a repair prompt that includes the original request plus the invalid output, asking for corrected JSON. Every one of the 10 agents now uses this helper — a bare unrecovered `json.loads` no longer exists anywhere in the agent layer.

### The 10 agents, one by one

| # | Agent (file) | Role | LLM call? | Key behavioral rule |
|---|---|---|---|---|
| 1 | `fact_extraction.py` | Turns raw narrative text into structured `entities`, `events`, and `statements` (each tagged fact/assumption/opinion/allegation/unknown) | Yes, uses `_call_model_json` (retry-enabled) | Never merges distinct people/events; never tags opinion as fact; ambiguous → `"unknown"`, never silently dropped |
| 2 | `legal_classification.py` | Proposes a **ranked list of candidate** legal categories with rationale + confidence (`low`/`medium`/`high`) | Yes, `_call_model_json` (retry-enabled) | Never invents a section number — that's Law Retrieval's job. Never narrows to one theory |
| 3 | `law_retrieval.py` | Retrieves real statute sections for each classification hypothesis | **No** — pure `query_provisions()` calls against ChromaDB | Hard requirement (CLAUDE.md §8.4): no provision is ever surfaced without a real retrieval hit. Returns `insufficient_data: true` honestly when nothing matches |
| 4 | `evidence_gap_analysis.py` | For each claim, suggests what *type* of evidence would typically help (e.g. "CCTV footage", "medical report") | Yes, `_call_model_json` | Never comments on whether a claim is true/likely — that's out of scope. Support status itself is computed by the orchestrator, not this agent |
| 5 | `devils_advocate.py` | Finds weaknesses, contradictions, and plausible opposing arguments using **only the existing facts** | Yes, `_call_model_json` | Cannot invent new facts to attack. Every weakness gets a `severity`: `strong`/`moderate`/`weak` |
| 6 | `legal_strategy.py` | Ranks possible legal approaches and names one "currently strongest" option | Yes, `_call_model_json` | Citations must be exact `chunk_id`s from what was actually retrieved (checked programmatically afterward). Framed as "based on currently known facts, X appears strongest" — never an imperative "you should do X" |
| 7 | `document_generation.py` | Drafts one of 7 document types from verified case state | Yes, `_call_model_json`, `max_tokens=4096` (higher than the 2048 default, since documents are longer) | Missing details become `[PLACEHOLDER]` text, never invented. Reports which `citations_used` it relied on, checked against real retrieved chunks afterward |
| 8 | `dynamic_interview.py` | Two operations: `next_question` (pick the single most legally material next question) and `check_contradiction` (does a new answer conflict with a prior statement/answer?) | Yes, both operations use `_call_model_json` | Has a hardcoded opening-narrative shortcut (no LLM call) when there are zero facts yet — just asks "Can you describe what happened?" |
| 9 | `question_preparation.py` | Generates questions the person might face (from opposing side/investigator/clarification) plus grounded suggested responses | Yes, `_call_model_json` | If a response can't be built from known facts, `suggested_response` is `null` + a `gap_note` explaining why — never a fabricated plausible-sounding answer |
| 10 | `claim_synthesis.py` | Proposes distinct claims/allegations from known statements/events, consolidated into plain-language sentences | Yes, `_call_model_json` | Not in CLAUDE.md's original §8 agent roster — added later to back the "suggest claims" UI action. Every claim must be grounded in given statements/events; returns `[]` rather than forcing one when nothing rises to the level of a claim. `Orchestrator.suggest_claims()` persists proposals as real `Claim` rows immediately (not a separate "suggestion" layer) and skips any whose text already matches an existing claim case-insensitively |

### Every agent's short-circuit pattern
Every agent that operates on case-level state (all except Law Retrieval, which has no such notion) checks whether it has *any* input to work with before calling the LLM at all — if statements/events/claims are all empty, it returns an `insufficient_case_state: True` shape directly, with **zero API calls made**. This is verified by tests that literally assert the mock would raise if called (see §12).

---

## 9. Backend — The RAG / Legal Knowledge Pipeline

**File: `backend/app/ingestion.py`** — turns the 13 raw legal PDFs into 2,761 searchable, metadata-tagged chunks inside ChromaDB.

### Pipeline steps
1. **Extract text** (`extract_text(path)`) — `pypdf.PdfReader` pulls text page-by-page for `.pdf` files; plain `.txt` files are read directly.
2. **Clean text** (`clean_text(text)`) — strips bare page-number-only lines (regex `^\s*\d{1,4}\s*$`), collapses 3+ consecutive newlines down to 2, strips trailing whitespace before newlines.
3. **Chunk by section** (`chunk_by_section(text)`) — the core regex:
   ```python
   _SECTION_HEADER_RE = re.compile(r"^[ \t]*(?:\d+\[)?(?:Section\s+)?(\d+[A-Z]?)\.[ \t]*(.*)$", re.MULTILINE)
   ```
   Matches lines like `"103. Punishment for murder."` or `"Section 122."`, capturing the section number (group 1, e.g. `"103"` or `"103A"`) and the rest of that line as the title (group 2). Everything between one match and the next becomes that section's chunk text. **Three real bugs found and fixed during this project**:
   - The gap between the number and the title was originally `\s*` (matches newlines too), which let a stray "Section 122." cross-reference in one PDF swallow an entire following real section header into a mislabeled chunk. Changed to `[ \t]*` (same-line whitespace only) to fix it — chunk count went from 5,091 to 5,136 after the fix.
   - **(2026-09-17) Table-of-Contents duplicates.** Every statute PDF also lists each section's number/title again in its own front-matter TOC — the header regex matched those lines identically to the real section body, producing a short title-only chunk (e.g. `"101. Murder."`, 12 characters) that outranked the real, 6,000+ character explanatory section in vector search purely by exact-keyword coincidence. This was the actual cause of "view in source" landing on the TOC page rather than the real explanation. Fixed with `_drop_table_of_contents_duplicates()`: for any repeated `section_number` within a file, keep only the chunk with the most text.
   - **(2026-09-17) Footnote-marker-prefixed headers.** 49 sections across 5 documents print an amended/inserted section with a leading footnote-index marker (e.g. `"3[15. Terrorist act .—..."`), which the old regex's line-start anchor never matched at all — those real section bodies were silently absorbed into the wrong chunk and were completely unretrievable under their own section number. Fixed by adding the optional `(?:\d+\[)?` prefix above. Also required deleting a file's previously-ingested chunk IDs before re-upserting on a change (`ingest_all()` previously only ever added-or-replaced IDs, never removed ones that no longer exist after re-chunking, which left stale duplicates behind after the TOC fix alone). Corpus re-ingested: 5,136 → 2,761 chunks (the drop is entirely the removed TOC duplicates).
4. **Metadata tagging** — every chunk gets: `act_name` (the filename stem, e.g. `"BNS_2023"`), `section_number`, `section_title` (truncated to `_TITLE_MAX_LEN = 120` characters), `tier` (1/2/3), `jurisdiction`, `source_file`, and **effective-date metadata** (see below).
5. **Effective-date metadata** (`ACT_EFFECTIVE_DATES` table) — a hand-built dictionary mapping each of the 13 act names to `{effective_from, effective_to, repealed_by, successor_of}`, e.g.:
   ```python
   "BNS_2023": {"effective_from": "2024-07-01", "effective_to": None, "repealed_by": None, "successor_of": "IPC_1860"}
   "IPC_1860": {"effective_from": "1862-01-01", "effective_to": "2024-06-30", "repealed_by": "BNS_2023", "successor_of": None}
   ```
   This directly supports the **dual-code problem**: India replaced IPC/CrPC/Evidence Act with BNS/BNSS/BSA on **1 July 2024**, so the system must be able to retrieve the *historically correct* provision for events before that date, not just the newest one. Values are best-effort from public knowledge, explicitly not re-verified against the government gazette per-document.
6. **Embedding & indexing** — `collection.upsert(ids=..., documents=[chunk text], metadatas=[...])` into ChromaDB, using Chroma's default embedding function (no custom embedding model chosen — an explicit v1 simplification).
7. **Change detection** (`ingest_all(force=False)`) — computes a SHA-256 checksum per source file (stored in `.ingestion_checksums.json`), skips re-embedding any file whose checksum hasn't changed. This is the **detection** half of "automated periodic re-check" (CLAUDE.md §12.4) — there is no scheduler/cron job (the **scheduling** half was deliberately not built for a local/dev target).

### Document tiers (the actual legal corpus — 13 real PDFs)
| Tier | Folder | Documents | Jurisdiction |
|---|---|---|---|
| 1 — Core legislation | `01-core-legislation/` | BNS 2023, BNSS 2023, BSA 2023 (current codes) + IPC 1860, CrPC 1973, Indian Evidence Act 1872 (historical, pre-July-2024 predecessors) | India (central) |
| 2 — Central special laws | `02-central-special-laws/` | POCSO 2012, NDPS 1985, UAPA 1967, IT Act 2000 | India (central) |
| 3 — Karnataka state laws | `03-karnataka-state-laws/` | Karnataka Police Act 1963, KCOCA 2000, Karnataka "Goonda" Act 1985 | India – Karnataka |

**Tiers 4 (judicial precedents) and 5 (police manuals) were researched and explicitly descoped** — no viable citator data source exists at portfolio-project cost (real citators are subscription-only), and no public source for a Karnataka police manual exists.

---

## 10. Backend — Evidence Handling & Encryption

### `backend/app/evidence_extraction.py`
Given raw file bytes and a file extension, returns `(extracted_text, confidence)` where confidence is always one of the literal strings `"high"`, `"medium"`, `"low"`, `"none"` — deliberately never a bare number, since the underlying tooling isn't precise enough to justify one.

- **PDF** (`_extract_pdf`): `pypdf.PdfReader` on an in-memory `io.BytesIO`. If any text layer exists → `"high"`. Empty text (a scanned/image-only PDF) → `"low"` with empty text. Scanned-PDF OCR is explicitly **not** supported (would need `poppler`/`pdf2image`, not installed).
- **Image** (`_extract_image`, for `.png/.jpg/.jpeg/.tiff/.bmp`): `pytesseract.image_to_data()` returns per-word confidence scores. Average confidence **≥ 80 → `"high"`**, **≥ 50 → `"medium"`**, below that → `"low"`. No text detected at all → `"none"`.
- **Plain text**: `"high"` if non-empty, `"none"` if empty.

Operates on **raw bytes**, not a file path — this was a deliberate refactor so extraction always happens on plaintext *in memory*, before any encryption/disk write, meaning a plaintext copy of an uploaded file never touches disk at all, not even transiently.

### `backend/app/encryption.py`
Implements **encryption-at-rest for evidence files only** (not the SQLite database — that was an explicit scope decision after weighing cost/benefit; full DB encryption via SQLCipher would need a different DB driver and was judged disproportionate for a local-only build with no real user data).

- Uses `cryptography.fernet.Fernet` (symmetric encryption).
- `encrypt_bytes(data)` / `decrypt_bytes(data)` — thin wrappers.
- **Key management**: if `settings.evidence_encryption_key` (env var `EVIDENCE_ENCRYPTION_KEY`) is set, that's used. Otherwise, a key is auto-generated on first use and **persisted** to `data/.evidence_encryption_key` (gitignored) so encrypted files stay decryptable across dev-server restarts. This is explicitly *not* real production key management (no secrets manager/KMS integration) — flagged as an open item, not silently declared solved.
- `Orchestrator.add_evidence_with_file()` calls `extract_text_and_confidence()` on the plaintext bytes first, then writes only `encrypt_bytes(file_bytes)` to disk, with a `.enc` filename suffix.
- `decrypt_bytes()` raises `cryptography.fernet.InvalidToken` on data it didn't encrypt — deliberately **not** caught and silently treated as plaintext, since that would defeat the point.

---

## 11. Backend — API Layer (main.py)

**File: `backend/app/main.py`** — the FastAPI app. Every endpoint follows the same pattern: look up the `Case` by ID (return `{"error": "case not found"}` if missing), instantiate an `Orchestrator(db)`, call the relevant method, return its result merged with `case_id`.

### All endpoints (25 routes)
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/cases` | Create a case (optional `jurisdiction` override) |
| `GET` | `/cases/{id}` | Look up a case (used to validate a locally-remembered `case_id` still exists) |
| `GET` | `/documents/{filename}` | Serve a raw source PDF from the ingested corpus. With `?section=&page=` query params (added 2026-09-17), serves a copy with that section's own text highlighted (see `pdf_highlight.py`, §9) instead of the plain file |
| `POST` | `/cases/{id}/narrative` | Submit narrative → fact extraction |
| `POST` | `/cases/{id}/classify` | Run classification + retrieval |
| `GET` | `/cases/{id}/claims` | List claims (with deterministically computed status) |
| `POST` | `/cases/{id}/claims` | Add a claim |
| `POST` | `/cases/{id}/claims/suggest` | Auto-propose grounded claims from known facts (Claim Synthesis agent) and persist them as real `Claim` rows |
| `PATCH` | `/cases/{id}/claims/{claim_id}` | Edit a claim's description (status is never directly settable) |
| `DELETE` | `/cases/{id}/claims/{claim_id}` | Delete a claim |
| `POST` | `/cases/{id}/evidence` | Add metadata-only evidence |
| `POST` | `/cases/{id}/evidence/upload` | Upload a real file (multipart), triggers OCR + encryption |
| `GET` | `/cases/{id}/evidence` | List the full evidence inventory |
| `PATCH` | `/cases/{id}/evidence/{evidence_id}/dispute` | Toggle an evidence item's disputed flag |
| `POST` | `/cases/{id}/evidence-gaps` | Run evidence gap analysis |
| `POST` | `/cases/{id}/devils-advocate` | Run Devil's Advocate |
| `POST` | `/cases/{id}/strategy` | Run Legal Strategy (gated by `acknowledged: bool`) |
| `POST` | `/cases/{id}/documents` | Generate a document draft |
| `POST` | `/cases/{id}/interview/next-question` | Get the next interview question |
| `GET` | `/cases/{id}/interview/turns` | List the interview conversation so far (rebuilds it after a page reload/tab remount) |
| `POST` | `/cases/{id}/interview/answer` | Submit an interview answer |
| `GET` | `/cases/{id}/strength` | Get the case-strength summary |
| `GET` | `/cases/{id}/timeline` | Get the sorted timeline |
| `GET` | `/cases/{id}/audit-log` | Get the full audit log |
| `POST` | `/cases/{id}/questions` | Prepare Q&A |

### Global exception handler
```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    logger.exception(...)
    return JSONResponse(status_code=500, content={"error": "internal server error"}, headers=CORS-header-if-origin-matches)
```
This exists because of a **real bug found via live browser testing**: without it, an unhandled exception (e.g. a missing API key) propagated past FastAPI's `CORSMiddleware` entirely, and the browser reported a misleading "blocked by CORS policy" error instead of the real 500 error.

CORS is configured to allow only `http://localhost:5173` (the Vite dev server origin) — no wildcard, since this is a local-dev-only build.

**No authentication anywhere** — this is a deliberate v1 decision (session-only, no accounts). Anyone who knows a `case_id` (a UUID) can read/modify that case. Acceptable only under the "synthetic/demo data, portfolio scope" assumption.

---

## 12. Backend — Test Suite

**116 automated tests across 28 files**, run with `pytest`. Almost all tests **mock the LLM call** (`monkeypatch.setattr(SomeAgent, "_call_model", fake_function)`) so the test suite runs instantly and doesn't need any model running at all, local or remote. This also makes the tests **provider-agnostic**: none needed to change across any of the three provider switches (Anthropic → Gemini → local Ollama, §16), since they mock `_call_model` itself, not any provider-specific client. The deliberate exceptions are `test_retrieval_accuracy.py`, `test_citation_accuracy.py`, and (added 2026-09-17) `test_pdf_highlight.py` and parts of `test_document_serving.py`, which all run against the **real ingested ChromaDB corpus and real source PDFs** (no mocking) because their entire purpose is to verify real retrieval/highlighting quality — none of that involves the LLM at all (§8's Law Retrieval Agent; `pdf_highlight.py` is pure PyMuPDF text search), so those files were unaffected by every provider switch too.

### `conftest.py`
Sets up an **isolated in-memory SQLite database** (`sqlite:///:memory:` with `StaticPool`) and overrides FastAPI's `get_db` dependency to use it instead of the real dev database file — this exists because of a bug found early on where the test suite was accidentally writing into the real dev DB. An `autouse=True` fixture wipes every table between tests.

### Test files, grouped by what they prove
| File | What it verifies |
|---|---|
| `test_health.py` | Basic liveness + case creation |
| `test_ingestion.py` | Chunking regex correctness (including the "Section 122." regression case), effective-date lookup table |
| `test_ingestion_change_detection.py` | SHA-256 checksum logic, checksum persistence, text cleaning |
| `test_retrieval_accuracy.py` | **14 real gold-standard queries** against the live corpus (e.g. "punishment for murder" → BNS §103; "criminal intimidation" → both BNS §351 *and* historical IPC §503, proving dual-code retrieval works). 10 remain passing "top-hit" assertions; **4 are now documented known-weakness markers** (POCSO/NDPS chunking, plus 3 added 2026-09-17 — "theft", the UAPA §15 terrorist-act query, and the electronic-record/§65B query — which used to pass only because the TOC-duplicate bug's exact-title-match coincidentally won; removing that bug exposed a real embedding-ranking weakness against long legal text for short/generic queries, not a chunking regression) |
| `test_citation_accuracy.py` | Every one of the 2,761 real chunks' `section_number` label actually matches its own text (self-consistency check, tolerating the footnote-marker prefix — see §9) + a marker documenting the still-missing semantic entailment check |
| `test_pdf_highlight.py` | `render_highlighted_pdf()` against the real BNS_2023.pdf: adds real highlight annotations on the correct page only, returns `None` for an unfound section or out-of-range page |
| `test_document_serving.py` | `GET /documents/{filename}`, including the `?section=&page=` highlight params and their fallback-to-plain-file behavior |
| `test_jurisdiction.py` | Explicit jurisdiction override, default value, mismatch-warning heuristic |
| `test_fact_extraction_retry.py`, `test_legal_classification_retry.py` | The JSON retry/repair helper recovers from one malformed response and still falls back correctly if retry also fails, and treats a wrong-shaped-but-valid response (e.g. a JSON array where a dict is required) the same as invalid JSON |
| `test_code_fence_stripping.py` | Markdown-fenced JSON responses (seen with both cloud and local models) are stripped before parsing, at the real `_call_model()` call site, not a mock of it |
| `test_retrieved_provisions_capping.py` | The real Document Generation bug fix: `_flatten_retrieved_provisions()` deduplicates by `chunk_id` and caps count/text length so an agent's prompt never gets overwhelmed by noisy retrieval results |
| `test_evidence_upload.py` | Real OCR (via a generated test image) and real PDF text extraction |
| `test_evidence_gap_analysis.py`, `test_evidence_dispute.py` | Deterministic claim-status computation across all four `ClaimStatus` values |
| `test_encryption.py` | Fernet round-trip, rejection of non-encrypted data, and an end-to-end real-file-upload test proving the on-disk bytes are genuinely not the plaintext |
| `test_devils_advocate.py`, `test_legal_strategy.py`, `test_document_generation.py`, `test_dynamic_interview.py`, `test_question_preparation.py` | Each agent's short-circuit-on-empty-case behavior, gating logic, and citation-binding/fabrication-stripping |
| `test_timeline.py` | Chronological sort with mixed dated/undated events |
| `test_audit_log.py` | Every mutation gets logged, in order |
| `test_case_strength.py` | The aggregate band is **never** a numeric score (a test literally walks the entire response tree checking for forbidden keys like `score`/`probability`), conflict-flagging logic |
| `test_adversarial.py` | **Hallucination test**: proves citation binding does NOT catch a fabricated section number embedded directly in prose (a documented gap, not a fix). **Overconfidence test**: proves the aggregate band can't reach "well-documented" while an unresolved contradiction exists, even if every other condition is met |
| `test_error_handling.py` | The global exception handler returns clean JSON with correct CORS headers instead of a raw 500 |

---

## 13. Data Directory

- **`data/raw/criminal-law/`** — the source-of-truth legal corpus: 13 real PDF files across 3 tiers (see §9), a `MANIFEST.md` recording exactly which government/quasi-official URL each PDF was downloaded from (with honesty flags where a source was a secondary aggregator rather than the official government site), and `.ingestion_checksums.json` (auto-generated, tracks per-file SHA-256).
- **`data/db/legal_lens.db`** — the live SQLite database file. Regenerated automatically on backend startup (`Base.metadata.create_all(bind=engine)` in `main.py`). Gitignored.
- **`data/vector_store/`** — ChromaDB's on-disk persistence (an HNSW index plus a `chroma.sqlite3` metadata store). Regenerated by running `python -m app.ingestion`. Gitignored.
- **`data/evidence/`** — Fernet-encrypted uploaded evidence files (`.enc` suffix). Gitignored.
- **`data/.evidence_encryption_key`** — the auto-generated Fernet key. Gitignored (it's a secret).

---

## 14. Frontend

A single-page React app (no router — but not a flat undifferentiated stack either: a real 3-stage tab flow, see below. A full visual/UX design pass — a design system, illustrations — was still not done, tracked as an honest limitation).

### `App.tsx`
The top-level component. Flow: `startCase()` → `POST /cases` → `ChatPanel` handles narrative intake conversationally → `submitNarrative()` → `POST /cases/{id}/narrative` → on success, `factsSubmitted` flips to `true` and the view auto-advances to the "Case Dashboard" tab. Always shows a persistent yellow disclaimer banner: *"This is an early development build. Nothing here is legal advice — all output is an AI-generated draft that requires professional review before any reliance on it."*

**Case resume on reload**: the active `case_id`, whether the narrative has been submitted, and the current stage are all mirrored into `localStorage`. On mount, a stored `case_id` is validated against the real backend (`GET /cases/{id}`) before being trusted — a stale id (e.g. a reset dev database) is discarded rather than shown as if it still worked.

**The 3-stage tab flow** (added 2026-08-26, closing what had been an honest gap — "no user flow designed, just every panel stacked vertically"): a `STAGES` array (`interview` / `dashboard` / `review`) drives a tab bar (`tabBarStyle`/`tabButtonStyle` in `shared.ts`). The Dashboard and Review tabs are `disabled` until `factsSubmitted` is true, since nothing in them is meaningful before a narrative exists. Each stage, once mounted, stays mounted (hidden via CSS on tab switch, not unmounted) so switching tabs never resets a panel's own state.

| Stage | Panels shown |
|---|---|
| **1. Interview** | `ChatPanel` (narrative intake + interview Q&A), then `TimelinePanel` |
| **2. Case Dashboard** | `ClaimsEvidencePanel`, plus an "Analyze the case" button that batches `ClassificationPanel`, `DevilsAdvocatePanel`, `StrategyPanel`, `QuestionPreparationPanel` together (each also has its own individual run button). The batch button becomes clickable again whenever a claim or evidence item changes (`caseStale` state) |
| **3. Document Review** | `DocumentsPanel`, `CaseStrengthPanel`, `AuditLogPanel` |

This maps directly onto the case lifecycle: gather facts → build and analyze the case → draft and review documents.

### `api.ts`
A typed fetch client. Defines TypeScript types mirroring every backend response shape (`Claim`, `Evidence`, `ClassifyResult`, `CaseStrengthResult`, etc.) and one function per endpoint under a single `api` object, e.g. `api.createCase()`, `api.submitNarrative(caseId, narrative)`, `api.disputeEvidence(caseId, evidenceId, disputed)`. Internal helpers: `get`, `post`, `postForm` (multipart), `patch`, `del`.

### The 10 panel components (`src/components/`)
Each panel is self-contained: its own `useState` for the result and loading flag, a button that calls the corresponding `api.*` function, and a render of the result. Notable ones:
- **`ChatPanel.tsx`** (renamed from `InterviewPanel.tsx`) — handles both the initial narrative submission and the follow-up dynamic-interview Q&A in one conversational thread; shows a contradiction warning banner if the backend flags one.
- **`ClaimsEvidencePanel.tsx`** — the most complex panel: add claims, add evidence (with optional file upload), run evidence-gap analysis, and an "Organize evidence" view that groups evidence by linked claim with a "Mark disputed"/"Clear dispute" toggle button per item.
- **`ClassificationPanel.tsx`** — also builds the "View in source" link for each retrieved provision: `?section=&page=` query params request a copy of the source PDF with that provision's own text highlighted server-side (`pdf_highlight.py`, added 2026-09-17), rather than relying on the browser's own "find in page".
- **`StrategyPanel.tsx`** — implements the acknowledgment gate as a real two-step UI: first shows only the disclaimer with an "I understand" button, and only *after* that click does it re-request with `acknowledged: true` and show actual content.
- **`CaseStrengthPanel.tsx`** — renders the coarse `aggregate_band` (color-coded label) alongside every disaggregated section (evidence coverage, disputed facts, legal uncertainty, counterarguments, flagged inter-agent conflicts).
- **`DocumentsPanel.tsx`** — a `<select>` of the 7 draft types, shows the generated content in a `<pre>` block, and (if any) a red citation-warning banner listing unverified citations that were dropped.

### `shared.ts`
Three exported style constants used across panels: `panelStyle` (bordered card), `buttonStyle`, and `severityColor` (maps `"strong"/"moderate"/"weak"` to red/orange/gray).

### Build tooling
- **Vite** (`vite.config.ts`) — just the React plugin, no customization.
- **TypeScript**, strict-ish config (`noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`).
- **oxlint** — a fast Rust-based linter, configured with React hooks rules.
- No CSS framework — plain inline `style={{...}}` objects and two small `.css` files.

---

## 15. Every Important Constant / Hyperparameter, In One Table

| Constant | Value | Where | Meaning |
|---|---|---|---|
| `ollama_model` | `"qwen2.5:7b-instruct"` | `config.py` | One model for every agent, no per-agent differentiation. Was `qwen3.5:9b-q4_K_M` (swapped 2026-09-16 for ~4-6x lower latency), before that `gemini-3.6-flash` (Google), and before that `"claude-sonnet-5"` (Anthropic) — three provider/model swaps total, §16 |
| `think` (Ollama request field) | `False` | `base.py` | Disabled Qwen3.5's reasoning mode when that was the active model (native API only, not the OpenAI-compat layer); a harmless no-op for the current `qwen2.5:7b-instruct`, which isn't a reasoning model |
| Local hardware | MacBook Pro, Apple M3 Pro, 18GB unified memory | verified via `sysctl`/`system_profiler` | Confirmed sufficient for a 9B Q4 model before adopting it |
| LLM `temperature` | *(unset — API default)* | `base.py` | Never explicitly tuned |
| `max_tokens` (default) | `2048` | `base.py` | Applies to 9 of 10 agents |
| `max_tokens` (Document Generation) | `4096` | `document_generation.py` | Higher because drafted documents are longer |
| `_call_model_json` retries | `1` | `base.py` | One repair attempt on malformed JSON before giving up |
| `query_provisions` default `n_results` | `5` | `vector_store.py` | Top-5 chunks per retrieval query |
| `INTERVIEW_QUESTION_BUDGET` | `10` | `orchestrator.py` | Hard cap on interview questions per case |
| OCR confidence: high | avg word confidence **≥ 80** | `evidence_extraction.py` | Tesseract's own 0–100 per-word confidence, averaged |
| OCR confidence: medium | **≥ 50** | `evidence_extraction.py` | |
| OCR confidence: low / none | below 50 / no words detected | `evidence_extraction.py` | |
| `_TITLE_MAX_LEN` | `120` chars | `ingestion.py` | Section-title truncation during chunking |
| Aggregate band: `well-documented` | support ratio **≥ 0.7** AND 0 unresolved contradictions AND ≤ 1 hypothesis | `orchestrator.py` (`_aggregate_band`) | Deterministic, no LLM |
| Aggregate band: `partially-documented` | support ratio **≥ 0.3** OR any claims exist | `orchestrator.py` | |
| Aggregate band: `early-stage` | everything else (incl. zero claims) | `orchestrator.py` | |
| Real ingested chunk count | **2,761** | ChromaDB, from `ingest_all()` | After the 2026-09-17 TOC-duplicate/footnote-marker fixes (was 5,136 before, 5,091 before the section-regex bugfix) |
| Source legal documents | **13 PDFs**, 3 tiers | `data/raw/criminal-law/` | |
| BNS/BNSS/BSA effective date | **2024-07-01** | `ingestion.py` `ACT_EFFECTIVE_DATES` | The India-wide criminal-code transition date |
| IPC/CrPC/Evidence Act `effective_to` | **2024-06-30** | same | Historical codes' cutoff |
| Backend test count | **116 tests**, 28 files | `backend/tests/` | |
| CORS allowed origin | `http://localhost:5173` | `main.py` | Vite dev server only |
| Page-number strip regex | `^\s*\d{1,4}\s*$` | `ingestion.py` | Removes bare page-number lines during cleaning |
| Section header regex | `^[ \t]*(?:Section\s+)?(\d+[A-Z]?)\.[ \t]*(.*)$` (MULTILINE) | `ingestion.py` | The core chunking regex — see §9 for the bug history |

---

## 16. Key Design Decisions & The Reasoning Behind Them

These are the decisions most likely to come up in a viva — each one traded something off deliberately, and CLAUDE.md documents the reasoning in full. Condensed here:

1. **Orchestrator = hand-coded state machine, not an LLM planner.** Safer/more debuggable for a legal-risk product; an LLM deciding its own next action would be harder to audit and test deterministically.
2. **Every legal citation must trace to a real retrieved chunk (§8.4, §12.6).** `LawRetrievalAgent` makes zero LLM calls — it's pure database query, so it is structurally impossible for it to "recall" a section number from the model's parametric memory. Citation *binding* (chunk_id membership check) then guards every downstream agent that cites something.
3. **No single win-probability score, ever (§15.1).** Replaced with one coarse, deterministic 3-band signal *shown alongside* full disaggregated detail — verified by a test that scans the entire API response tree for forbidden score-shaped keys.
4. **Agents never resolve conflicts with each other — they surface them.** `_flag_agent_conflicts()` juxtaposes Legal Classification's hypotheses against Devil's Advocate's strong weaknesses rather than picking a "winner"; there's no principled basis for the orchestrator to decide which agent is more right.
5. **First-wave legal domain = criminal law**, deliberately the *higher-risk* choice over the originally-recommended lower-risk consumer-protection domain — chosen specifically because it exercises the hardest problems (the IPC→BNS dual-code transition, sensitive domains like POCSO) early.
6. **No authentication.** Session-only, `case_id` possession = access. Smaller attack surface (no credential storage) but zero real access control — acceptable only because this uses synthetic/demo data, never real users' real legal matters.
7. **AI-draft watermarking was implemented, then explicitly removed** at the project owner's instruction, then **twice re-confirmed** as staying removed when asked again later. This is documented as a real narrowing of the product's safety posture, not hidden.
8. **Encryption scoped to evidence files only, not the whole database** — a direct cost/benefit call: SQLCipher would need a new DB driver and connection-string surgery, judged disproportionate for local/dev data with no real users, whereas evidence-file encryption (Fernet) was a contained, real, already-designed piece of scope.
9. **Data-retention deletion endpoint was designed but never built** — the open question of whether audit-log entries should survive a case's deletion (compliance value) or be deleted with it (literal "erasure on request") was never resolved, so building the endpoint would have baked in an unreviewed answer.
10. **LLM provider switched twice on 2026-08-26 — Anthropic → Gemini → fully local.** The first switch (to Gemini's free tier) was a practical necessity: the Anthropic account had no funded credit balance. The second (to a local model via Ollama) was a deliberate, explicit user choice to remove the API/network dependency entirely — not forced by a further blocker. Real hardware was checked before picking a model (MacBook Pro, Apple M3 Pro, 18GB unified memory), and what was already installed was used as-is (Qwen3.5 9B, already pulled via Ollama) rather than downloading something else. Both swaps stayed contained to `_call_model()`'s internals — every agent's prompt/logic and every test needed zero changes each time, proving the provider-agnostic design of the `Agent` base class held up under two real swaps, not just in theory. A genuine side benefit of going local: sensitive narrative content no longer leaves the machine for LLM calls at all, resolving cross-border-data and training-opt-in questions that had been left open (and re-opened) for both cloud providers.
11. **"Model capability limit" turned out to be wrong — a real bug, investigated instead of assumed.** After the local switch, Document Generation initially seemed unable to produce valid output where the other 8 agents worked fine, and the first-pass explanation was "a 9B quantized model just can't handle the longest/most complex prompt." That explanation was never actually verified — so it was tested directly: calling the agent with the exact failing case's payload showed the model wasn't refusing or degrading gracefully at all, it was **losing track of the task under 15 retrieved provisions** (5 hits × 3 classification hypotheses, mostly duplicates and irrelevant matches) and echoing back a fragment of its own input as if it were the answer. Fixed by deduplicating and capping what `Orchestrator._flatten_retrieved_provisions()` hands to any agent (8 provisions max, 800 chars of text each) — after which Document Generation produced a correct, well-cited complaint draft on the exact same scenario that had been failing. The lesson generalizes past this one bug: a plausible-sounding explanation for a failure ("the model just isn't good enough") is not the same as a verified one, and the honest move when you're not sure is to go check, not to write it down as settled.

---

## 17. Known Limitations — Deliberately Left Incomplete

Say these out loud in a viva *before* you're asked — it shows the project was engineered with discipline, not that it's unfinished by accident.

- **No sentence-level citation entailment check.** The system verifies a *cited chunk_id was really retrieved*, but does not verify that generated *prose* text accurately represents what that section actually says. A test (`test_adversarial.py`) deliberately proves a fabricated section number embedded directly in prose (outside the checked citations list) survives untouched.
- **POCSO/NDPS retrieval quality is worse than the rest of the corpus** — a naive section-chunker limitation (those PDFs format amendment-history text in a way the regex doesn't distinguish from substantive offence text). Documented via a marker test, not silently hidden.
- Systematic evaluation against a labeled gold-standard set of scenarios (not just the one hand-reviewed `e2e_smoke.py` run) hasn't been done yet.
- **No legal-expert review** of any output — genuinely blocked, no such resource available to this project.
- **The SQLite database and ChromaDB's own storage are unencrypted.** Only evidence files are encrypted at rest.
- **No data-retention/deletion endpoint.**
- **No privacy policy** — correctly requires real legal drafting, not an AI-authored substitute.
- **No re-ingestion scheduler** — checksum-based change *detection* exists, but nothing triggers it automatically (no cron job, since this is local/dev only).
- **Similar-case / precedent retrieval is deferred entirely** — no viable citator (overruled/distinguished/followed tracking) data source exists at portfolio-project cost.
- **No full visual/UX design pass** — a 3-stage tab flow (Interview / Case Dashboard / Document Review) now organizes the panels by case lifecycle, but there's no design system, illustrations, or graphic-design work beyond that information architecture.
- **Two Karnataka-act source PDFs (KCOCA, the Goonda Act) came from a secondary aggregator**, not the official government site directly — flagged in `MANIFEST.md` for re-verification.

---

## 18. How To Run This Project

### The easy way: `run.py`

```bash
# One-time: install Ollama (https://ollama.com) and pull a model
ollama pull qwen2.5:7b-instruct

python3 run.py
```
That's it — `run.py` (at the project root) does everything else itself, idempotently (safe to re-run; each step is skipped if already done): creates `backend/.venv` and installs dependencies if missing, creates `backend/.env` from the example if missing, checks Ollama is reachable and the model is pulled (warns but doesn't hard-fail if not), ingests the legal corpus into ChromaDB if it hasn't been already, runs `npm install` for the frontend if `node_modules` is missing, then starts both the backend and frontend together, waits for both to come up, and prints the URLs. `Ctrl+C` (or `kill <pid>` — both `SIGINT` and `SIGTERM` are handled) stops both cleanly, no orphaned processes.

### The manual way (equivalent, step by step)

```bash
# One-time: install Ollama (https://ollama.com) and pull a model
ollama pull qwen2.5:7b-instruct   # or another model — see config.py's OLLAMA_MODEL
# make sure the Ollama app/daemon is running (http://localhost:11434)

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # no API key needed — fully local. Override OLLAMA_MODEL/OLLAMA_BASE_URL if needed.
python -m app.ingestion   # ingest the legal corpus into ChromaDB (run once)
uvicorn app.main:app --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # serves on http://localhost:5173

# Tests
cd backend
python -m pytest -q   # 116 tests, no API key required, no model needed (mocked)
```

---

## 19. Viva / Presentation Cheat Sheet (Q&A prep)

**"What kind of architecture is this?"**
A multi-agent, orchestrator-coordinated pipeline: one hand-coded Python state machine (`Orchestrator`) invokes 10 specialist LLM agents, each with a single narrow responsibility, communicating only through shared structured database state — never talking to each other directly.

**"How do you stop the AI from making up legal citations?"**
Two layers: (1) `LawRetrievalAgent` makes *zero* LLM calls — it only returns text that's really in the ChromaDB vector index, built from 13 real government PDFs. (2) Any agent that cites something afterward (Legal Strategy, Document Generation) self-reports which retrieved chunk IDs it used, and the orchestrator checks that list against what was *actually* retrieved, silently stripping anything that doesn't match. We're honest that this doesn't catch a fabricated citation hidden inside generated prose text — we wrote a test that proves that gap exists.

**"How is 'case strength' shown without a misleading score?"**
Never a number. A pure Python function computes one of three text labels (`early-stage`/`partially-documented`/`well-documented`) from already-known counts (evidence support ratio, contradiction count, hypothesis count) — no LLM involvement, so it can't be talked into a rosier answer — and it's always shown *next to* the full detailed breakdown, never instead of it.

**"What's the RAG pipeline, technically?"**
PDF → `pypdf` text extraction → regex-based section chunking (with metadata: act name, section number/title, tier, jurisdiction, effective dates) → embedded and stored in ChromaDB (its default embedding function) → queried via cosine-similarity search returning top-5 chunks.

**"What was the hardest bug you found?"**
A chunking regex bug where `\s*` (matches newlines) let a stray "Section 122." cross-reference in one PDF swallow the real following section's text into a wrongly-labeled chunk. Found by writing a self-consistency test that checks every chunk's own text against its own label across the *entire real corpus* — not by manual inspection. Fixed by restricting the regex gap to same-line whitespace only.

**"Why no authentication?"**
Deliberate v1 scope decision: this is a portfolio project using synthetic/demo data, not real users' real legal situations. Session-only, no accounts — smaller attack surface, but explicitly not production-ready.

**"What would you build next if this became a real product?"**
Full DB encryption (SQLCipher), a real access-control layer, a data-retention/deletion endpoint, sentence-level citation entailment checking, live-LLM evaluation against labeled scenarios, and — most importantly — actual legal-expert review of every agent's output before this touches a real user's real situation.
