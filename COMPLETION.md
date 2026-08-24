# COMPLETION.md — Legal Lens Project Tracker

> **Single source of truth for project progress.** This file is maintained continuously as decisions are made and work is completed.
>
> **Maintenance rules (do not violate):**
> 1. Never mark `[x]` unless the task is actually, verifiably complete.
> 2. When a task completes, flip `[ ]` → `[x]` — do not delete or rewrite history.
> 3. Add new subtasks whenever additional work is discovered; do not silently absorb scope into an existing checked item.
> 4. Do not remove incomplete tasks to "clean up" the tracker.
> 5. If a task is blocked, mark it `[ ] (BLOCKED: reason)` and state the dependency explicitly.
> 6. Keep completed tasks visible for historical tracking — this file is a log, not just a live status board.
> 7. Keep this file synchronized with `CLAUDE.md` — every `DECISION REQUIRED` resolved there should unblock/update corresponding tasks here.

**Legend:** `[ ]` not started · `[x]` complete · `[~]` in progress · `[ ] (BLOCKED: ...)` blocked

---

## Phase 0 — Project Definition

- [x] Capture initial project idea and full feature brief from user (2026-08-21).
- [x] Draft initial `CLAUDE.md` master definition document.
- [x] Draft initial `COMPLETION.md` tracker (this file).
- [x] Define problem statement — **CONFIRMED 2026-08-24: draft in `CLAUDE.md` §2 accepted as final** (pre-lawyer orientation and case preparation, not advocacy/adjudication replacement).
- [x] Define target users for v1 — **DECIDED 2026-08-21: multiple personas from day one** (citizen, law student, paralegal, lawyer power-user) (`CLAUDE.md` §3). Follow-up: persona-specific presentation layer still `DECISION REQUIRED`.
- [x] Define jurisdiction scope for v1 — **DECIDED 2026-08-21: India, including select state laws** (`CLAUDE.md` §12.1). Follow-up: which states, on what basis, still open.
- [x] Define legal domain scope for v1 — **DECIDED 2026-08-21: broad multi-domain from the start** (`CLAUDE.md` §12.1). Follow-up: which domains ship in the first working slice vs. later waves still open; now the lead item for Phase 1.
- [x] Define product boundaries / what Legal Lens explicitly will not do — **CONFIRMED 2026-08-24: draft in `CLAUDE.md` §5 accepted as final** (not a lawyer substitute, no outcome guarantees, not an autonomous filer, not a source of law itself).
- [ ] Identify legal and ethical risks specific to chosen domain(s) — **DEFERRED 2026-08-24 to Phase 1**, blocked until first-wave domains are selected there; will be enumerated per domain once that list exists rather than drafted generically now.
- [x] Determine project context — **DECIDED 2026-08-21: portfolio project** (`CLAUDE.md` §3.1). Implication: synthetic/demo case data by default, modest scale targets, compliance work demonstrates awareness rather than production certification.
- [x] Determine expected scale — **DECIDED 2026-08-21: not built for real concurrent user traffic** (portfolio project, `CLAUDE.md` §3.1).
- [x] **RISK FLAGGED — RESOLVED 2026-08-24:** chosen scope (multi-persona + broad multi-domain + India+state law) is large for a portfolio-scale project. **User signed off on narrow-first sequencing**: architecture supports multi-domain from day one, but Phase 3/4 build out one domain end-to-end before expanding to the next (`CLAUDE.md` §12.1).

## Phase 1 — Requirements and Research

- [x] Select first-wave domain for the narrow slice — **DECIDED 2026-08-24: criminal law** (BNS/BNSS/BSA + historical IPC/CrPC/Evidence Act) (`CLAUDE.md` §12.1). Chosen deliberately over the lower-risk consumer-protection recommendation; raises §12.3 (dual-code) and §18 (sensitive-domain policy) sooner.
- [x] Decide state-specific law inclusion — **DECIDED 2026-08-24: central + Karnataka** (`CLAUDE.md` §12.5), not central-only as previously recommended.
- [x] Identify specific Karnataka acts relevant to criminal law — **DONE 2026-08-24** (background research agent): Karnataka Police Act 1963, Karnataka Control of Organised Crimes Act 2000 (KCOCA), Karnataka Prevention of Dangerous Activities Act 1985 ("Goonda Act"), Karnataka Police Complaints Authority rules (`CLAUDE.md` §12.1 tier 3). No Karnataka-specific textual amendments to CrPC/BNSS itself were found — flagged, not assumed absent.
- [x] Research candidate legal data sources (India Code, e-Gazette, Indian Kanoon, licensed databases, etc.) — **DONE 2026-08-24**: compared India Code, e-Gazette, Karnataka DPAL, Indian Kanoon, SCC/Manupatra on authority, licensing, format, and coverage (`CLAUDE.md` §12.2).
- [x] Decide final source hierarchy (which source wins on conflict) — **DECIDED 2026-08-24**: e-Gazette > India Code > Karnataka DPAL > Indian Kanoon (paid API); SCC/Manupatra excluded (`CLAUDE.md` §12.2).
- [x] Decide document acquisition method — **DECIDED 2026-08-24: manual human download** into a project folder, not scraping/bulk API pulls — sidesteps the unverified robots.txt/ToS status of India Code and Karnataka DPAL rather than resolving it outright (`CLAUDE.md` §12.2).
  - [x] Compile the concrete v1 criminal-law document download list — **DONE 2026-08-24**: `data/raw/criminal-law/MANIFEST.md`, with a tiered folder structure to drop downloaded files into. Tiers 4–5 intentionally left unpopulated pending open questions above.
- [ ] Verify authoritative status and licensing terms of each candidate source — partially done (Indian Kanoon's paid-API requirement confirmed); India Code / Karnataka DPAL robots.txt/ToS still unconfirmed, deliberately not blocking given the manual-download decision above.
- [x] Identify required legal documents for criminal-law narrow slice — **DECIDED 2026-08-24, revised same day: 3-tier hierarchy** for v1 (`CLAUDE.md` §12.1): (1) core legislation (BNS/BNSS/BSA + historical IPC/CrPC/Evidence Act), (2) central special laws (POCSO, NDPS, UAPA, IT Act), (3) Karnataka state acts (list above). Originally proposed as 5 tiers; tiers 4 (judicial precedents) and 5 (police manuals) were researched and then explicitly descoped — see below.
  - [ ] Confirm which additional acts (Contract Act, Consumer Protection Act, PWDVA, etc.) are in scope for *later* domain waves outside criminal law (not this narrow slice).
  - [x] Research sourcing for tier 2 (POCSO/NDPS/UAPA/IT Act) — **DONE**: same source as tier 1 (India Code), these are also central acts.
  - [x] Research sourcing for tier 5 (state police manuals/standing orders) — **DONE 2026-08-24**: no public downloadable source found (historical 1965/1973 manual is archival/physical only; ksp.karnataka.gov.in has circulars and an RTI-disclosure manual, not an operational manual). **Tier 5 descoped for v1.**
- [x] Define case-law/precedent source strategy — **RE-CONFIRMED DEFERRED 2026-08-24**: briefly reversed into v1 scope as tier 4 (`CLAUDE.md` §13.2, §12.1), then researched and **descoped**: no true citator (overruled/distinguished/followed tracking) exists at portfolio-project cost — Indian Kanoon's API exposes only raw cite/cited-by counts; real citators are SCC Online/Manupatra-subscription-tier only. Precedent retrieval stays deferred per the original 2026-08-21 decision.
  - [x] Resolve the `OPEN QUESTION`: is a maintained citator-like data source available/licensable for Indian case law? — **RESOLVED 2026-08-24: no**, not at accessible cost. See above.
- [ ] Study licensing and usage restrictions for all chosen sources — Indian Kanoon paid-API terms confirmed; others still pending (see verification item above).
- [x] Define update/amendment-tracking strategy — **DECIDED 2026-08-24: automated periodic re-check** (`CLAUDE.md` §12.4), overriding the doc's own manual-review-gated recommendation. Risk flagged, not resolved: silent auto-ingestion of a misread amendment. Follow-up `DECISION REQUIRED` at Phase 2: full auto-apply vs. automated-detection-with-human-gated-application.
- [x] Define effective-date / repealed-law modeling approach — **CONFIRMED 2026-08-24 as a firm requirement** (was `ASSUMPTION TO VALIDATE`, `CLAUDE.md` §12.3): every provision gets `effective_from`/`effective_to`/`repealed_by` plus successor/predecessor pointer. Concrete schema is Phase 2 work.
- [ ] Enumerate legal and ethical risks specific to criminal law as a domain (carried over from Phase 0, now unblocked) — e.g., risk of the system being read as predicting criminal liability, mandatory-reporting-adjacent content (POCSO, domestic violence intersecting with criminal law), risk of misuse for harassment/false-complaint drafting.
- [ ] Research practice-of-law / regulatory constraints relevant to the product's jurisdiction(s) (`CLAUDE.md` §5) — priority on criminal-law-specific constraints given domain choice.
- [ ] Research privacy/data-protection requirements applicable to the product's target region(s) (`CLAUDE.md` §18) — priority on sensitive-category handling given criminal-law domain.

## Phase 2 — System Design

- [x] Finalize multi-agent architecture and orchestration pattern (`CLAUDE.md` §8).
  - [x] Decide orchestrator implementation approach — **DECIDED 2026-08-24: hand-coded state machine** (`CLAUDE.md` §8.1).
  - [ ] Define per-agent input/output contracts (Fact Extraction, Legal Classification, Law Retrieval, Legal Strategy, Devil's Advocate, Document Generation) — still needed as concrete schemas, beyond §8.2–8.7's conceptual descriptions.
  - [ ] Define inter-agent conflict-resolution rules — deferred until Devil's Advocate is actually implemented (`CLAUDE.md` §8.8).
  - [x] Define synchronous vs. asynchronous agent invocation model — **DECIDED 2026-08-24: synchronous per user turn** (`CLAUDE.md` §8.8).
  - [x] Agent communication model — **DECIDED 2026-08-24: shared structured Case Builder state**, not message-passing (`CLAUDE.md` §8.8).
- [ ] Design RAG architecture in detail (`CLAUDE.md` §12.6).
  - [ ] Define chunking strategy respecting statutory section boundaries.
  - [ ] Define metadata schema (act, section, jurisdiction, effective dates, provenance, version/checksum).
  - [ ] Define citation-binding mechanism (generated text ↔ retrieved chunk).
  - [ ] Define retrieval-confidence / "no good match" handling.
- [ ] Design database schema for Case Builder (`CLAUDE.md` §10.2 is a conceptual sketch only — needs real schema work).
  - [ ] Decide on versioning strategy for Case Builder state (`ASSUMPTION TO VALIDATE`, `CLAUDE.md` §10.2).
- [ ] Design Evidence model and storage schema (`CLAUDE.md` §11).
  - [x] Decide scope — **DECIDED 2026-08-21: basic OCR/text extraction for text-bearing evidence**, no audio/video content analysis (`CLAUDE.md` §11.3).
  - [ ] Design OCR confidence/quality indicator and its propagation into downstream fact-verification logic.
- [ ] Design Dynamic Interview question-selection logic in detail (`CLAUDE.md` §9.2).
  - [ ] Define per-topic stopping criteria.
  - [ ] Define whole-interview stopping criteria (`OPEN QUESTION`, `CLAUDE.md` §9.2).
  - [ ] Define contradiction-detection and handling flow.
  - [ ] Define jurisdiction-detection approach (`OPEN QUESTION`, `CLAUDE.md` §9.4).
- [ ] Design security architecture (`CLAUDE.md` §18).
  - [x] Authentication approach — **DECIDED 2026-08-21: no auth required, session-only for v1** (`CLAUDE.md` §18). Follow-up open: whether any save/resume mechanism is needed for ephemeral sessions.
  - [ ] Authorization / access-control model.
  - [ ] Encryption at rest and in transit.
  - [ ] Audit logging design.
  - [ ] Data retention & deletion policy.
  - [ ] Sensitive-domain handling policy (mandatory-reporting-adjacent content, minor-safety content) (`DECISION REQUIRED`, `CLAUDE.md` §18).
- [x] Choose technology stack — **DECIDED 2026-08-24** (`CLAUDE.md` §19), proposed by the assistant under explicit user authorization to pick unilaterally where reasonable:
  - [x] LLM provider — **Anthropic Claude API**, one model family across all agents for v1.
  - [x] Vector database — **ChromaDB (embedded)**.
  - [x] Knowledge graph layer — **not included for v1**; revisit only if the relational model proves inadequate.
  - [x] Primary datastore — **SQLite**.
  - [x] Evidence/file storage — **local filesystem**, under the repo's data directory. Encryption-at-rest NOT implemented in initial scaffold — real gap, tracked in Phase 7.
  - [x] Backend framework — **Python + FastAPI**.
  - [x] Frontend framework — **React + Vite + TypeScript**.
  - [x] Deployment target — **local/dev only**.
  - [x] API design — **REST**.

## Phase 3 — Data and Knowledge Base

- [ ] Acquire legal documents per finalized scope — **BLOCKED, in progress**: `MANIFEST.md` exists, downloads not yet placed in `data/raw/criminal-law/`. Everything below is blocked on this.
- [ ] Validate documents against authoritative source.
- [~] Extract text — **first pass 2026-08-24**: `backend/app/ingestion.py` handles PDF (`pypdf`) and plain text. Not yet structure-aware in the sense §12.6 means (preserving nested sub-section structure); it's a flat text extraction feeding a naive chunker.
- [ ] Clean documents.
- [~] Chunk documents — **naive first pass 2026-08-24**: regex split on `Section N.` / `N.` patterns. **Not** the real requirement (chunk boundaries must respect actual legal document structure) — will mis-split any document that doesn't follow this exact convention. Needs real work once real documents are available to test against.
- [~] Generate metadata — **first pass 2026-08-24**: act name (from filename), tier, jurisdiction, source file. Missing: section number (chunker doesn't extract it as a field yet), effective dates, provenance (retrieval date, checksum) per `CLAUDE.md` §12.2/§12.3's requirements.
- [x] Build embeddings — ChromaDB's default embedding function, wired via `backend/app/vector_store.py`.
- [~] Build retrieval system — **first pass 2026-08-24**: `LawRetrievalAgent` queries ChromaDB directly, never falls back to model knowledge. Verified to correctly return empty/`insufficient_data` against the current empty corpus.
- [ ] Implement source citation binding — not meaningful yet without section-number metadata (see above).
- [ ] Implement update/re-ingestion mechanism per finalized strategy (`CLAUDE.md` §12.4: automated periodic re-check) — not built; `ingest_all()` currently upserts by filename-derived ID, so re-running it does overwrite stale chunks for a re-downloaded file, but there's no scheduled job or change-detection yet.
- [ ] Build gold-standard evaluation set (scenario → correct-provision mappings) for retrieval testing.

## Phase 4 — Core Intelligence

- [~] Fact Extraction agent implementation — **first pass 2026-08-24**: `backend/app/agents/fact_extraction.py`, single Claude API call producing structured JSON, wired through the orchestrator into the Case Builder. Not yet evaluated against labeled scenarios (Phase 6); no retry/repair logic if the model returns malformed JSON.
  - [x] Entity extraction (people, orgs, locations, dates, events, relationships) — basic version implemented, unevaluated.
  - [x] Fact/assumption/opinion/allegation/unknown tagging — implemented, unevaluated.
  - [ ] Timeline construction — events are persisted individually; no ordering/timeline view built yet.
- [~] Legal Classification agent implementation — **first pass 2026-08-24**: `backend/app/agents/legal_classification.py`. Deliberately does not cite section numbers (that's Law Retrieval's job, not this agent's) — only proposes candidate categories with rationale/confidence. Unevaluated against labeled scenarios.
  - [x] Multi-hypothesis classification with rationale — implemented, unevaluated.
- [ ] Dynamic Interview implementation.
  - [ ] Question generation.
  - [ ] Sufficiency/stopping logic.
  - [ ] Contradiction flagging.
- [ ] Evidence analysis implementation (metadata logging at minimum; content analysis if in scope).
- [ ] Evidence Gap Analysis implementation.
- [~] Law Retrieval agent implementation — **first pass 2026-08-24**: `backend/app/agents/law_retrieval.py` + `backend/app/vector_store.py`. Queries ChromaDB directly (no LLM call for retrieval itself, per §8.4's hard requirement against fabricated citations); returns `insufficient_data: true` and an explanatory note when nothing is ingested — verified this is exactly what happens right now, since **no documents have been ingested yet** (`data/raw/criminal-law/` only has `MANIFEST.md`, no downloaded files). Citation-binding and confidence handling not yet meaningful with an empty corpus — blocked on ingestion, which is blocked on manual downloads.
  - [x] Phase 3 ingestion pipeline first pass — `backend/app/ingestion.py`: PDF/text extraction (`pypdf`), naive regex section-chunking (**not** the structure-aware chunker §12.6 actually calls for — flagged as a known gap, not a finished implementation), metadata tagging (act name, tier, jurisdiction, source file), embedding into ChromaDB. Ready to run (`python -m app.ingestion`) the moment files land in `data/raw/criminal-law/`; ingests 0 chunks today by design, verified via smoke test.
- [ ] Similar case / precedent retrieval — **DEFERRED (2026-08-21), re-confirmed 2026-08-24 after research**: briefly considered for the criminal-law slice as document-hierarchy tier 4, then descoped once Phase 1 research confirmed no viable citator source exists (`CLAUDE.md` §13.2). Stays deferred to a later phase.
- [ ] Counterargument (Devil's Advocate) agent implementation.
- [ ] Case Strength analysis implementation.
  - [ ] Multi-dimensional, non-scored presentation logic (`CLAUDE.md` §15).
  - [ ] Decide/implement whether any coarse aggregate indicator is shown (`OPEN QUESTION`, `CLAUDE.md` §15.2).

## Phase 5 — Case Building and Documents

- [~] Case Builder core implementation — **first pass 2026-08-24**: `backend/app/models.py` implements Case/Party/Event/Statement/Claim/Evidence/DocumentDraft per §10.2's sketch. **No versioning implemented** — §10.2's `ASSUMPTION TO VALIDATE` (should case state be versioned per material change) is still unresolved; current implementation overwrites in place. `DECISION REQUIRED` before this is treated as done.
- [ ] Timeline generation and display.
- [ ] Evidence organization UI/logic.
- [ ] Question preparation feature implementation (`CLAUDE.md` §14).
- [ ] Response preparation feature implementation (strictly fact-grounded).
- [ ] Complaint/document generation agent implementation.
- [ ] Additional document templates (legal notice, case summary, chronology, evidence list, statement) — scope TBD per Phase 0.
- [ ] AI-draft labeling / professional-review-required watermarking on all generated documents.

## Phase 6 — Evaluation and Testing

- [ ] Retrieval evaluation against gold-standard set.
- [ ] Citation accuracy testing (automated check: cited text actually matches source).
- [ ] Legal provision accuracy spot-checks.
- [ ] Hallucination adversarial testing.
- [ ] Adversarial testing (attempts to induce overconfident/unsupported claims).
- [ ] Agent-level evaluation (each agent tested against labeled scenarios).
- [ ] End-to-end case simulations (synthetic/anonymized scenarios).
- [ ] Legal-expert review of outputs (BLOCKED: pending confirmation this resource is available — `CLAUDE.md` §20 open question).

## Phase 7 — Security, Privacy, and Compliance

- [ ] Authentication implementation.
- [ ] Authorization implementation.
- [ ] Data encryption (at rest, in transit).
- [ ] Secure evidence storage implementation.
- [ ] Privacy policy drafted (requires legal input — flagged, not assumed to be AI-authored final policy).
- [ ] Audit logging implementation.
- [ ] Data retention strategy implementation.
- [ ] Sensitive-domain safeguards implementation (per Phase 2 policy decision).

## Phase 8 — UI and Deployment

- [ ] User flows designed (interview flow, case dashboard, document review flow) — not designed yet; current UI is a minimal scaffold, not a designed flow.
- [~] Frontend implementation — **scaffolded 2026-08-24**: `frontend/` (React + Vite + TS), minimal case-intake form + fact-extraction result display, persistent AI-draft disclaimer. Type-checks and builds clean. No design pass, no other Case Builder views yet.
- [~] Backend implementation — **scaffolded 2026-08-24**: `backend/` (FastAPI), running and tested (`pytest` passes, live health-check + case-creation verified). Only the fact-extraction path is wired; most agents and endpoints from Phase 4/5 are not implemented yet.
- [~] API design and implementation — **REST endpoints scaffolded**: `GET /health`, `POST /cases`, `POST /cases/{id}/narrative`. No auth (per §18 decision), no versioning, no error-response schema yet beyond ad hoc `{"error": ...}`.
- [ ] Deployment setup (per chosen target).
- [ ] Monitoring setup.
- [ ] Logging setup.
- [ ] Error handling and graceful-degradation behavior (especially for retrieval-uncertain / low-confidence states).

## Phase 9 — Final Validation

- [ ] Full system testing.
- [ ] Benchmarking against defined evaluation criteria (Phase 6 outputs).
- [ ] Legal expert review (BLOCKED: same dependency as Phase 6 item).
- [ ] Documentation finalized.
- [ ] Final demo prepared.
- [ ] Project report / retrospective written.

---

## Open Items Requiring User Input (live list — mirrors tags in `CLAUDE.md`)

This section tracks every unresolved `DECISION REQUIRED` / `OPEN QUESTION` / `ASSUMPTION TO VALIDATE` currently blocking downstream phases. Updated as the discovery interview proceeds.

1. ~~Primary target persona for v1~~ — DECIDED: multi-persona (`CLAUDE.md` §3). Follow-up open: persona-specific presentation layer design.
2. ~~Jurisdiction scope for v1~~ — DECIDED: India + select state laws (`CLAUDE.md` §12.1). Follow-up open: which states, selection basis.
3. ~~Legal domain scope for v1~~ — DECIDED: broad multi-domain (`CLAUDE.md` §12.1). Follow-up open: first-wave domain list (now the lead Phase 1 item).
4. ~~Project context~~ — DECIDED: portfolio project (`CLAUDE.md` §3.1, §19).
19. ~~Scope-sequencing sign-off~~ — DECIDED 2026-08-24: narrow-first ingestion confirmed by user (`CLAUDE.md` §12.1).
20. ~~Product boundaries draft~~ — CONFIRMED 2026-08-24 as final (`CLAUDE.md` §5).
21. ~~First-wave domain~~ — DECIDED 2026-08-24: criminal law (`CLAUDE.md` §12.1). Follow-up open: expansion order after criminal law.
22. ~~State-law inclusion~~ — DECIDED 2026-08-24: central + Karnataka (`CLAUDE.md` §12.5). Follow-up open: which specific Karnataka acts.
5. Orchestration pattern for multi-agent system (`CLAUDE.md` §8).
6. ~~Automation level for Legal Strategy agent~~ — DECIDED: ranks options + suggests best path, non-binding (`CLAUDE.md` §8.5). Follow-up open: gate ranked recommendations behind explicit user acknowledgment? (recommended yes, unconfirmed).
7. ~~Case-law/precedent feature~~ — DECIDED: deferred to later phase (`CLAUDE.md` §13.2). Briefly reopened 2026-08-24, then re-confirmed deferred same day after research showed no viable citator source.
8. ~~Evidence handling depth~~ — DECIDED: basic OCR/text extraction, no audio/video analysis (`CLAUDE.md` §11.3).
9. Case strength presentation: fully disaggregated vs. some coarse aggregate indicator (`CLAUDE.md` §15.2).
10. ~~State-specific law inclusion~~ — DECIDED: central + Karnataka (`CLAUDE.md` §12.5); see item 22.
11. ~~Amendment/update process for the knowledge base~~ — DECIDED 2026-08-24: automated periodic re-check (`CLAUDE.md` §12.4). Follow-up open: full auto-apply vs. detection-only with human-gated application (Phase 2).
12. ~~Authoritative source selection for statutory text~~ — DECIDED 2026-08-24: e-Gazette > India Code > Karnataka DPAL > Indian Kanoon (paid API) (`CLAUDE.md` §12.2).
13. ~~Multi-language support requirement~~ — DECIDED: English only for v1 (`CLAUDE.md` §23).
14. ~~Authentication requirement~~ — DECIDED: no auth, session-only (`CLAUDE.md` §18). Data-retention policy for session data still open.
15. Sensitive-domain (mandatory-reporting-adjacent, minor-safety) handling policy (`CLAUDE.md` §18).
16. Technology stack — LLM approach (API-based) and language/framework sequencing decided; specific vector DB, datastore, backend/frontend framework, and deployment target still open, to be proposed at Phase 2 (`CLAUDE.md` §19).
17. Whether a lawyer-review handoff/marketplace is ever in scope (`CLAUDE.md` §22).
18. Legal-expert review availability for evaluation (`CLAUDE.md` §20).
23. ~~Citator-like data source availability/licensing~~ — RESOLVED 2026-08-24: not available at portfolio-project cost; precedent retrieval (tier 4) descoped as a result (`CLAUDE.md` §13.2).
24. ~~Sourcing for criminal-law document tier 2 and tier 5~~ — RESOLVED 2026-08-24: tier 2 (POCSO/NDPS/UAPA/IT Act) sources from India Code same as tier 1; tier 5 (police manuals) has no public source and is descoped (`CLAUDE.md` §12.1).

---

## Change Log

- **2026-08-21** — Tracker created alongside initial `CLAUDE.md` draft. Phase 0's first three items marked complete (idea captured, initial docs drafted). All other items pending discovery interview.
- **2026-08-21** — Discovery round 1: decided target users (multi-persona), jurisdiction (India + select states), domain scope (broad multi-domain), project context (portfolio). Scope risk flagged pending sequencing sign-off.
- **2026-08-21** — Discovery round 2: decided Legal Strategy agent automation level (ranked + suggested path), evidence handling depth (OCR/text extraction), case-law/precedent deferred to later phase.
- **2026-08-21** — Discovery round 3: decided LLM approach (API-based hosted), stack selection deferred to Phase 2 design, authentication (none, session-only for v1), language support (English only for v1).
- **2026-08-24** — Phase 0 closed out: problem statement (§2) and product boundaries (§5) confirmed as drafted; scope-sequencing risk resolved (user signed off on narrow-first ingestion, `CLAUDE.md` §12.1); per-domain legal/ethical risk enumeration deferred to Phase 1 pending first-wave domain selection. **Phase 0 complete.** Starting Phase 1.
- **2026-08-24** — Phase 1 discovery round 1: first-wave domain decided as criminal law (BNS/BNSS/BSA + historical IPC/CrPC/Evidence Act); state-law scope decided as central + Karnataka (not central-only). Required-documents sub-items resolved as a consequence. Domain risk enumeration (carried from Phase 0) now unblocked and added as a Phase 1 task.
- **2026-08-24** — Phase 1 research round 1: background agent identified 4 Karnataka criminal-law acts and compared candidate data sources. User then locked in the full v1 criminal-law document hierarchy (5 tiers, including central special laws and police manuals beyond the original core-codes scope) and **reversed the 2026-08-21 case-law/precedent deferral for criminal law specifically**. Source hierarchy and manual-download acquisition method decided. Tiers 2 (special laws) and 5 (police manuals) still need dedicated source research.
- **2026-08-24** — Phase 1 research round 2: background agent investigated citator availability (tier 4) and police-manual sourcing (tier 5). Neither is viable at portfolio-project scope — no citator exists below SCC Online/Manupatra subscription cost, and no public source for a Karnataka Police Manual/Standing Orders was found. User **descoped both tiers**; the 2026-08-21 precedent-retrieval deferral is back in force. Criminal-law v1 document scope is now a **3-tier** hierarchy (core legislation, central special laws, Karnataka state laws). `MANIFEST.md` updated accordingly.
- **2026-08-24** — Phase 1 discovery round 2: effective-date/successor-pointer data model confirmed as firm requirement (`CLAUDE.md` §12.3). Amendment-tracking strategy decided as automated periodic re-check (`CLAUDE.md` §12.4) — a deliberate departure from the doc's own manual-review-gated recommendation; risk flagged for Phase 2 to resolve (full auto-apply vs. detection-only). User began downloading Tier 1–3 documents per `MANIFEST.md` in parallel.
- **2026-08-24** — User directed a jump to code scaffolding. Remaining Phase 1 practice-of-law/privacy research items deferred (not dropped); domain risk enumeration explicitly skipped. Phase 2 orchestration pattern, agent communication model, and full tech stack decided in one pass to unblock scaffolding (see `CLAUDE.md` §8.1, §8.8, §19 and Phase 2 checklist above). **Phase 2's foundational decisions are complete; detailed design work (per-agent contracts, RAG chunking specifics, Case Builder schema, security architecture beyond auth) remains open and will be filled in as those parts are actually built.**
- **2026-08-24** — First working slice scaffolded and verified running: `backend/` (FastAPI + SQLAlchemy/SQLite, `POST /cases`, `POST /cases/{id}/narrative` wired through a hand-coded `Orchestrator` to a `FactExtractionAgent` calling the Anthropic API), `frontend/` (React + Vite + TS, minimal case-intake UI with a persistent AI-draft disclaimer per §5/§22). Backend tests pass (`pytest`); frontend type-checks and builds; end-to-end health check and case creation verified live. Case Builder data model implemented per §10.2's conceptual sketch (Case/Party/Event/Statement/Claim/Evidence/DocumentDraft) — **without versioning**, since §10.2's versioning `ASSUMPTION TO VALIDATE` is still unresolved; tracked below as a Phase 5 gap. Git repo initialized, changes staged but not committed. Only Fact Extraction is wired up — Legal Classification, Law Retrieval, Evidence Gap Analysis, Devil's Advocate, and Document Generation agents are not yet implemented (Phase 4/5 work, not done here).
- **2026-08-24** — User flagged (correctly) that RAG retrieval can't function with no documents ingested — `data/raw/criminal-law/` only has `MANIFEST.md`, nothing downloaded yet. Confirmed and addressed: added Legal Classification agent (hypotheses only, no citations — doesn't need the corpus), a Phase 3 ingestion pipeline first pass (`app/ingestion.py`: PDF/text extraction, naive section-regex chunking — explicitly flagged as not yet the real structure-aware chunker §12.6 requires, metadata tagging, ChromaDB embedding), and a Law Retrieval agent (`app/law_retrieval.py`) that queries ChromaDB directly with zero LLM involvement in the retrieval step itself, honoring §8.4's hard requirement against fabricated citations. Verified live: with the corpus empty, ingestion returns 0 chunks and retrieval returns `[]`/`insufficient_data: true` — confirmed by direct smoke test, not assumed. Both new agents wired into the orchestrator via a new `POST /cases/{id}/classify` endpoint. Tests still pass.
