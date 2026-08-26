# Problem Statement: Mutual Fund FAQ Assistant (Facts-Only Q&A)

## Overview

The objective of this project is to build a **facts-only FAQ assistant** for mutual fund schemes, using **Groww** as the reference product context. The assistant will answer objective, verifiable queries related to mutual funds by retrieving information exclusively from official public sources, such as AMC (Asset Management Company) websites, AMFI, and SEBI.

The system must strictly avoid providing investment advice, opinions, or recommendations. Every response must include a **single, clear source link** and adhere to defined constraints around clarity, accuracy, and compliance.

## Objective

Design and implement a lightweight **Retrieval-Augmented Generation (RAG)**-based assistant that:

- Answers factual queries about mutual fund schemes
- Uses a curated corpus of official documents
- Provides concise, source-backed responses

## Target Users

- Retail investors comparing mutual fund schemes
- Customer support and content teams handling repetitive mutual fund queries

## Scope of Work

### 1. Corpus (RAG knowledge base)

Pick **exactly one AMC** and **3–5 schemes** under it. Use the Groww scheme pages provided as examples/scheme landing points (or as additional starting material), then collect authoritative official pages for each scheme and general concepts.

**Example scheme scope** (choose 3–5 total under one AMC; example given: SBI):

- https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth
- https://groww.in/mutual-funds/sbi-flexicap-fund-direct-growth
- https://groww.in/mutual-funds/sbi-elss-tax-saver-fund-direct-growth
- https://groww.in/mutual-funds/sbi-contra-fund-direct-growth
- https://groww.in/mutual-funds/sbi-small-midcap-fund-direct-growth

Collect **15–25 public pages** from official sources (AMC / SEBI / AMFI). Official landing pages:

- https://www.sbimf.com/offer-document-sid-kim
- https://www.sbimf.com/factsheets/
- https://www.sbimf.com/total-expense-ratio/
- https://www.sbimf.com/

#### Local corpus inventory (`docs/`)

Currently **10 PDFs** (KIM + SID for all 5 schemes). These cover **scheme KIM/SID** only. Factsheets, TER/charges pages, riskometer/benchmark notes, FAQs, and statement/tax-doc guides are **not yet in `docs/`**.

| Category (problem statement) | In `docs/`? | Files |
| --- | --- | --- |
| Scheme KIM | Yes (5) | `kim---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf`, `kim---sbi-flexicap-fund.pdf`, `kim---sbi-elss-tax-saver-fund-(formerly-known-as-sbi-long-term-equity-fund).pdf`, `kim---sbi-contra-fund.pdf`, `kim---sbi-small-cap-fund.pdf` |
| Scheme SID | Yes (5) | `sid---sbi-large-cap-fund-(formerly-known-as-bluechip-fund).pdf`, `sid---sbi-flexicap-fund.pdf`, `sid---sbi-elss-tax-saver-fund.pdf`, `sid---sbi-contra-fund.pdf`, `sid---sbi-small-cap-fund.pdf` |
| Scheme factsheet pages | No | Download from https://www.sbimf.com/factsheets/ (target: 5 scheme factsheets) |
| Scheme fee/charges and exit/transaction-related pages | No | Use KIM/SID plus https://www.sbimf.com/total-expense-ratio/; add any dedicated charges pages |
| Benchmark and riskometer/portfolio risk notes | No | Usually on factsheets and/or SID; add AMFI/SEBI riskometer notes if needed |
| Scheme FAQs / capital-gains / tax-document resources | No | Collect official SBI / AMFI / SEBI investor pages |
| Statement-download or tax-document guidance | No | Collect official SBI investor-service pages |

**Count toward 15–25 sources:** 10 local KIM/SID PDFs (cite the official SID/KIM URLs, not local paths) + remaining pages still to collect (factsheets, TER, riskometer/benchmark, FAQs, statement/tax guides) to reach 15–25.

**Note:** Local small-cap files are named **SBI Small Cap Fund**. The Groww scheme list includes `sbi-small-midcap-fund-direct-growth`. Confirm these refer to the same scheme before ingesting.

### 2. FAQ assistant (working prototype)

The prototype should answer factual queries only, such as:

- “Expense ratio of ?”
- “ELSS lock-in?”
- “Minimum SIP?”
- “Exit load?”
- “Riskometer/benchmark?”
- “How to download capital-gains statement?”

### 3. Refusal handling

The assistant must refuse non-factual or advisory queries, such as:

- No investment advice
- No “should buy/sell” recommendations
- No personal suitability guidance
- No calculation of returns or comparative analytics across schemes

Refusal responses should:

- Be polite and clearly worded
- Reinforce the facts-only limitation
- Provide a relevant educational link (e.g., AMFI or SEBI resource)

### 4. User interface (minimal)

The solution should include a simple interface with:

- A welcome message
- Three example questions
- A visible disclaimer: **“Facts-only. No investment advice.”**

### 5. Constraints

#### Data and sources

- Use only official public sources (AMC, AMFI, SEBI)
- Do not use third-party blogs or aggregator websites

#### Privacy and security

Do not collect, store, or process:

- PAN or Aadhaar numbers
- Account numbers
- OTPs
- Email addresses or phone numbers

#### Content restrictions

- No investment advice or recommendations
- No performance comparisons or return calculations
- For performance-related queries, provide a link to the official factsheet only

#### Transparency

- Responses must be short, factual, and verifiable
- Every answer must include a source link and last updated date

### 6. Answer formatting and transparency

For every assistant response:

- Must be **≤ 3 sentences**
- Must include **“Last updated from sources: ”** and the current date (or the date official sources were last refreshed) after the answer
- Must include **at least one source link** (exactly one is preferred; at minimum, one clear citation)

### 7. Security, privacy, and compliance constraints

- Public sources only. No screenshots of the app back-end or other private systems as sources
- No third-party blogs as sources; use only official public pages
- No PII: do not accept, store, or process PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers
- Do not request or infer sensitive data
- Do not include or log user-identifying details

## What to submit (deliverables)

1. **Working prototype** link (app/notebook) or a **≤3-min demo video** if hosting isn’t possible
2. **Source list** (CSV/MD) containing the 15–25 URLs used in the corpus
3. **README** with:
   - Setup steps
   - Scope (AMC + selected schemes)
   - Known limits (what the assistant refuses to answer, citation policy, and any incomplete areas)
4. **Sample Q&A file** with 5–10 example queries, each with the assistant’s answers and the links used as citations
5. **Disclaimer snippet** used in the UI (must include: “Facts-only. No investment advice.”)

## Success criteria

- Accurate retrieval of factual mutual fund information
- Strict adherence to facts-only responses (no advice, no speculation)
- Consistent inclusion of valid source citations for factual answers
- Proper refusal of advisory queries (e.g., “Should I buy/sell?”) with a facts-only message and a relevant educational link
- Clean, minimal, and user-friendly interface

## Summary (trustworthiness and compliance)

The goal is to build a trustworthy, transparent, and compliant mutual fund FAQ assistant that **prioritizes accuracy over intelligence**. The system should ensure that users receive only verified, source-backed financial information, without any advisory bias or speculative content.
