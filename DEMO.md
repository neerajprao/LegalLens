# Legal Lens — Live Demo Script

The LLM is now **fully local** — `qwen2.5:7b-instruct` running via Ollama, no API key, no internet dependency, no rate limit, no cost (switched 2026-08-26 at the user's request; see `CLAUDE.md` §19 and `PROJECT_REPORT.md` §7 for the full history: Anthropic → Gemini free tier → local Qwen3.5 9B, then swapped again 2026-09-16 to the current smaller/faster model purely for latency). This makes the demo simpler and stronger than either cloud stage was: nothing can 429, nothing needs a credential you might forget to bring, and the whole pipeline was verified to run start to finish live before this script was written (`backend/e2e_smoke.py`, 13 of 13 stages, no mocking — see `PROJECT_REPORT.md` §6).

The only real constraint: each real model call takes roughly **10–20 seconds on Apple M3 Pro** (longer for the more complex prompts like Document Generation) — this is CPU/GPU inference on a laptop, not a data-center API, so build that pacing into how you narrate the demo rather than rushing between clicks.

---

## Before you start

The easy way — one command from the project root, does everything (venv, deps, `.env`, ingestion, both servers):
```bash
ollama pull qwen2.5:7b-instruct   # one-time, skip if already pulled
python3 run.py
```
`Ctrl+C` stops both servers cleanly when you're done. See `explanation.md` §4 for exactly what it checks and skips.

If you'd rather run each piece by hand (or `run.py` isn't available):
```bash
# One-time: Ollama running with the model pulled
ollama pull qwen2.5:7b-instruct   # skip if already pulled
# make sure the Ollama app/daemon is running (check: curl http://localhost:11434/api/tags)

# Terminal 1 — backend
cd backend
source .venv/bin/activate        # or: python -m venv .venv && pip install -e . first time
python -m app.ingestion          # only needed once, or after changing data/raw/criminal-law/
uvicorn app.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm install                      # first time only
npm run dev                      # serves http://localhost:5173
```
Either way: open `http://localhost:5173`. Confirm `curl http://localhost:8000/health` returns `{"status":"ok"}` and `curl http://localhost:11434/api/tags` lists `qwen2.5:7b-instruct` if anything looks wrong.

---

## Stage 1 — Interview

1. Click **"Start a case"** → a `case_id` (UUID) appears. *Say: "No login, no account — session-based by design; the case ID itself is the access token, a deliberate v1 scope decision covered in `CLAUDE.md` §18."*
2. Type a short narrative into the textarea, e.g.:
   > *"On 3 January 2026, my neighbor sent me threatening WhatsApp messages after a dispute over a shared wall. I have screenshots of the messages."*
3. Click **Submit** and wait (~15-20s — the model is genuinely thinking, running on this laptop, not calling out anywhere). Returns structured `entities`/`events`/`statements`, each statement tagged `fact`/`assumption`/`opinion`/`allegation`/`unknown`. On success the view auto-advances to "2. Case Dashboard". *Say: "That request never left this machine — worth pointing at Activity Monitor / a network tab to show zero outbound traffic during that wait, if you want to make the point vividly."*
4. Back on stage 1 later: **Interview panel** ("Get next question") asks the single most legally material next question, with a one-sentence rationale — try answering it with something that contradicts an earlier statement and watch it get flagged. **Timeline panel** sorts whatever events exist chronologically and separates undated ones (instant, no model call).

## Stage 2 — Case Dashboard

5. **Claims & Evidence panel** — add a claim ("Threatening messages were sent"), add evidence linked to it (upload an actual image/PDF file — instant, no model call). OCR/text-extraction runs locally (Tesseract/pypdf), and the file is Fernet-encrypted before being written to disk — you can `cat` the file in `data/evidence/` afterward to show it's genuinely not readable plaintext.
6. Click **"Organize evidence"** — groups evidence by linked claim, shows extraction confidence and a "Mark disputed" toggle (instant).
7. Click **"Analyze evidence gaps"** — the model suggests what evidence type would typically help; the supported/unsupported/disputed/partially-supported *status* itself is computed deterministically, never by the model.
8. **Classification & Law Retrieval panel** — classification takes a model call; **Law Retrieval itself makes zero LLM calls** — it's a direct ChromaDB query. A strong standalone demo of the RAG retrieval, with no need to wait on a model call at all:
   ```bash
   cd backend && python -c "
   from app.vector_store import query_provisions
   for h in query_provisions('punishment for murder', n_results=3):
       print(h['metadata']['act_name'], '§' + h['metadata']['section_number'], '-', h['metadata']['section_title'][:60])
   "
   ```
   Returns real matching sections from the real 2,761-chunk corpus of 13 government PDFs — never invented.

   Back in the UI, click **"View in source"** on any retrieved provision card — it opens the real source PDF with that provision's own text highlighted in gold, baked in server-side by `pdf_highlight.py` (PyMuPDF), not just the browser's own "find in page." *Say: "This used to just jump to the page — it originally had a real bug where the linked page was the Act's own Table of Contents, not the actual explanation, because a duplicate title-only chunk was winning retrieval. Fixed by deduplicating the corpus and highlighting the real passage server-side."*
9. **Devil's Advocate panel**, **Legal Strategy panel** — for Strategy, specifically demo the acknowledgment gate: clicking "View suggested options" first shows *only* a disclaimer with an "I understand" button — nothing else renders until that's clicked. A real UI implementation of a documented product-boundary decision (`CLAUDE.md` §8.5).
10. **Question & Answer Preparation panel** — try a case with a claim that has no linked evidence and watch it return `suggested_response: null` with a real gap note instead of making something up.

## Stage 3 — Document Review

11. **Document Drafts panel** — pick a draft type, generate. If citations were used, point out the citation-verification banner: any citation the model claims to have used gets checked against what was *actually* retrieved, and anything unverified is flagged in a red banner rather than silently trusted. This agent used to fail on complex cases (too many noisy retrieved provisions overwhelmed the prompt) — a real bug, found by direct investigation rather than assumed away as "the model just isn't good enough," and fixed by capping/deduplicating what gets retrieved before drafting. It now produces a real, correctly-cited draft reliably.
12. **Case Strength panel** — with zero claims it correctly shows `"early-stage"` — a deterministic function, no LLM involved in computing the band itself, even though the detailed sections above it (evidence coverage, counterarguments) do come from real model calls. Explain the three-band design and point out the disclaimer text ("not a probability of success or a legal verdict").
13. **Audit Log panel** — instant, no model call. Shows every material mutation logged in order, with timestamps.

---

## If the model is slow or a step doesn't come back cleanly

This is real local inference on a laptop, not a guaranteed-fast cloud API — narrate that plainly rather than apologizing for it: *"this is running entirely on this machine's own GPU, which is a meaningfully different tradeoff than the cloud APIs everyone else's demo probably relies on."* If you'd rather not wait live for every step, fall back to the test suite instead — a legitimate, honest substitute:
```bash
cd backend && python -m pytest -v
```
116 tests, all passing, in under 6 seconds. Walk through a few interesting ones out loud:
- `test_citation_accuracy.py` — checks all 2,761 real corpus chunks for label/text self-consistency (this test caught a real bug — see `PROJECT_REPORT.md` §6).
- `test_ingestion.py::test_chunk_by_section_drops_table_of_contents_duplicate_in_favor_of_real_section_body` — the regression test for the 2026-09-17 TOC-duplicate bug that started this whole line of fixes.
- `test_pdf_highlight.py` — asserts real highlight annotations land on the correct page of the real source PDF, and only there.
- `test_adversarial.py` — a test that *proves a real gap exists* (a fabricated citation embedded in prose isn't caught) rather than only testing what already passes.
- `test_case_strength.py::test_case_strength_never_returns_a_numeric_score` — walks the entire API response tree asserting no score-shaped key ever appears.
- `test_fact_extraction_retry.py::test_wrong_shaped_but_valid_json_is_treated_as_a_parse_failure` — the regression test for the real crash bug the local model exposed, and how it's now handled.
- `test_retrieved_provisions_capping.py` — the regression test for the *other* real Document Generation bug (too much noisy retrieved context, not a capability wall) — a good story of investigating a plausible-sounding explanation instead of accepting it.

---

## Anticipated audience questions

See `explanation.md` §19 ("Viva / Presentation Cheat Sheet") for ready answers to: *"How do you stop the AI from making up citations?"*, *"How is case strength shown without a misleading number?"*, *"What was the hardest bug you found?"*, *"Why no authentication?"*, and *"What would you build next?"* — plus the new obvious one: *"Why local instead of a cloud API?"* → cost, privacy (nothing leaves the machine), and no rate limits, at the cost of being slower than a cloud API. A good follow-up if asked "did going local cost you anything in quality?": yes, briefly — it surfaced a real bug (Document Generation losing track of its task when handed too much noisy retrieved context) that a bigger cloud model had been silently tolerating. Fixed by capping the input, not by giving up on the local model.
