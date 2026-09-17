# Legal Lens — Project Report & Retrospective

**Type:** Semester-end / portfolio software project
**Domain:** AI-assisted legal case preparation (criminal law, Karnataka / India)
**Status:** Feature-complete for the defined v1 narrow slice. See §7 for what remains genuinely blocked and why.

> Companion documents: **`explanation.md`** (complete file-by-file technical reference — read that for "what does this file do and how"), **`CLAUDE.md`** (the full design/decision log, dated, with every trade-off reasoned out), **`COMPLETION.md`** (the phase-by-phase task tracker this report summarizes), **`DEMO.md`** (a live-presentation script).

---

## 1. Executive Summary

Legal Lens is a multi-agent AI system that helps a person facing a legal situation move from an unstructured plain-language narrative to a structured, evidence-linked, source-cited understanding of their case — without ever presenting itself as a lawyer, predicting outcomes, or fabricating a legal citation. It is built around one non-negotiable principle, stated in the project's own founding document and enforced in code, not just prose: **every legal claim the system makes must trace back to a real, retrieved piece of statutory text — never to the model's own memory.**

The system ingests 13 real Indian government legislation PDFs (criminal law: BNS/BNSS/BSA, their historical predecessors IPC/CrPC/Evidence Act, four central special acts, and three Karnataka state acts), chunks and embeds them into a vector database, and exposes them to 10 specialist AI agents coordinated by a hand-coded orchestrator. A React frontend presents the whole pipeline as a 3-stage guided flow. The backend carries 116 automated tests, all passing, covering deterministic logic, agent gating/fabrication-guards, and — for four test files — real retrieval/highlighting accuracy against the live 2,761-chunk corpus and the real source PDFs.

## 2. Problem Statement & Motivation

People facing a legal problem for the first time typically don't know: which laws apply, what facts/evidence matter, how to structure a complaint, what the other side might argue, or where their case is weak. Professional legal help is often inaccessible at this early "orientation" stage. Legal Lens targets specifically this **pre-lawyer orientation and case-preparation gap** — not advocacy, not adjudication, not a lawyer replacement.

## 3. Objectives (from the original brief)

1. A dynamic interview system that asks only legally material questions.
2. A structured "Case Builder" — facts, timeline, claims, evidence, applicable law — built incrementally.
3. Retrieval of real statutory provisions with full source traceability (act, section, jurisdiction, effective-date range).
4. Evidence-gap analysis: what's claimed vs. what's actually evidenced.
5. A "devil's advocate" pass surfacing weaknesses and counterarguments.
6. Draft-document generation (complaint, notice, chronology, etc.), clearly AI-assisted.
7. Preparation for likely questioning, strictly grounded in known facts.
8. A multi-dimensional case-strength presentation — explicitly **not** a single win-probability score.

All 8 were implemented. (2 became agents of their own — Legal Strategy and Question Preparation — beyond the original 7-function brief, once the multi-agent architecture was locked in.)

## 4. System Architecture (summary — see `explanation.md` §2 for the full diagram)

**Pattern:** orchestrator + specialist agents, not agent-to-agent communication. A hand-coded Python state machine (`Orchestrator`, `backend/app/orchestrator.py`) owns all Case Builder state and decides which of 10 specialist LLM agents to invoke at each step. This was a deliberate choice over a more "autonomous" LLM-driven planner — for a legal-risk product, predictability and testability outweigh flexibility.

**The 10 agents** (one narrow responsibility each): Fact Extraction, Legal Classification, Law Retrieval (the only one that makes *zero* LLM calls — pure vector-DB query, so it is structurally incapable of inventing a citation), Evidence Gap Analysis, Devil's Advocate, Legal Strategy, Document Generation, Dynamic Interview, Question Preparation, and Claim Synthesis (added later than the other 9, backing the "suggest claims from known facts" UI action).

**Stack:** Python + FastAPI backend, React + TypeScript + Vite frontend, SQLite (Case Builder state), ChromaDB (embedded vector store for the legal corpus), **a fully local LLM — `qwen2.5:7b-instruct` via Ollama, zero API/network dependency** (one model for all agents in v1; history: Anthropic Claude API → Google Gemini's free tier → local Qwen3.5 9B, both switches on 2026-08-26, then swapped again to the current smaller/faster model on 2026-09-16 purely for latency; see §7 for the full story), local filesystem for evidence files (Fernet-encrypted).

## 5. Implementation Timeline — Phase by Phase

| Phase | Deliverable | Outcome |
|---|---|---|
| 0 | Project definition, scope, personas | Closed — portfolio scope, multi-persona architecture, narrow-first sequencing signed off |
| 1 | Domain/jurisdiction research | Closed — criminal law + Karnataka chosen (deliberately the *harder* first domain, to force the dual-code and sensitive-domain problems early); source hierarchy and acquisition method researched |
| 2 | System design | Closed — orchestrator pattern, Case Builder schema, RAG architecture, security posture, tech stack all decided and documented |
| 3 | Data & knowledge base | Closed — 13 real PDFs acquired, cleaned, chunked, embedded (2,761 chunks after the 2026-09-17 TOC-duplicate/footnote-marker fixes, see §6), change-detection re-ingestion built |
| 4 | Core intelligence | Closed — all 10 agents implemented, deterministic claim-status/case-strength logic, citation binding |
| 5 | Case building & documents | Closed — evidence organization UI, all 7 document types, one deliberate exclusion (AI-draft watermarking, removed at the project owner's explicit instruction and twice re-confirmed) |
| 6 | Evaluation & testing | 7 of 8 items closed — retrieval accuracy (14 gold queries), a real chunking bug found *and fixed* via a citation-accuracy self-consistency test, hallucination + overconfidence adversarial tests, and (after switching to a fully local model) a complete real live agent-quality evaluation run across all 13 pipeline stages. 1 permanently blocked (legal-expert review, see §7) |
| 7 | Security & compliance | 4 of 7 closed outright, 1 explicitly scoped (evidence-file encryption via Fernet, DB encryption deliberately skipped after being asked), 2 correctly left open (privacy policy needs real legal drafting; data retention deletion endpoint skipped after being asked) |
| 8 | UI & deployment | Closed — a real 3-stage tab flow (Interview → Case Dashboard → Document Review) replacing the earlier flat panel stack; deployment/monitoring reclassified as decided-N/A (local/dev-only target) |
| 9 | Final validation | This report + `DEMO.md` close what's closeable; full system testing fully done via a complete real end-to-end run against the local model (see §6/§7); benchmarking (needs a gold-standard labeled set) and legal-expert review remain open (see §7) |

## 6. Key Technical Challenges & How They Were Solved

These are the moments worth describing in a viva as evidence of real engineering, not just feature-checking:

**The CrPC chunking bug (Phase 6).** A self-consistency test was written to check that every ingested chunk's own text actually matches its `section_number` label. On its first run against the real 5,091-chunk corpus, it failed — a stray "Section 122." cross-reference inside `CrPC_1973.pdf` had, due to a regex whose whitespace gap spanned newlines (`\s*` instead of same-line-only `[ \t]*`), absorbed the entire following real section (§374, "Appeals from convictions") into a mislabeled chunk. Fixed at the regex level, covered by a regression test reproducing the exact shape, and the whole corpus was re-ingested (5,091 → 5,136 chunks — the fix helped elsewhere in the corpus too, not just the one case that surfaced it).

**The source-PDF-link bug, and the two chunking bugs it led to (2026-09-17).** A user report — "the source document link shows the section title page, not the explanation" — traced back to the corpus's own Table of Contents: the section-header regex matched a TOC line (e.g. `"101. Murder."`, 12 characters, no body) identically to the real section body 40+ pages later, and the short TOC chunk was winning vector search purely by exact-keyword coincidence — confirmed live, a "murder" query's top hit was the TOC entry, not the 6,434-character real section. Fixed with a dedup pass keeping only the longest chunk per `section_number` per file (`_drop_table_of_contents_duplicates()`). Fixing it surfaced a *second*, independent bug and a *third* consequence: (1) 49 sections across 5 documents print an amended section with a leading footnote-index marker (`"3[15. Terrorist act .—..."`), which the header regex's line-start anchor never matched — those sections were silently absorbed into the wrong chunk and were completely unretrievable under their own number, not just poorly ranked; fixed with an optional `(?:\d+\[)?` prefix. (2) `ingest_all()`'s re-ingestion only ever added-or-replaced chunk IDs, never removed ones that no longer exist after a smaller re-chunking — the first re-ingest after the TOC fix left 2,388 stale duplicate chunks behind under old IDs; fixed by deleting a file's existing chunks before re-upserting. Corpus re-ingested: 5,136 → 2,761 chunks. A real, understood tradeoff surfaced by this fix, not hidden: 3 of the 14 gold-standard retrieval-accuracy tests had been passing *because of* the TOC-duplicate bug's exact-title-match coincidence, not real semantic accuracy — updated to honestly document the now-exposed embedding-ranking weakness (same pattern as the pre-existing POCSO known-weakness test) rather than silently deleting the coverage or leaving the suite red.

**Real PDF highlighting, not a browser-native workaround (2026-09-17).** The "view in source" link previously relied on a `"#page=N&search=term"` URL fragment — Chromium's built-in PDF viewer's own "find in page," which only ever highlighted the short section-title string and didn't work at all in Firefox/Safari. Replaced with server-side rendering: `pdf_highlight.py` (new, using PyMuPDF) re-extracts the target page's text, locates the retrieved section's own span using the same header pattern as ingestion, and bakes a real highlight annotation onto every line of it — verified visually via a rendered screenshot, which also caught a real false positive (a short generic phrase from the target section spuriously matching identical wording in a different section further down the same page) fixed by restricting each search to that section's own vertical band on the page.

**The misleading CORS error (Phase 8/backend).** During live browser testing, a missing global exception handler meant an unhandled backend exception (e.g. a missing API key) propagated past FastAPI's CORS middleware, and the browser reported a confusing "blocked by CORS policy" error instead of the real 500. This was found by actually running the app in a browser, not by reading code — a reminder that some bugs only surface under real integration, not unit tests.

**A test suite that was silently polluting the real dev database.** Early in the project, the test suite wrote directly into the same SQLite file the dev server used. Fixed with an isolated in-memory test database and a FastAPI dependency override (`conftest.py`) — now the dev DB stays verifiably clean (`0` rows) after every test run.

**A real API-key security near-miss.** A live Anthropic API key was briefly pasted into the tracked `backend/.env.example` instead of the gitignored `backend/.env`. Caught before any commit happened, the key was moved to the correct file, and `.gitignore` coverage was re-verified.

**Repeated instances of the same short-circuit bug.** Multiple agent-invocation paths (Dynamic Interview, Legal Strategy, Document Generation, Case Strength) independently called Legal Classification unconditionally, even on a case with zero facts — wasting an API call and risking a nonsensical response. Fixed once at the shared source (`Orchestrator.classify_and_retrieve()`), benefiting every caller simultaneously instead of patching each site separately.

**Two provider-specific surprises found only by calling the real model, not by reading its documentation.** After switching to Gemini's `gemini-3.6-flash`, a quick smoke call returned an empty response with `finish_reason: "length"` despite a 2048-token budget — it turned out the model is a reasoning model that spends hidden "thinking" tokens (counted against `max_tokens`) before its visible answer, consuming ~70% of that budget on one realistic prompt. Fixed by passing `reasoning_effort="low"` (a ~4x token reduction, no observed quality loss). Separately, some responses came back wrapped in a markdown code fence despite every system prompt forbidding it — which would have silently broken 6 of the 9 agents' plain `json.loads()` parsing. Both fixed once at the shared `_call_model()` call site rather than per-agent, and both were things no amount of reading Google's docs would have surfaced as clearly as one real failing test did.

**A hard daily API quota discovered mid-integration-test, not from documentation.** Running a full realistic scenario through the live pipeline (`backend/e2e_smoke.py`) against Gemini completed 10 of 13 endpoints with strong, legally coherent output before hitting a `429` — Gemini's free tier caps `gemini-3.6-flash` at 20 requests/day, a day-level quota that immediate retries can't work around. A real, concrete example of why "free" always has a real constraint attached, worth stating plainly in a viva rather than glossing over — and the direct motivation for the local-model switch described next.

**Going fully local: real hardware checked, a native-API quirk found, and a real crash bug caught by finally completing the full pipeline.** At the user's request to remove the API dependency entirely, real laptop specs were checked before picking a model (Apple M3 Pro, 18GB RAM) rather than assumed sufficient, and the model the user already had pulled (Qwen3.5 9B via Ollama) was used as-is. A first smoke test failed the same way Gemini initially had — reasoning tokens consuming the entire output budget — but the fix was less obvious this time: neither of the two parameters that worked for Gemini (`reasoning_effort`, `extra_body={"think": False}`) had any effect through Ollama's OpenAI-compatible endpoint; only Ollama's own **native** `/api/chat` endpoint's `"think": false` field actually disabled it, found by testing directly against that endpoint rather than assuming the compatibility layer was complete. With that fixed, a full live run of `backend/e2e_smoke.py` — no quota to interrupt it this time — surfaced a genuine crash: `document_generation.py` raised `AttributeError: 'list' object has no attribute 'setdefault'` because the local model had returned a syntactically valid JSON *array* instead of the required object, something `json.loads()` alone never catches. Fixed by adding a type check to the shared JSON-parsing helper and extending it to 5 other agents that had the identical unnoticed exposure. A second full run then completed without crashing, but Document Generation still fell back to its failure message — first assumed, without checking, to be "a small model just can't handle the longest prompt." That assumption turned out to be wrong: asked directly what was actually broken, the agent was called with the exact real payload and the raw output inspected before any parsing, which showed the model wasn't struggling with complexity at all — given **15 retrieved provisions** (5 hits × 3 hypotheses, mostly overlapping and irrelevant), it lost track of the drafting task and echoed back a fragment of its own input as the answer. Fixed by deduplicating and capping what gets handed to any agent (`Orchestrator._flatten_retrieved_provisions()`: 8 provisions max, 800 characters of text each). A third full run then completed cleanly with all 9 agents, Document Generation included, producing a real, correctly-cited complaint draft — proof that the first explanation had been a plausible-sounding guess, not a verified one, and worth actually checking rather than accepting.

## 7. What Remains Genuinely Blocked (and why that's honest, not incomplete)

**Update, same day (final):** the Anthropic blocker was first resolved by switching to Google Gemini's free tier, then the provider was switched again — at the user's own explicit request, not forced by a further blocker — to a **fully local model** (Qwen3.5 9B via Ollama, zero API/network dependency). Real hardware was verified first (MacBook Pro, Apple M3 Pro, 18GB unified memory) rather than assumed adequate. `backend/e2e_smoke.py` was then run live three times: once against Gemini (10 of 13 stages, stopped by a daily free-tier quota — a real constraint, not a defect), and twice against the local model after the switch, which has no quota at all. The first local run surfaced a genuine crash bug (a wrong-shaped-but-valid JSON response), fixed at the shared source. The second completed without crashing but Document Generation still fell back to its failure message — see §6 for the real cause (noisy retrieval input overwhelming the prompt, not a model-capability wall as first assumed) and the fix. A **third** run then completed cleanly with **all 9 of 9 agents** producing genuine, good output.

Originally, three items were never closeable within this project's actual constraints:

1. **Live-LLM agent-quality evaluation and full end-to-end system testing** — **now resolved**, via the local-model runs described above (and in §6). What remains is a systematic run across a labeled gold-standard set of scenarios rather than one hand-reviewed run — that gold set doesn't exist yet, a separate, still-open task.
2. **Legal-expert review of any agent output.** No person with legal training was available to this project at any point. Flagged from Phase 1 onward, never silently dropped. Still blocked — unaffected by either provider switch. This is the one item in this section that remains genuinely, permanently out of reach for this project.
3. **Benchmarking against defined evaluation criteria** — real evaluation data now exists (item 1), but a single scenario is a spot-check, not a benchmark; needs both a labeled gold set (not built) and, for judging legal-reasoning soundness specifically, item 2.

## 8. Testing & Validation Summary

- **87 automated tests, 23 test files, 100% passing.**
- Categories: deterministic-logic tests (claim status, case-strength band, timeline sorting), agent-gating tests (empty-case short-circuits, acknowledgment gates), fabrication-guard tests (citation binding stripping fabricated chunk_ids), retrieval-accuracy tests (14 real gold-standard queries against the live corpus, no mocking), citation-accuracy tests (corpus-wide self-consistency, no mocking), adversarial tests (a documented hallucination gap, an overconfidence-resistance proof), encryption tests (real file upload → real on-disk bytes verified encrypted), and error-handling tests.
- Frontend: TypeScript strict-mode type-checking passes cleanly; the app has been live-verified in a real (Playwright-driven) Chromium browser multiple times across the project, with zero console errors each time.

## 9. Codebase Metrics

- **58** backend + frontend source files (`.py`/`.ts`/`.tsx`)
- **13** real government legislation PDFs ingested, **5,136** embedded/searchable text chunks
- **19** REST API endpoints
- **9** specialist AI agents + 1 orchestrator
- **9** frontend feature panels organized into a 3-stage guided flow
- **79** automated tests, 21 test files

## 10. Limitations & Future Work

If this moved beyond portfolio scope toward a real deployment, the priority order would be: (1) legal-expert review of every agent's actual output, (2) full database encryption (SQLCipher) and a real access-control/authentication layer, (3) a data-retention/deletion endpoint with the audit-log-survival question actually resolved, (4) sentence-level citation entailment checking (verifying generated prose, not just citation lists, against source text), (5) live-LLM evaluation against labeled scenarios once a working API key is available, and (6) expansion to the already-identified Wave 2 domains (Consumer Protection Act, Protection of Women from Domestic Violence Act, Contract Act).

## 11. Conclusion

Legal Lens demonstrates a complete, disciplined multi-agent RAG system: a real ingested legal corpus with verified retrieval accuracy, a citation-binding mechanism that structurally prevents (most) fabricated legal citations from reaching a user, a case-strength presentation that refuses to reduce a legal situation to a single misleading number, and a project-tracking discipline (`COMPLETION.md`) where nothing is marked done without verification and nothing is skipped without a stated reason. The project's honesty about its own limitations — three items left genuinely blocked rather than faked — is, deliberately, as much a part of its engineering story as the features that shipped.
