# Criminal Law v1 — Document Acquisition Manifest

> **Scope: 3 tiers, not 5.** Tiers 4 (judicial precedents) and 5 (police manuals) were researched on 2026-08-24 and descoped — no viable citator source and no public police-manual source exist at portfolio-project scope. See the bottom of this file.

> Acquisition method: **manual human download** (`CLAUDE.md` §12.2). Drop each downloaded file into the matching tier folder below. Prefer PDF where available (preserves official formatting); keep the original filename or rename to `<ActName>_<Year>.pdf`.
>
> For every file, note the source URL and retrieval date somewhere retrievable (a spreadsheet, or a `.source.txt` sidecar next to the file) — provenance tracking is a hard requirement (`CLAUDE.md` §16), and it's far easier to capture at download time than to reconstruct later.
>
> Checklist: mark `[x]` as each document is downloaded and placed.

## Tier 1 — Core Legislation (`01-core-legislation/`)

Source hierarchy: e-Gazette (ground truth) → India Code (primary working source).

- [ ] **Bharatiya Nyaya Sanhita (BNS), 2023** — substantive criminal law, current. India Code: https://www.indiacode.gov.in — search "Bharatiya Nyaya Sanhita 2023". e-Gazette notification: https://egazette.gov.in — search notification dated 25 Dec 2023 (Act No. 45 of 2023).
- [ ] **Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023** — procedural code, current. Same sources as above (Act No. 46 of 2023).
- [ ] **Bharatiya Sakshya Adhiniyam (BSA), 2023** — evidence law, current. Same sources as above (Act No. 47 of 2023).
- [ ] **Indian Penal Code (IPC), 1860** — historical, governs pre-1 July 2024 events. India Code retains repealed acts.
- [ ] **Code of Criminal Procedure (CrPC), 1973** — historical, governs pre-1 July 2024 events.
- [ ] **Indian Evidence Act, 1872** — historical, governs pre-1 July 2024 events.

## Tier 2 — Central Special Laws (`02-central-special-laws/`)

Source: India Code (same repository as Tier 1 — these are also central acts, confirmed 2026-08-24).

- [ ] **Protection of Children from Sexual Offences (POCSO) Act, 2012**
- [ ] **Narcotic Drugs and Psychotropic Substances (NDPS) Act, 1985**
- [ ] **Unlawful Activities (Prevention) Act (UAPA), 1967**
- [ ] **Information Technology (IT) Act, 2000** — criminal-law-relevant sections only (e.g., §§43–47, 65–78) need not download the whole act's non-criminal provisions, but easier to grab the full text and scope later.

## Tier 3 — Karnataka State Laws (`03-karnataka-state-laws/`)

Source: Karnataka DPAL — https://dpal.karnataka.gov.in

- [ ] **Karnataka Police Act, 1963** (as amended through 2012 Police Reforms Ordinance)
- [ ] **Karnataka Control of Organised Crimes Act, 2000 (KCOCA)** (as amended 2009)
- [ ] **Karnataka Prevention of Dangerous Activities Act, 1985** ("Goonda Act", as amended 2000)
- [ ] **Karnataka State Police Complaints Authority rules** (under Police Act §20C/20D, following the 2012 Ordinance)

**Not yet confirmed current** — before relying on these, verify no amendments exist after the years noted above (Phase 1 research flagged this as unverified, not resolved).

## Tier 4 — Judicial Precedents (`04-judicial-precedents/`) — DESCOPED

**Descoped 2026-08-24, `CLAUDE.md` §13.2.** No true citator (overruled/distinguished/followed tracking) exists at portfolio-project cost — Indian Kanoon's API exposes only raw cite/cited-by counts, not treatment classification; real citators are SCC Online/Manupatra-subscription-tier only. Case-law/precedent retrieval stays deferred to a later phase. Folder left in place for that future work; nothing to download here for v1.

## Tier 5 — Execution & Police Manuals (`05-police-manuals/`) — DESCOPED

**Descoped 2026-08-24, `CLAUDE.md` §12.1.** No public downloadable source exists for a Karnataka Police Manual or consolidated Standing Orders — the historical 1965/1973 manual is archival/physical only; ksp.karnataka.gov.in hosts circulars and an RTI-mandated disclosure manual, not an operational manual. Further pursuit (RTI request, deeper DPAL index crawl) is out of scope for this project. Folder left in place in case this changes; nothing to download here for v1.

---

**Provenance reminder:** every file placed here needs, at minimum, its source URL and download date recorded before Phase 3 ingestion treats it as authoritative (`CLAUDE.md` §12.2, §16).
