# CLAUDE.md — Legal Lens Master Project Definition

> **Status:** PLANNING PHASE. No implementation has begun. This document is the single source of truth for what Legal Lens is, why it exists, and how it should eventually be built. It is a living document — update it after every planning decision.
>
> **Tagging convention used throughout this document:**
> - `OPEN QUESTION` — something we haven't discussed yet; needs a conversation.
> - `DECISION REQUIRED` — a fork in the road has been identified; the project cannot proceed past a certain point without picking a side.
> - `ASSUMPTION TO VALIDATE` — a working assumption is in place (often to keep this document coherent) but has NOT been confirmed by the user and may be wrong.
>
> Do not treat anything tagged above as settled. Do not write code against an `OPEN QUESTION` or unvalidated `ASSUMPTION`.

---

## 1. Project Vision

Legal Lens is an AI-assisted platform that helps a person who is facing a legal situation — and who does not necessarily know any legal terminology — move from *"something happened to me and I don't know what to do"* to a structured, evidence-linked, source-cited understanding of their situation: what facts they have, what legal provisions might apply, what's missing, what the other side might argue, and what documents or next steps could help.

Legal Lens is explicitly **not** trying to be a lawyer, replace legal advice, or predict court outcomes. It is trying to be the most rigorous, traceable, well-organized **case preparation and legal orientation assistant** possible, built so that every claim it makes can be traced to a verifiable source, and every place it is uncertain is presented as uncertain.

## 2. Problem Statement

People encountering a legal problem (a dispute, a potential offence, a contract issue, a rights violation, etc.) typically face:

- Not knowing which laws or legal categories apply to their situation.
- Not knowing what facts/evidence matter and what to collect.
- Not being able to afford or access a lawyer for early-stage orientation.
- Not knowing how to structure a complaint, notice, or case file.
- Not knowing the weaknesses in their own case, or what the other side might argue.
- Difficulty finding relevant statutory provisions or precedents in dense legal text.

Legal Lens addresses the **orientation and preparation** gap — not the advocacy or adjudication gap.

`ASSUMPTION TO VALIDATE`: The core problem being solved is *pre-lawyer orientation and case preparation*, not *replacing* a lawyer at any stage. This acts like an assistant to lawyers/paralegals/normal humans. This shapes almost every downstream design decision (disclaimers, automation limits, human-in-the-loop requirements). Confirm this framing with the user.

## 3. Target Users

**DECISION (2026-08-21):** v1 targets multiple personas from day one:

- **Persona A — Ordinary citizen / self-represented individual.** No legal knowledge. Needs plain-language interview, heavy hand-holding, strong disclaimers, cannot be expected to validate legal citations themselves.
- **Persona B — Law student.** Learning-oriented. Wants to see reasoning, citations, counterarguments, and the "why" behind classifications. More tolerant of imperfect UX, more capable of catching errors.
- **Persona C — Paralegal / junior associate / lawyer's assistant.** Uses the tool to accelerate case-file preparation, evidence organization, and first-draft documents under supervision of a licensed lawyer. Highest tolerance for structured/technical UI, lowest tolerance for hallucination since output feeds real practice.
- **Persona D — Practicing lawyer (power user).** Wants speed: fast retrieval, precedent search, draft generation, case-strength summarization for cases they already understand.

`DECISION REQUIRED`: Multi-persona v1 means the same underlying case data and outputs must be presentable at different levels of plain-language vs. technical density. This needs a UI/content-layer decision: a single adaptive presentation, or persona-specific views over the same Case Builder state. Not yet designed.

`ASSUMPTION TO VALIDATE`: Given this is a **portfolio project** (see §3.1 below), true simultaneous multi-persona support across the full feature set is a large surface area. Recommend the *architecture* support multiple personas (data model, agent outputs are persona-agnostic and structured), while the first working vertical slice demonstrates one persona's full flow end-to-end before building out the others — otherwise nothing reaches "done." This needs explicit confirmation from the user before Phase 4 begins.

### 3.1 Project Context

**DECISION (2026-08-21):** This is a **portfolio project** — built to demonstrate depth of thinking, system design quality, and technical execution, not to serve real production users or real legal matters. This has significant implications, flagged here so they aren't silently lost:

- Real users' real legal situations should **not** be processed by this system unless/until privacy, security, and legal-risk work (§18, §5) is substantially further along than a portfolio timeline typically allows. Demo/synthetic case data should be the default assumption for development and demonstration.
- Compliance rigor (data protection law, unauthorized-practice-of-law rules) matters for *demonstrating awareness* of these constraints in the design, but does not need to be operationalized to production-grade certification for a portfolio artifact.
- Scale/availability targets (§7) can stay modest — this is not being built for concurrent real traffic.
- **Scope risk flagged explicitly:** the combination chosen — multi-persona, broad multi-domain, India + state laws — is a large scope for a project not backed by a team or production timeline. See §12.1 for the corresponding recommendation to sequence breadth *after* a working narrow slice, and `COMPLETION.md`'s Open Items list for the tracked risk.

## 4. Core Use Cases

1. A user describes a situation in plain language; the system conducts a dynamic interview to fill gaps.
2. The system builds a structured Case file: facts, parties, timeline, claims, evidence, applicable law.
3. The system retrieves and cites relevant statutory provisions with source traceability.
4. The system identifies evidence gaps and asks the user to address them.
5. The system generates counterarguments / weaknesses ("devil's advocate" pass).
6. The system helps prepare draft documents (complaint, notice, chronology, evidence list) marked clearly as AI-assisted drafts requiring professional review.
7. The system helps prepare for likely questioning (from opposing side, court, or investigators) strictly from known facts.
8. The system presents case strength as a structured, multi-dimensional assessment (not a single win-probability number) — coverage, uncertainty, contradictions, counterarguments.
9. (Optional/late-phase) The system surfaces similar precedents/case law with explicit reliability caveats.

## 5. Product Boundaries — What Legal Lens Is NOT

These boundaries are foundational, not incidental, given the legal-risk profile of this product:

- **Not a substitute for a licensed lawyer.** It does not give "legal advice" in the professional-responsibility sense; it gives structured legal *information* and *organization*.
- **Not a guarantee of outcome.** No win-probability numbers without a rigorously defensible methodology (none currently exists for this domain at this fidelity — see §16).
- **Not an autonomous filer.** It does not submit documents to courts/authorities on a user's behalf (at least not in any near-term version).
- **Not a source of law itself.** Every legal claim must cite a retrieved, verifiable source — the model's own "knowledge" is never treated as authoritative for statutory content.

`DECISION REQUIRED`: Jurisdictional practice-of-law regulations (e.g., unauthorized practice of law rules) may constrain what the product can legally do/say in a given market. This needs explicit legal review before any public launch — flagged here as a hard product-boundary risk, not just a UX concern.

## 6. Functional Requirements Overview

Grouped by the 7 core functionalities from the original brief. Each is expanded in its own section later in this document.

| # | Functionality | Section |
|---|---|---|
| 1 | Dynamic Legal Interview System | §8 |
| 2 | Case Builder | §9 |
| 3 | Evidence Management & Gap Analysis | §10 |
| 4 | Legal Knowledge & RAG System | §11–12 |
| 5 | Previous Case / Precedent Reference | §13 |
| 6 | Question & Answer Preparation | §14 |
| 7 | Case Strength Analysis | §15 |

Plus supporting system: Multi-agent architecture (§7), Document Generation (see §9.6), Explainability/Hallucination Prevention (§16), Jurisdiction & Temporal Validity (§17), Privacy/Security (§18), Architecture & Tech (§19).

## 7. Non-Functional Requirements

- **Traceability:** Every legal-provision claim must be linkable to an ingested source document + version + effective-date window.
- **Explainability:** Every classification, recommendation, or generated argument must be inspectable — "why did the system say this."
- **Safety over completeness:** The system must prefer saying "uncertain / insufficient information" over fabricating a confident-sounding but unsupported answer.
- **Auditability:** All interview exchanges, retrieved sources, and generated outputs relevant to a case must be logged for later review (by the user, and potentially a supervising lawyer).
- **Privacy:** Legal situations are highly sensitive (domestic violence, criminal allegations, financial disputes). Data handling must assume worst-case sensitivity by default.
- **Availability / latency:** `OPEN QUESTION` — no target SLAs defined yet; depends on whether this is a live product or a research/portfolio project (see §21 discovery topic).
- **Correctness over speed:** Multi-agent pipelines (interview, retrieval, drafting) should be allowed to take longer if it materially improves citation accuracy.

## 8. Multi-Agent Architecture

`ASSUMPTION TO VALIDATE`: The system uses an **orchestrator + specialist agents** pattern (a central controller sequences/coordinates the specialist agents below) rather than fully autonomous peer-to-peer agent communication. This is the safer, more debuggable default for a legal-risk product, but must be confirmed with the user, who may prefer a different topology (e.g., a simpler single-agent-with-tools design for MVP, deferring "multi-agent" complexity).

### 8.1 Orchestrator (implicit in the brief, not named as an agent but required)

- Owns the Case Builder state.
- Decides which specialist agent(s) to invoke at each step of the interview/case-building process.
- Resolves conflicting outputs between agents (e.g., Legal Classification suggests category A, Devil's Advocate flags contradiction).
- Enforces the "never present unsupported legal claims" invariant across all agent outputs before they reach the user.

**DECISION (2026-08-24):** Hand-coded state machine, not an LLM-driven planner — the safer, more testable default for a legal-risk product, as originally recommended.

### 8.2 Fact Extraction Agent

- **Input:** Raw user narrative (text, possibly multi-turn), interview answers.
- **Output:** Structured entities (people, orgs, locations, dates, events, actions, relationships) + explicit tagging of each statement as `fact` / `assumption` / `opinion` / `allegation` / `unknown`. Timeline draft.
- **Failure modes to design against:** merging distinct people/events, mis-tagging opinion as fact, silently dropping ambiguous statements instead of flagging them.

### 8.3 Legal Classification Agent

- **Input:** Structured facts from Fact Extraction, jurisdiction context.
- **Output:** Ranked list of *possible* legal categories/offences/disputes/remedies — explicitly multiple hypotheses, not a single verdict. Confidence/rationale per hypothesis.
- **Failure modes:** premature narrowing to one legal theory; ignoring plausible alternative characterizations; jurisdiction mismatch.

### 8.4 Law Retrieval Agent

- **Input:** Legal classification hypotheses + facts.
- **Output:** Retrieved statutory provisions/sections/rules with source metadata (document, version, effective date, section number) — see RAG architecture §12.
- **Hard requirement:** No provision is surfaced without a retrieval hit against the verified knowledge base. The agent must not "recall" a section number from model parametric knowledge.

### 8.5 Legal Strategy Agent

- **Input:** Facts, legal classifications, retrieved provisions, evidence status.
- **Output:** **DECISION (2026-08-21):** Ranks possible approaches/remedies/procedural options and surfaces a suggested best path — going beyond a flat options-list, while the suggestion must remain explicitly non-binding (framed as "based on currently known facts, X appears strongest, because..." rather than "you should do X").
- **Product-boundary consequence:** Because this agent actively ranks and recommends, it carries meaningfully more legal-risk/product-boundary exposure than a pure options-lister (see §5). This raises the bar on:
  - Disclaimer strength and placement (must be adjacent to every ranked recommendation, not just a global footer).
  - Traceability: the ranking rationale must cite the specific facts/evidence/provisions driving it (§16) so the "why" is inspectable, not a black-box preference.
  - `DECISION REQUIRED`: Should ranked recommendations be gated behind an explicit user acknowledgment ("this is not legal advice, do you want to see a suggested path") before being shown? Recommend yes; not yet confirmed.

### 8.6 Devil's Advocate / Counterargument Agent

- **Input:** Full case state (facts, evidence, claims).
- **Output:** Weaknesses, missing-evidence-driven vulnerabilities, plausible opposing arguments, alternative interpretations of the same facts.
- **Design constraint:** Must operate on the same fact/evidence base as other agents — cannot invent facts to attack, only expose weaknesses in what exists or is missing.

### 8.7 Complaint / Case Document Generation Agent

- **Input:** Verified case state + retrieved legal provisions.
- **Output:** Structured drafts (complaint, legal notice, case summary, chronology, evidence list, statement, question sets). Every generated document must be watermarked/labeled as an AI-assisted draft requiring professional review before use.
- **Hard requirement:** Does not fabricate facts not present in the Case Builder; does not invent citations.

### 8.8 Agent Communication & Orchestration

**DECISION (2026-08-24):**
- Agents communicate via **shared structured Case Builder state**, not message-passing/conversation — auditable, avoids uncontrolled inter-agent chat.
- Agent invocation is **synchronous per user turn** for v1 (no background/async agent runs yet — e.g., Evidence Gap Analysis re-runs when triggered by the orchestrator after a relevant state change, not on an independent background loop).
- `OPEN QUESTION` still unresolved: what happens when two agents disagree (e.g., Legal Classification vs. Devil's Advocate)? Deferred to when Devil's Advocate is actually implemented (Phase 4) rather than decided abstractly now.

## 9. Dynamic Legal Interview System

### 9.1 Design Goals
- Ask only legally material questions — no interrogation for its own sake.
- Adapt based on: problem type, facts already known, jurisdiction, current legal-classification hypotheses, missing evidence, and detected contradictions.
- Maintain a structured, appendable record of every answer (feeds directly into Case Builder).

### 9.2 Question Selection Logic (conceptual, not implementation)
For each turn:
1. Compute current "information state" (what's known/unknown/contradictory) from Case Builder.
2. Ask Legal Classification Agent: given current facts, what additional facts would most change or confirm the hypothesis set?
3. Rank candidate questions by expected information gain / legal materiality.
4. Select next question(s); avoid re-asking already-answered material.
5. Determine sufficiency: stop interviewing a topic when marginal value of more questions is low, OR user signals they don't know / can't provide more.

`OPEN QUESTION`: What is the stopping criterion for the *entire* interview (not just one topic)? Fixed question budget? Confidence threshold on classification? User-initiated "I think that's everything"?

### 9.3 Contradiction Handling
- If a new answer contradicts an earlier one, the system must flag it explicitly (not silently overwrite), tag both statements, and may ask a clarifying question.
- Contradictions become part of the Case Builder's "disputed facts" set (see §10) and are visible to the Devil's Advocate Agent.

### 9.4 Jurisdiction Detection
`OPEN QUESTION`: How is jurisdiction determined — explicit user input, inferred from location facts, or both? What happens with cross-jurisdiction facts (e.g., online contract between parties in different states/countries)?

## 10. Case Builder

### 10.1 Purpose
The single structured, evolving representation of the user's legal situation. All agents read from and write to it (via the orchestrator). It is the artifact that gets exported into documents, shown to the user, and (eventually) reviewed by a human lawyer.

### 10.2 Conceptual Data Model (sketch — not a DB schema; schema work is implementation phase)

- **Case** — id, status, jurisdiction, created/updated timestamps, summary.
- **Party** — id, role (user/opposing/witness/third-party/authority), name or identifier, relationship-to-user.
- **Relationship** — party ↔ party, type, description.
- **Event** — id, timestamp (or estimated/approximate), description, participants, source (user statement vs. evidence-derived), confidence.
- **Timeline** — ordered/orderable sequence of Events, with explicit handling of uncertain/approximate dates.
- **Statement** — raw text, classification (`fact`/`assumption`/`opinion`/`allegation`/`unknown`), linked Event/Party if applicable, source (interview turn reference).
- **Claim/Allegation** — id, description, asserted-by (party), supporting Statements, supporting Evidence, status (supported/unsupported/disputed).
- **Evidence** — see §10.3 (Evidence model) below; linked to Claims and Events.
- **LegalProvision (reference)** — pointer into the RAG knowledge base (not stored duplicated), plus the reasoning link explaining *why* it was retrieved for this case.
- **LegalAction/Remedy (candidate)** — id, description, supporting provisions, procedural notes, status (candidate/discussed/rejected).
- **Counterargument** — id, description, target Claim(s), source (Devil's Advocate Agent), status.
- **OpenQuestion (case-level)** — things the system still needs clarified — distinct from the document-level `OPEN QUESTION` tags in this file; this is per-case runtime state.
- **DocumentDraft** — id, type (complaint/notice/summary/etc.), content, generation timestamp, source Case Builder version, review-status (AI-draft / lawyer-reviewed / finalized).

`ASSUMPTION TO VALIDATE`: Case Builder state should be **versioned** (every material change creates a new version, not an overwrite) so that "what did the system know when it generated this document" is always reconstructable. This is important for auditability but adds real implementation complexity — confirm this is wanted for MVP or deferred.

## 11. Evidence Model & Evidence Gap Analysis

### 11.1 Evidence Types (from brief)
Documents, contracts/agreements, messages, emails, images, videos, audio, witness information, financial records, other digital evidence, government documents, other.

### 11.2 Core Distinction (must be enforced everywhere in the system)
1. **Facts claimed by the user** (unverified narrative statements).
2. **Evidence provided by the user** (actual artifacts — documents, media, records).
3. **Facts independently supported by evidence** (a claim that has at least one linked, plausible piece of evidence).

These three must never be conflated in the UI, in generated documents, or in internal agent reasoning. A claim with no linked evidence stays visibly "unsupported," even if plausible.

### 11.3 Evidence Gap Analysis
For each Claim/Allegation in the Case Builder:
- Does it have linked Evidence? (yes/no/partial)
- Is the linked Evidence itself disputed or of uncertain provenance?
- What evidence *type* would typically support this kind of claim (domain-informed heuristic — e.g., a contract dispute typically benefits from the written contract, correspondence, payment records)?
- Surface this as a structured gap list, not a hidden internal score.

**DECISION (2026-08-21):** v1 includes **basic content extraction (OCR/text extraction)** for text-bearing evidence (scanned documents, images of text, PDFs, etc.) — beyond pure metadata logging, but stopping short of full media (audio/video) content analysis. Consequences to design for:
- Extracted text becomes a candidate source for fact-verification (e.g., checking if a claimed contract term is actually present in the uploaded contract) — but extracted text must be treated as *evidence content*, distinct from user-asserted facts (§11.2's three-way distinction still applies: extracted text supports evidence-backed facts, it does not become a "fact" on its own without being linked to a claim).
- OCR errors are a new failure mode: extracted text must carry a confidence/quality indicator, and low-confidence extractions should not silently feed downstream reasoning as if reliable.
- Privacy/security surface area increases (document content is processed, not just stored) — reinforces the need for encryption-at-rest and access control (§18) before any real documents are handled.
- Audio/video evidence in v1 is logged with metadata + user description only; no transcription/analysis. `OPEN QUESTION`: is basic audio transcription (not full analysis) worth adding later given how common WhatsApp/call-recording evidence is in real disputes? Parked for future expansion (§23).

## 12. Legal Knowledge Base & RAG Architecture

### 12.1 Scope Decision

**DECISION (2026-08-21):** Jurisdiction is **India, including select state laws** (not central-law-only); domain scope is **broad multi-domain from the start** (not a single narrow slice). This is a deliberate scope expansion beyond the original recommendation, made knowingly as part of a portfolio project's ambition (see §3.1).

`DECISION REQUIRED` (still open, now narrower): "Broad multi-domain" and "select state laws" still need concrete boundaries before ingestion work can start:
- Which domains, specifically, are "in" for the first working version vs. the full target set? (e.g., is criminal law in scope alongside civil/consumer/contract from the very first working slice, or added in a second wave?)
- Which states' laws, specifically, are "select" — and on what basis are they selected (most common disputes, most-populous states, arbitrary)?

**DECISION (2026-08-24):** Sequencing confirmed by user. "Broad multi-domain, India + state laws" remains the **long-term target architecture** (data model, agent outputs, and RAG pipeline are built domain-agnostic from the start), but Phase 3 (`COMPLETION.md`) ingests one domain first, end-to-end — proving out ingestion pipeline, chunking, citation-binding, and evaluation — before expanding domain-by-domain. This avoids a shallow, low-quality pass across everything at once, which would undermine the traceability/accuracy requirements that are this project's core differentiator.

**DECISION (2026-08-24):** First-wave domain is **criminal law** — Bharatiya Nyaya Sanhita (BNS) 2023 + Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 + Bharatiya Sakshya Adhiniyam (BSA) 2023, plus their historical predecessors (IPC, CrPC, Evidence Act) for pre-July-2024 events per §12.3's temporal-validity requirement. This is a deliberately higher-risk/higher-payoff choice than the originally recommended consumer-protection starting point: it directly exercises §12.3's dual-code (old law/new law) modeling problem, but also raises sensitivity earlier (§18's mandatory-reporting/minor-safety policy gap becomes relevant sooner — flagged for Phase 1's practice-of-law/privacy research tasks below). `DECISION REQUIRED` (Phase 1, remaining): domain-by-domain expansion order after criminal law.

**DECISION (2026-08-24), Tiers 4–5 descoped 2026-08-24:** The criminal-law v1 document scope is a **three-tier** hierarchy (originally proposed as five; Tiers 4 and 5 were researched and then explicitly descoped once research showed no viable source):

1. **Core legislation** — BNS (substantive), BNSS (procedural), BSA (evidence), plus historical IPC/CrPC/Evidence Act for pre-July-2024 events (§12.3).
2. **Central special laws** — POCSO, NDPS Act, UAPA, IT Act (the criminal-law-relevant provisions).
3. **State-specific laws** — Karnataka Police Act 1963, Karnataka Control of Organised Crimes Act 2000 (KCOCA), Karnataka Prevention of Dangerous Activities Act 1985 ("Goonda Act"), Karnataka Police Complaints Authority rules (§12.5).

**Descoped — Judicial precedents:** researched and rejected 2026-08-24. No true citator (overruled/distinguished/followed tracking) exists at portfolio-project cost — Indian Kanoon's API exposes only raw cite/cited-by counts; real citator products are SCC Online/Manupatra-subscription-tier only. Rather than ship an unreliable version of §13.2's status-tracking requirement, precedent retrieval stays deferred per §13.2's original 2026-08-21 decision.

**Descoped — Execution & police manuals:** researched and rejected 2026-08-24. No public downloadable source found for a Karnataka Police Manual or consolidated Standing Orders — the historical 1965/1973 manual is archival/physical only; ksp.karnataka.gov.in hosts circulars and an RTI-mandated disclosure manual, but not an operational manual. Further pursuit (a full department-wise DPAL index crawl, or an RTI request) was judged out of scope for a portfolio project.

### 12.2 Source Authority & Hierarchy

**DECISION (2026-08-24):** Source authority hierarchy for the criminal-law slice, based on Phase 1 research:

1. **e-Gazette** (egazette.gov.in) — ground truth for enacted text and effective dates; used to validate the other sources, not as the primary day-to-day working source (PDF-only, not structured by section).
2. **India Code** (indiacode.gov.in) — primary working source for tiers 1–2 (core legislation + central special laws); official Ministry of Law and Justice repository, structured by section, retains historical/repealed acts.
3. **Karnataka DPAL** (dpal.karnataka.gov.in) — primary source for tier 3 (Karnataka acts).
4. **Indian Kanoon**, via its **paid API** (not scraping — their terms discourage raw scraping) — primary source for tier 4 (judicial precedents), and secondary cross-check for tiers 1–3 when India Code text is ambiguous.
5. SCC Online / Manupatra — excluded; subscription cost not viable for a portfolio project.

**Acquisition method (DECIDED 2026-08-24):** documents are acquired by **manual human download** into a project folder, not automated scraping or bulk API pulls — this sidesteps the unverified robots.txt/ToS status of India Code and Karnataka DPAL (flagged as an open gap in Phase 1 research) without needing to resolve it. Provenance for each manually-downloaded document (source URL, retrieval date, version/edition) must still be recorded per the requirement below.

- How is source provenance stored (publisher, retrieval date, document version/edition, URL/citation, checksum)? — `OPEN QUESTION`, still needs a concrete schema (Phase 2 data-model work).
- What is the process when two sources disagree on text? — resolved by the hierarchy above (higher-ranked source wins); e-Gazette is the tiebreaker of last resort.

### 12.3 Historical / Repealed Law Handling
India recently replaced IPC/CrPC/Evidence Act with BNS/BNSS/BSA (effective July 1, 2024). This is a first-class design problem, not an edge case:
- Events that occurred **before** the transition date are generally governed by the old law (IPC/CrPC/Evidence Act) for many purposes; events after are governed by the new codes. `DECISION REQUIRED` on exactly how transitional/saving-clause rules are modeled — this is legally nuanced and should not be hardcoded as a naive date cutoff without review.
- The knowledge base must store **both** old and new provisions, each tagged with effective-date ranges, and the Law Retrieval Agent must select based on the **event date**, not the query date.
**DECISION (2026-08-24):** Confirmed as the data-model requirement (no longer just an assumption). Every ingested provision — BNS/BNSS/BSA and historical IPC/CrPC/Evidence Act alike — carries explicit `effective_from` / `effective_to` (or `repealed_by`) fields, plus a pointer to its successor/predecessor provision where applicable (e.g., BNS §103 ↔ IPC §302). The Law Retrieval Agent selects based on the event date, not the query date, per this schema. Schema work itself (field types, storage) is Phase 2.

### 12.4 Amendment Tracking
**DECISION (2026-08-24):** **Automated periodic re-check** — a scheduled job diffs source sites (India Code, e-Gazette, Karnataka DPAL) against the ingested corpus and flags/applies detected changes automatically. This overrides the earlier recommendation of manual-review-gated updates, which was made specifically because of this product's legal-risk profile (§7's "safety over completeness," §16's hallucination-prevention requirements). **Risk flagged, not resolved by this decision:** silent automated application of a detected "amendment" could ingest a premature, misread, or incorrectly-diffed change without human verification — directly in tension with §7's traceability/explainability requirements. `DECISION REQUIRED` (Phase 2, follow-up): at minimum, define what "applies changes automatically" means precisely — full silent ingestion, or automated *detection* with the *application* step still requiring a human trigger (a middle ground worth revisiting before Phase 3 implementation, since full silent ingestion has no verification step at all).

### 12.5 State-Specific Law
**DECISION (2026-08-24):** v1's narrow slice is **central law + Karnataka state law**, not central-law-only. `DECISION REQUIRED` (Phase 1): identify which specific Karnataka acts/amendments are relevant to the first-wave domain (criminal law — §12.1) — e.g., Karnataka Police Act, state amendments to criminal procedure, or other state-specific criminal-adjacent legislation — as part of the source-research task below. Karnataka remains the "select state" for the broader multi-domain target in §12.1 unless later revisited.

### 12.6 RAG Pipeline (conceptual, technology-agnostic — no stack chosen yet)
1. **Ingestion:** acquire source documents from decided authoritative source(s).
2. **Validation:** verify document integrity/authenticity against source (e.g., checksum, official publication reference).
3. **Text extraction & cleaning:** structure-aware extraction (preserve section/sub-section numbering — critical for legal citation accuracy, not just prose flow).
4. **Chunking:** must respect legal document structure (section/sub-section boundaries), not naive fixed-length chunking — a chunk split mid-section risks citation and retrieval accuracy failures.
5. **Metadata tagging:** act name, section number, jurisdiction, effective-date range, source provenance, version/checksum, repealed/successor links.
6. **Embedding & indexing:** technology TBD (§19).
7. **Retrieval:** must return chunk + full provenance metadata, never bare text.
8. **Citation binding:** every LLM-generated sentence that references a legal provision must be programmatically bound to a specific retrieved chunk id — not just "the model said it cited this."

### 12.7 Hallucination Prevention for Retrieval
- Retrieval alone is never treated as *proof* a legal conclusion is correct — retrieval finds candidate relevant text; an explicit verification/consistency step (rule-based or a stricter secondary check) should confirm the cited section text actually supports the generated claim before it's shown to the user. `OPEN QUESTION`: exact mechanism (e.g., quote-verification, entailment check) is implementation-phase, but the *requirement* is locked in now.
- If retrieval confidence is low or no good match is found, the system must say so explicitly rather than presenting a weak match as authoritative.

## 13. Case Law & Precedent Reference (Similar Case Finder)

### 13.1 Capabilities Envisioned
Similar factual-pattern search, similar-provision search, precedent retrieval, comparison/explanation of similarities & differences, jurisdiction/court-level relevance, and status tracking (overruled/distinguished/followed) where available.

### 13.2 Known Limitations (must be designed around, not hidden)
- AI-based "similar case" search is prone to superficial pattern-matching (same words, different legal significance) — this must be disclosed to users, not presented as legal-equivalence.
- Overruled/distinguished/followed status tracking requires a maintained citator-like data source, which is a significant undertaking (`OPEN QUESTION`: is such a data source available/licensable, or is this feature descoped for v1?).
- Precedent value varies enormously by court level and jurisdiction — a High Court judgment from a different state may have persuasive-only, not binding, value. The system must always surface court level and binding/persuasive status alongside any case reference.

**DECISION (2026-08-21), briefly reversed 2026-08-24, RE-CONFIRMED DEFERRED 2026-08-24:** Case-law/precedent retrieval is **deferred to a later phase**, not in v1 — including for the criminal-law slice. It was briefly brought into v1 scope as document-hierarchy tier 4 (§12.1), but Phase 1 research confirmed no true citator (a maintained overruled/distinguished/followed tracking source) exists at a cost/access level realistic for a portfolio project: Indian Kanoon's API exposes only raw cite/cited-by counts, not treatment classification, and real citator products (SCC Online, Manupatra) are subscription-tier-only. Rather than ship an unreliable version of §13.2's status-tracking requirement, the user chose to descope Tier 4 entirely and keep the original 2026-08-21 deferral in force. v1 focuses exclusively on statutory retrieval (§12) across all criminal-law tiers.

## 14. Question & Answer Preparation System

- Generates: questions the opposing side might ask, clarification questions, witness questions, complainant/respondent questions, follow-ups, and suggested responses.
- **Hard constraint:** Suggested responses must be strictly grounded in facts already present in the Case Builder. The system must explicitly flag questions it cannot yet help answer due to missing evidence/information, rather than fabricating a plausible-sounding answer.
- `OPEN QUESTION`: Is this feature aimed at self-represented users preparing for an interaction, or at legal professionals prepping a client/witness? Affects tone, level of legal jargon, and liability framing.

## 15. Case Strength Analysis

### 15.1 Explicit Rejection of Naive Scoring
Per the brief: no simplistic numerical "probability of winning" without a strong, defensible methodology — and no such methodology currently exists for this problem at the fidelity this system could achieve. This is a firm design constraint, not a stylistic preference.

### 15.2 Recommended Alternative Presentation (to be validated with user)
Structured, multi-dimensional, qualitative-first presentation:
- Evidence coverage per claim (supported / partially supported / unsupported).
- Enumerated contradictions and disputed facts.
- Enumerated legal uncertainty points (e.g., "multiple plausible classifications, not yet resolved").
- Enumerated counterarguments and their apparent strength (qualitative: strong/moderate/weak rationale shown).
- Explicit confidence/uncertainty language per section, never a single aggregate score.

`OPEN QUESTION`: Should there be *any* aggregate indicator (e.g., a coarse categorical band like "well-documented / partially documented / early-stage") or should presentation remain fully disaggregated? Needs product/UX discussion — some aggregate signal may aid usability but risks being over-interpreted as a verdict.

## 16. Explainability, Citation, and Hallucination Prevention

- Every legal-provision reference shown to a user must display: act name, section, jurisdiction, effective-date range, and a link/reference to the exact retrieved source chunk.
- Every agent-generated conclusion (classification, strategy option, counterargument) must be traceable to the specific facts/evidence/provisions that produced it — not just presented as an opinion.
- The system must have a well-defined behavior for **uncertainty**: explicit "I don't have enough information" / "sources conflict" / "no directly applicable provision found" states, distinct from confident answers. `DECISION REQUIRED`: exact UX pattern for surfacing uncertainty (inline flags, confidence bands, separate "needs clarification" section) — deferred to UI/UX design phase.
- Retrieval ≠ correctness (see §12.7) — this principle applies system-wide, not just to law retrieval; e.g., a "similar case" retrieval is not proof of precedential relevance either.

## 17. Jurisdiction & Temporal Validity

- Jurisdiction (which law applies) and temporal validity (which *version* of the law applies, based on event date) are treated as **first-class, mandatory fields** on every legal conclusion — not afterthoughts.
- The distinction between "identifying potentially applicable provisions" and "giving definitive legal advice" must be reflected in UI language throughout (e.g., "may be relevant," "a court would need to determine," never "you will win" or "this is illegal").

## 18. Privacy, Security, and Data Handling

**DECISION (2026-08-21):** No authentication required for v1 — session-only, anonymous use. Case data is tied to a browser/session, not a persistent account. Consequences to design for:
- Case data does **not** persist reliably across sessions/devices unless a separate mechanism is added (`OPEN QUESTION`: is any session-persistence — e.g., a local export/save-and-resume — needed, or is a case fully ephemeral within one sitting?).
- Weaker privacy posture than an authenticated system in one sense (no account-level access control) but also a smaller attack surface (no credential storage, no account-takeover risk) — consistent with portfolio-project scope (§3.1) and synthetic/demo data assumption.
- Audit logging (§7) still applies to session data while it exists, even without persistent accounts.
- This decision should be revisited before any production-track evolution of the project (§23) — session-only auth is not adequate if real users' real legal data is ever handled long-term.

`OPEN QUESTION`s — still deferred, required before any real user data is handled:
- Data residency requirements (especially if handling Indian users' sensitive legal/personal data).
- Encryption at rest/in transit for case data and uploaded evidence.
- Data retention policy — how long is case data kept, can users delete it, is there a legal-hold consideration.
- Audit logging — who can see what, and for how long are interview/agent logs retained.
- Whether any data is used for model training/improvement (should default to **no** unless explicitly opted in, given sensitivity).
- Handling of especially sensitive categories (e.g., POCSO-related content, domestic violence) may require extra safeguards, mandatory-reporting considerations in some jurisdictions, and possibly restricted/guarded flows rather than full automation. `DECISION REQUIRED`: how does the product handle legal domains with mandatory reporting or minor-safety implications? This needs explicit policy before those domains are enabled, if ever.

## 19. System Architecture & Technology

**DECISION (2026-08-21):** LLM approach is **API-based hosted models** (not local/self-hosted).

**DECISION (2026-08-24):** Full stack locked in to unblock scaffolding — proposed by the assistant given user authorization to "pick a stack unilaterally where reasonable," not independently deliberated line-by-line:

- **LLM provider: Anthropic Claude API.** One model family across all agents for v1 (no per-agent model differentiation yet); revisit cost/latency/quality tradeoffs per-agent later if warranted.
- **Backend: Python + FastAPI.** Best ecosystem fit for the LLM/agent/RAG-heavy work ahead.
- **Frontend: React + Vite + TypeScript.** Standard, fast local dev loop.
- **Primary datastore (Case Builder): SQLite.** Matches the local/dev, portfolio-scale, session-only-auth decisions already made (§3.1, §18) — no server process to run.
- **Vector database: ChromaDB (embedded).** No separate service to stand up; sufficient for one domain's statutory corpus.
- **Knowledge graph layer: not included for v1.** `OPEN QUESTION` resolved as "not worth the complexity" by default given portfolio scope — revisit only if entity/relationship modeling in the Case Builder proves inadequate with the relational model alone.
- **File/evidence storage: local filesystem**, under the repo's data directory. Encryption-at-rest is still an open §18 item — not implemented in the initial scaffold; flagged, not silently assumed solved.
- **Deployment target: local/dev only.** Consistent with §3.1's portfolio-scale framing.
- **API design: REST.** Simplest fit for a hand-coded orchestrator (§8.1) driving synchronous per-turn agent calls.

Given the API-based-LLM decision: sensitive user narrative content will be sent to Anthropic's API. This reinforces §18's data-handling requirements (no training-data opt-in by default, clear disclosure to users) and should be stated explicitly in any privacy-facing text, even for a portfolio/demo deployment using synthetic data.

## 20. Evaluation & Benchmarking Strategy (to be developed)

Planning-stage placeholders — to be filled in once scope is set:
- Retrieval evaluation: precision/recall of correct provision retrieval against a hand-built gold set of legal-scenario → correct-provision mappings.
- Citation accuracy: does every generated citation actually match retrieved source text (automatable check).
- Hallucination testing: adversarial prompts designed to induce fabricated citations or overconfident claims.
- Agent-level evaluation: does Fact Extraction correctly separate fact/opinion/assumption on labeled test narratives; does Legal Classification surface the correct hypothesis set on known scenarios.
- End-to-end case simulations against realistic (anonymized/synthetic) scenarios, ideally reviewed by a person with legal training.

`OPEN QUESTION`: Is legal-expert review available/planned at any point in this project (even informally)? This materially affects how much we can trust our own eval process.

## 21. Risks, Failure Cases, and Misuse Prevention

- **Hallucinated citations** — mitigated by §12.7's binding/verification requirement.
- **Overconfident case-strength presentation** — mitigated by §15's rejection of naive scoring.
- **Users treating output as definitive legal advice** — mitigated by persistent disclaimers, UI language choices (§17), and explicit human-in-the-loop framing (§5).
- **Jurisdiction/temporal mismatch** (applying wrong-era or wrong-region law) — mitigated by §12.3/§17 requirements.
- **Sensitive-domain harms** (e.g., mishandling domestic violence or minor-safety disclosures) — flagged in §18 as needing explicit policy, possibly gated features.
- **Misuse for generating bad-faith legal threats/harassment documents** — `OPEN QUESTION`: what safeguards (rate limits, review gates, misuse detection) are appropriate for the Document Generation agent? Needs discussion once document-generation scope is decided.
- **Over-collection of sensitive personal/legal data** without adequate security — see §18.

## 22. Human-in-the-Loop Points (candidates, to be refined)

- Before any generated document (complaint/notice/etc.) is treated as "final" — always requires explicit user acknowledgment that it's an AI draft.
- `OPEN QUESTION`: Is there ever a point where a *licensed professional* review is built into the product flow (e.g., an optional lawyer-review marketplace/handoff), or is that entirely out of scope? This is a product-strategy question, not just a technical one.

## 23. Future Expansion (explicitly NOT v1 — parking lot)

- Broader statutory coverage (state laws, additional central acts).
- Case-law/precedent search (see §13, likely deferred).
- Multi-jurisdiction support beyond India.
- Multi-language support — **DECIDED (2026-08-21): English only for v1**; Hindi/regional-language support explicitly deferred to future expansion.
- Lawyer-review marketplace / professional handoff integration.
- Deeper evidentiary content analysis (e.g., automated contract clause analysis) beyond evidence logging.
- Knowledge graph-based cross-referencing across statutes and case law.

---

## Change Log

- **2026-08-21** — Initial draft created. No user-confirmed decisions yet; all `DECISION REQUIRED` / `OPEN QUESTION` / `ASSUMPTION TO VALIDATE` items are pending the discovery interview.
- **2026-08-24** — Phase 0 closed. §2 problem statement and §5 product boundaries confirmed as drafted, no changes. §12.1 sequencing recommendation upgraded from proposal to `DECISION`: narrow-first ingestion confirmed, broad multi-domain remains the target architecture. Per-domain legal/ethical risk enumeration deferred to Phase 1 (needs first-wave domain selection first). Phase 1 begun.
- **2026-08-24** — Phase 1 discovery round 1: first-wave domain decided as **criminal law** (BNS/BNSS/BSA + historical IPC/CrPC/Evidence Act) (§12.1) — raises §12.3's dual-code problem and §18's sensitive-domain policy gap earlier than originally recommended, flagged for near-term research. State-law scope decided as **central + Karnataka** (§12.5), not central-only as previously recommended; specific Karnataka criminal-adjacent acts still to be identified during source research.
- **2026-08-24** — Phase 1 research round 1 (background agent): identified 4 Karnataka criminal-law-adjacent acts (Police Act 1963, KCOCA 2000, Prevention of Dangerous Activities/"Goonda" Act 1985, Police Complaints Authority rules); evaluated candidate sources and proposed a hierarchy. User then expanded criminal-law v1 scope to a 5-tier document hierarchy (core legislation, central special laws, state laws, judicial precedents, execution/police manuals) and **reversed §13.2's precedent-retrieval deferral for the criminal-law domain specifically** — see §12.1 and §13. Source-authority hierarchy locked in as e-Gazette > India Code > Karnataka DPAL > Indian Kanoon (paid API) (§12.2); acquisition method decided as manual human download rather than scraping, sidestepping the unverified ToS gap. Tiers 2 and 5 (special laws, police manuals) still need their own source research pass before Phase 3.
- **2026-08-24** — Phase 1 research round 2 (background agent): investigated Tier 4 (citator availability) and Tier 5 (police manuals sourcing). Found no true citator exists at portfolio-project cost, and no public source for a Karnataka Police Manual/Standing Orders. User then **descoped both Tier 4 and Tier 5**, re-confirming §13.2's original precedent-retrieval deferral rather than shipping an unreliable version of it. Criminal-law v1 document scope is now a **3-tier** hierarchy: core legislation, central special laws, Karnataka state laws (§12.1).
- **2026-08-24** — Phase 1 discovery round 2: §12.3's effective-date/successor-pointer data model confirmed as a firm requirement (was an assumption). §12.4's amendment-tracking strategy decided as **automated periodic re-check**, overriding the doc's own manual-review-gated recommendation — risk flagged (silent automated ingestion of a misread amendment conflicts with §7/§16), with a Phase 2 follow-up to define whether "automatic" means full silent ingestion or automated detection + human-gated application.
- **2026-08-24** — User directed a jump straight to code scaffolding, explicitly deferring (not dropping) Phase 1's remaining practice-of-law and privacy research, and explicitly skipping domain risk enumeration. Phase 2 stack and architecture decisions made to unblock this (§8.1, §8.8, §19): hand-coded orchestrator state machine, shared Case Builder state for agent communication, synchronous per-turn invocation; Python/FastAPI backend, React/Vite/TypeScript frontend, Anthropic Claude API, SQLite, embedded ChromaDB, local filesystem evidence storage, local/dev deployment, REST API. Encryption-at-rest for evidence storage explicitly NOT implemented yet — flagged as a real gap, not silently assumed solved. Repository scaffolding follows this entry.
