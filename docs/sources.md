# Source registry

Corpus URL registry for the facts-only RAG assistant.  
Schema: Architecture §6.2. Order: Implementation plan Phase 1 (**Groww first**).

**Ingest from `local_path`. Cite `url`.** Never cite a filesystem path in answers.

| Field | Description |
| --- | --- |
| `source_id` | Stable id |
| `url` | Public citation URL |
| `publisher` | `GROWW` \| `SBI` \| `AMFI` \| `SEBI` |
| `doc_type` | `groww_scheme` \| `KIM` \| `SID` \| `factsheet` \| `TER` \| `FAQ` \| `statement_guide` \| `education` |
| `scheme` | Canonical scheme name, or `shared` |
| `scheme_tag` | Stable filter tag used at ingest/retrieve |
| `local_path` | Snapshot path used at ingest (empty until Phase 2 fetch for HTML) |
| `retrieved_on` | ISO date of fetch or PDF registration |
| `priority` | `1` = Groww (primary), `2` = SBI scheme docs, `3` = shared / AMFI / SEBI |

**AMC:** SBI Mutual Fund only. **Plan coverage:** Direct Growth listings on Groww.

---

## Naming decision (Phase 1.5) — CONFIRMED

| Question | Decision |
| --- | --- |
| Does Groww `https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth` equal **SBI Small Cap Fund**? | **Yes — same scheme.** |
| Evidence (Groww) | Page title / product name is **SBI Small Cap Fund Direct Growth**; category ranks under Equity Small Cap; objective is predominantly small-cap stocks. Legacy URL slug retains `small-midcap`. |
| Evidence (SBI) | Official factsheet / offer docs use **SBI Small Cap Fund**, noted as previously **SBI Small & Midcap Fund**. Local PDFs: `kim---sbi-small-cap-fund.pdf`, `sid---sbi-small-cap-fund.pdf`. |
| Ingest / retrieve tags | **Merge.** Use canonical scheme `SBI Small Cap Fund` and tag `sbi_small_cap` for both Groww HTML and SBI KIM/SID. Do **not** keep separate `groww_small_midcap` vs `sbi_small_cap` tags. |
| Citation for Groww row | Still cite the Groww URL as listed (`.../sbi-small-midcap-fund-direct-growth`). |

Checked: 2026-08-24.

---

## Safe aliases (Phase 1.6) — CONFIRMED

Apply during parse / scheme detection only. Citation URLs stay as registered.

| Alias / former name | Canonical scheme | `scheme_tag` |
| --- | --- | --- |
| Bluechip / SBI BlueChip Fund | SBI Large Cap Fund | `sbi_large_cap` |
| Long Term Equity / SBI Long Term Equity Fund / Magnum Taxgain (historical) | SBI ELSS Tax Saver Fund | `sbi_elss` |
| Small & Midcap / Small Midcap / SBI Small & Mid Cap Fund | SBI Small Cap Fund | `sbi_small_cap` |

**Do not alias:** other AMCs, other SBI schemes (e.g. Mid Cap, Large & Midcap), or Regular-plan variants as if they were these Direct Growth Groww pages.

---

## Block A — Primary: Groww scheme URLs (sources #1–5) — Phase 1.2 DONE

`publisher=GROWW`, `doc_type=groww_scheme`, **`priority=1`**.  
Allowlist: only these five `groww.in/mutual-funds/...` paths (no Groww blog/news/other funds).

| Check | Result |
| --- | --- |
| URLs registered | 5 / 5 (plan Phase 1 task 2) |
| HTTP verify (2026-08-24) | All **200 OK** (public GET) |
| HTML snapshot on disk | **Yes** — Phase 2.1 fetch (2026-08-25) |
| `retrieved_on` | **2026-08-25** |

**Registered in source list:** 2026-08-24. **Fetched:** 2026-08-25.

| # | source_id | url | publisher | doc_type | scheme | scheme_tag | local_path | retrieved_on | priority |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| 1 | `groww-large-cap` | https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth | GROWW | groww_scheme | SBI Large Cap Fund | `sbi_large_cap` | `docs/corpus/groww/sbi-large-cap-direct-plan-growth.html` | 2026-08-25 | 1 |
| 2 | `groww-flexicap` | https://groww.in/mutual-funds/sbi-flexicap-fund-direct-growth | GROWW | groww_scheme | SBI Flexicap Fund | `sbi_flexicap` | `docs/corpus/groww/sbi-flexicap-fund-direct-growth.html` | 2026-08-25 | 1 |
| 3 | `groww-elss` | https://groww.in/mutual-funds/sbi-elss-tax-saver-fund-direct-growth | GROWW | groww_scheme | SBI ELSS Tax Saver Fund | `sbi_elss` | `docs/corpus/groww/sbi-elss-tax-saver-fund-direct-growth.html` | 2026-08-25 | 1 |
| 4 | `groww-contra` | https://groww.in/mutual-funds/sbi-contra-fund-direct-growth | GROWW | groww_scheme | SBI Contra Fund | `sbi_contra` | `docs/corpus/groww/sbi-contra-fund-direct-growth.html` | 2026-08-25 | 1 |
| 5 | `groww-small-cap` | https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth | GROWW | groww_scheme | SBI Small Cap Fund | `sbi_small_cap` | `docs/corpus/groww/sbi-small-midcap-fund-direct-growth.html` | 2026-08-25 | 1 |

**Phase 2 note:** fail the index build if any of these five GETs fail. Cite `url` (Groww), never `local_path`.

---

## Block B — Supporting: SBI KIM/SID (sources #6–15) — Phase 1.3 DONE

`publisher=SBI`, `doc_type=KIM|SID`, **`priority=2`**.  
**Ingest** local PDFs already on disk. **Cite** matching `sbimf.com` PDF URLs (not `docs/corpus/...`).  
Hub (also listed in Phase 1.4): https://www.sbimf.com/offer-document-sid-kim

| Check | Result |
| --- | --- |
| Local PDFs | 10 / 10 present under `docs/corpus/kim/` and `docs/corpus/sid/` |
| Citation URLs | Scheme PDF URLs on `sbimf.com` (verified HTTP 200, `application/pdf`, 2026-08-25) |
| `retrieved_on` | Local file date **2026-08-24** (registration / corpus copy date) |

**Registered in source list:** 2026-08-25.

| # | source_id | url | publisher | doc_type | scheme | scheme_tag | local_path | retrieved_on | priority |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| 6 | `kim-large-cap` | https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf | SBI | KIM | SBI Large Cap Fund | `sbi_large_cap` | `docs/corpus/kim/kim---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf` | 2026-08-24 | 2 |
| 7 | `sid-large-cap` | https://www.sbimf.com/docs/default-source/sif-forms/sid---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf | SBI | SID | SBI Large Cap Fund | `sbi_large_cap` | `docs/corpus/sid/sid---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf` | 2026-08-24 | 2 |
| 8 | `kim-flexicap` | https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-flexicap-fund.pdf | SBI | KIM | SBI Flexicap Fund | `sbi_flexicap` | `docs/corpus/kim/kim---sbi-flexicap-fund.pdf` | 2026-08-24 | 2 |
| 9 | `sid-flexicap` | https://www.sbimf.com/docs/default-source/sif-forms/sid---sbi-flexicap-fund.pdf | SBI | SID | SBI Flexicap Fund | `sbi_flexicap` | `docs/corpus/sid/sid---sbi-flexicap-fund.pdf` | 2026-08-24 | 2 |
| 10 | `kim-elss` | https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund).pdf | SBI | KIM | SBI ELSS Tax Saver Fund | `sbi_elss` | `docs/corpus/kim/kim---sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund).pdf` | 2026-08-24 | 2 |
| 11 | `sid-elss` | https://www.sbimf.com/docs/default-source/sif-forms/sid---sbi-elss-tax-saver-fund.pdf | SBI | SID | SBI ELSS Tax Saver Fund | `sbi_elss` | `docs/corpus/sid/sid---sbi-elss-tax-saver-fund.pdf` | 2026-08-24 | 2 |
| 12 | `kim-contra` | https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-contra-fund.pdf | SBI | KIM | SBI Contra Fund | `sbi_contra` | `docs/corpus/kim/kim---sbi-contra-fund.pdf` | 2026-08-24 | 2 |
| 13 | `sid-contra` | https://www.sbimf.com/docs/default-source/sif-forms/sid---sbi-contra-fund.pdf | SBI | SID | SBI Contra Fund | `sbi_contra` | `docs/corpus/sid/sid---sbi-contra-fund.pdf` | 2026-08-24 | 2 |
| 14 | `kim-small-cap` | https://www.sbimf.com/docs/default-source/sif-forms/kim---sbi-small-cap-fund.pdf | SBI | KIM | SBI Small Cap Fund | `sbi_small_cap` | `docs/corpus/kim/kim---sbi-small-cap-fund.pdf` | 2026-08-24 | 2 |
| 15 | `sid-small-cap` | https://www.sbimf.com/docs/default-source/sif-forms/sid---sbi-small-cap-fund.pdf | SBI | SID | SBI Small Cap Fund | `sbi_small_cap` | `docs/corpus/sid/sid---sbi-small-cap-fund.pdf` | 2026-08-24 | 2 |

**Note:** Local PDFs are the ingest bytes. Online `url` may be a newer AMC upload than the local copy; Phase 2 may re-download later if checksums diverge. Citations always use `url`.

---

## Block C — Supporting: shared official pages (sources #16–22) — Phase 1.4 DONE

`publisher=SBI|AMFI|SEBI`, **`priority=3`**.  
HTML (and later factsheet PDFs) fetched in Phase 2 into `docs/corpus/shared/` / `docs/corpus/factsheets/`.

| Check | Result |
| --- | --- |
| Required hubs (plan task 4) | 5 / 5 registered |
| Optional extras | Smart Statement + SEBI riskometer |
| HTTP verify / fetch (2026-08-25) | SBI + AMFI **fetched**; SEBI soft-skipped (DNS fail) — retry in Phase 2 later |
| Local snapshots | **6 / 7** under `docs/corpus/shared/` (`sebi-riskometer` pending) |

**Registered in source list:** 2026-08-25. **Fetched (except SEBI):** 2026-08-25.

| # | source_id | url | publisher | doc_type | scheme | scheme_tag | local_path | retrieved_on | priority |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| 16 | `sbi-home` | https://www.sbimf.com/ | SBI | FAQ | shared | `shared` | `docs/corpus/shared/sbi-home.html` | 2026-08-25 | 3 |
| 17 | `sbi-sid-kim-hub` | https://www.sbimf.com/offer-document-sid-kim | SBI | FAQ | shared | `shared` | `docs/corpus/shared/sbi-sid-kim-hub.html` | 2026-08-25 | 3 |
| 18 | `sbi-factsheets-hub` | https://www.sbimf.com/factsheets/ | SBI | factsheet | shared | `shared` | `docs/corpus/shared/sbi-factsheets-hub.html` | 2026-08-25 | 3 |
| 19 | `sbi-ter` | https://www.sbimf.com/total-expense-ratio/ | SBI | TER | shared | `shared` | `docs/corpus/shared/sbi-ter.html` | 2026-08-25 | 3 |
| 20 | `amfi-investor` | https://www.amfiindia.com/investor | AMFI | education | shared | `shared` | `docs/corpus/shared/amfi-investor.html` | 2026-08-25 | 3 |
| 21 | `sbi-smart-statement` | https://www.sbimf.com/smart-statement | SBI | statement_guide | shared | `shared` | `docs/corpus/shared/sbi-smart-statement.html` | 2026-08-25 | 3 |
| 22 | `sebi-riskometer` | https://investor.sebi.gov.in/riskometer.html | SEBI | education | shared | `shared` | `docs/corpus/shared/sebi-riskometer.html` | (pending fetch) | 3 |

**Statement-guide note (`sbi-smart-statement`):** Public process page only. The assistant must **never** collect, store, or ask for PAN/email/OTP (problem-statement PII rules). Use for “how to request a statement” facts, then refuse if the user pastes PAN.

**Performance refusals:** Prefer citing `sbi-factsheets-hub` (or a future per-scheme factsheet PDF), **not** Groww return charts.

### Phase 2 fetch targets (not yet on disk)

| Target | Destination | Notes |
| --- | --- | --- |
| Sources #16–22 HTML | `docs/corpus/shared/*.html` | Required for shared-page ingest |
| Per-scheme factsheet PDFs (optional, keep total ≤25) | `docs/corpus/factsheets/` | Download from https://www.sbimf.com/factsheets/ for the five schemes if needed for riskometer/benchmark/performance-link cases |
| SEBI circular (optional alt) | `docs/corpus/shared/` | https://www.sebi.gov.in/legal/circulars/aug-2021/disclosure-of-risk-o-meter-of-scheme-benchmark-and-portfolio-details-to-the-investors_52262.html |

**Citeable URL count:** 5 Groww + 10 SBI KIM/SID + 7 shared = **22** (within 15–25).

---

## Status

| Phase 1 task | Status |
| --- | --- |
| 1.1 Schema + Groww-first registry file | Done (this file; Groww #1–5 registered) |
| 1.2 Groww URLs | **Done** — Block A; all five URLs verified HTTP 200 (2026-08-24) |
| 1.3 SBI KIM/SID rows | **Done** — Block B; 10 local PDFs mapped to verified sbimf.com PDF URLs |
| 1.4 Shared official pages | **Done** — Block C; 7 shared URLs; total citeable **22** |
| 1.5 Naming check Small Cap / Small Midcap | **Confirmed — same scheme; merged tags** |
| 1.6 Safe aliases | **Confirmed — table above** |

### Phase 2 task status

| Task | Status |
| --- | --- |
| 2.1 `src/ingest/fetch.py` (Groww → PDFs → shared) | **Done** — 5 Groww HTML, 10 PDFs registered, 6/7 shared HTML |
| 2.2 `parse.py` | **Done** — Groww HTML + PDF + shared; 21 docs parsed |
| 2.3 `chunk.py` | **Done** — section-aware + quality pass; `data/chunks.jsonl` |
| 2.4 `embed.py` | **Done** — `python scripts/embed_corpus.py` (optional `--smoke`) |
| 2.5 `scripts/build_index.py` | **Done** — `python scripts/build_index.py` (or `python -m src.ingest`) |
| 2.6 Smoke-test retrieval | **Done** (via `--smoke`) |
