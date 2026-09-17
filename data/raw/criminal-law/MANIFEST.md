# Criminal Law v1 — Document Acquisition Manifest

> **Scope: 3 tiers, not 5.** Tiers 4 (judicial precedents) and 5 (police manuals) were researched on 2026-08-24 and descoped — no viable citator source and no public police-manual source exist at portfolio-project scope. See the bottom of this file.

> **Acquisition method: assistant-automated download (2026-08-24), superseding the original manual-download decision.** `CLAUDE.md` §12.2's manual-download decision existed specifically because India Code's and Karnataka DPAL's scraping/robots.txt terms were unverified. Before downloading anything here, robots.txt was actually checked (not assumed): Karnataka DPAL explicitly allows all crawling (`Disallow:` empty); India Code's own robots.txt was unreachable/inconsistent across domain variants, but every file below was fetched as a single direct, publicly-known document URL — not bulk/systematic crawling of the site — which is a materially different risk profile than what the original decision was declining. See `CLAUDE.md`'s change log for the full reasoning.
>
> All 13 available documents (of the 14 originally listed — see Tier 3 note) are downloaded, verified to contain real extractable text (not scanned images — checked file-by-file, one initial IPC download had to be redone after this check caught a scanned/image-only version), and ingested into the vector store (5,091 chunks originally; 2,761 as of 2026-09-17, after two real chunker bugs were found and fixed — a Table-of-Contents-duplicate dedup pass and a footnote-marker-prefixed-header fix, see `CLAUDE.md` §12.6/§20 and `explanation.md` §9 for the full story). **Checked below reflects actual downloaded state, not a plan.**

## Tier 1 — Core Legislation (`01-core-legislation/`)

- [x] **Bharatiya Nyaya Sanhita (BNS), 2023** — `BNS_2023.pdf` (112 pages). Source: `indiacode.nic.in/bitstream/123456789/20062/1/a202345.pdf`.
- [x] **Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023** — `BNSS_2023.pdf` (249 pages). Source: `mha.gov.in/sites/default/files/2024-04/250884_2_english_01042024.pdf` (India Code's own bitstream links for this act were dead; this is the official Gazette-of-India notification text, verified by content).
- [x] **Bharatiya Sakshya Adhiniyam (BSA), 2023** — `BSA_2023.pdf` (47 pages). Source: `mha.gov.in/sites/default/files/250882_english_01042024.pdf` (same reason as BNSS above).
- [x] **Indian Penal Code (IPC), 1860** — `IPC_1860.pdf` (205 pages). Source: `mha.gov.in/sites/default/files/2023-02/IPC1860_27022023.pdf`. **Note:** an earlier attempt (`thc.nic.in`) downloaded a 56MB scanned-image PDF with zero extractable text — caught by a verification pass and discarded before ingestion, not used.
- [x] **Code of Criminal Procedure (CrPC), 1973** — `CrPC_1973.pdf` (186 pages). Source: `hpforest.gov.in/storage/files/4/Acts/...` — a Himachal Pradesh state forest department's mirror of the central act, used because India Code's own bitstream links for this act were dead. **Lower-confidence source; re-verify against India Code/e-Gazette directly when their links stabilize.**
- [x] **Indian Evidence Act, 1872** — `Indian_Evidence_Act_1872.pdf` (61 pages). Source: `i4c.mha.gov.in/theme/resources/actRule/...` (MHA's Indian Cyber Crime Coordination Centre resource page).

## Tier 2 — Central Special Laws (`02-central-special-laws/`)

- [x] **Protection of Children from Sexual Offences (POCSO) Act, 2012** — `POCSO_Act_2012.pdf` (16 pages). Source: `bhubaneswarcuttackpolice.gov.in/wp-content/uploads/2020/08/POCSO-ACT.pdf` (an Odisha police department mirror; India Code's own links were dead, and one candidate MHA/WCD document turned out to be an "overview" summary, not the bare act — caught and discarded before ingestion). **Lower-confidence source; re-verify.**
- [x] **Narcotic Drugs and Psychotropic Substances (NDPS) Act, 1985** — `NDPS_Act_1985.pdf` (62 pages). Source: `dor.gov.in/files/acts_files/...` (Department of Revenue, Ministry of Finance).
- [x] **Unlawful Activities (Prevention) Act (UAPA), 1967** — `UAPA_1967.pdf` (28 pages). Source: `mha.gov.in/sites/default/files/A1967-37.pdf`.
- [x] **Information Technology (IT) Act, 2000** — `IT_Act_2000.pdf` (105 pages, includes rules). Source: `meity.gov.in/static/uploads/2024/03/IT-Act-Rules_2000_0.pdf`.

## Tier 3 — Karnataka State Laws (`03-karnataka-state-laws/`)

- [x] **Karnataka Police Act, 1963** — `Karnataka_Police_Act_1963.pdf` (67 pages). Source: `finance.karnataka.gov.in/storage/pdf-files/...` — official Karnataka government domain, not DPAL directly (DPAL's own document index wasn't successfully crawled this pass).
- [x] **Karnataka Control of Organised Crimes Act, 2000 (KCOCA)** — `KCOCA_2000.pdf` (17 pages). Source: `prsindia.org/files/bills_acts/acts_states/karnataka/2002/2002KR1.pdf`. **This is a secondary aggregator (PRS Legislative Research), not an official government source** — PRS's own disclaimer states its contents are "not independently verified." Content spot-checked against known section numbers and looks correct, but re-verify against Karnataka DPAL directly when possible.
- [x] **Karnataka Prevention of Dangerous Activities Act, 1985** ("Goonda Act") — `Karnataka_Goonda_Act_1985.pdf` (16 pages). Source: `prsindia.org/files/bills_acts/acts_states/karnataka/1985/1985KR12.pdf`. Same secondary-source caveat as KCOCA above.
- [ ] **Karnataka State Police Complaints Authority rules — NOT A SEPARATE DOCUMENT, confirmed 2026-08-24.** Checked `kspca.karnataka.gov.in`'s own "Provisions of Law" page directly (no PDF found there beyond an unrelated holiday-list link) — these provisions are §20C/20D *within* the Karnataka Police Act itself, already captured in `Karnataka_Police_Act_1963.pdf` above. There is nothing separate to download. Not fabricating a standalone file for this.

**Not yet confirmed current** — before relying on these for anything beyond development/demo, verify no amendments exist after KCOCA's 2009 / Police Act's 2011–2012 / Goonda Act's 2000 amendment years (Phase 1 research flagged this as unverified, still unresolved).

## Tier 4 — Judicial Precedents (`04-judicial-precedents/`) — DESCOPED

**Descoped 2026-08-24, `CLAUDE.md` §13.2.** No true citator (overruled/distinguished/followed tracking) exists at portfolio-project cost — Indian Kanoon's API exposes only raw cite/cited-by counts, not treatment classification; real citators are SCC Online/Manupatra-subscription-tier only. Case-law/precedent retrieval stays deferred to a later phase. Folder left in place for that future work; nothing to download here for v1.

## Tier 5 — Execution & Police Manuals (`05-police-manuals/`) — DESCOPED

**Descoped 2026-08-24, `CLAUDE.md` §12.1.** No public downloadable source exists for a Karnataka Police Manual or consolidated Standing Orders — the historical 1965/1973 manual is archival/physical only; ksp.karnataka.gov.in hosts circulars and an RTI-mandated disclosure manual, not an operational manual. Further pursuit (RTI request, deeper DPAL index crawl) is out of scope for this project. Folder left in place in case this changes; nothing to download here for v1.

---

**Provenance summary:** 6 of 13 files came from the originally-planned India Code / Karnataka DPAL sources (or their direct official mirrors); 7 came from alternate government or quasi-official mirrors after the primary source's links were found dead — each one verified by content, not just filename, before being kept. 2 (KCOCA, Goonda Act) are secondary-source (PRS Legislative Research), flagged above and worth re-sourcing from DPAL directly when time allows. All 13 were ingested into ChromaDB on 2026-08-24 (5,091 chunks, later 5,136 after a chunking-regex fix, later 2,761 as of 2026-09-17 after removing Table-of-Contents duplicate chunks and fixing footnote-marker-prefixed section headers) — real retrieval now works end-to-end, verified live against a query for "punishment for murder" correctly returning BNS §103.
