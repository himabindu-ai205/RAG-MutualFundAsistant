# Google Stitch prompt — Phase 4 UI

Paste the **Primary prompt** into [Google Stitch](https://stitch.withgoogle.com). Then use the follow-ups if you need extra states. Export HTML/CSS (not a screenshot-only mock) into `ui/` and wire it to FastAPI as described in [`implementation-plan.md`](./implementation-plan.md) Phase 4.

**Do not use Streamlit.** This prompt is the source of truth for the Phase 4 frontend.

---

## Primary prompt (paste this)

```text
Design a production-ready, single-purpose web UI for a facts-only Mutual Fund FAQ Assistant. This is NOT a trading app, NOT a dashboard, NOT Streamlit, and NOT a chatbot with avatars or bubbles filling the screen.

Product
- Name: SBI Mutual Fund FAQ Assistant
- Audience: retail investors asking objective scheme facts
- Backend already exists: FastAPI POST /chat with JSON { "question": "..." } only
- Answers are ≤3 sentences, one source URL, and a last-updated date
- Primary cited sources are Groww scheme pages; SBI KIM/SID are supporting corpus only

Must-have first-paint layout (desktop 1440×900, then match on mobile 390)
Keep it one screen. Everything below must be visible without scrolling on a normal laptop viewport (1366×768 and up). Compact vertical rhythm. No hero image, no illustration, no stock photos.

1. Header
   - Title: SBI Mutual Fund FAQ Assistant
   - Subtitle: Facts from Groww scheme pages. SBI KIM/SID used as supporting corpus.
2. Persistent disclaimer banner (highest visual priority, never below the fold)
   - Exact text: Facts-only. No investment advice.
   - High-contrast, always visible, not a tiny footer, not a dismissible toast
3. Welcome (2 short lines max)
   - Welcome. Ask factual questions about five SBI schemes: Large Cap, Flexicap, ELSS Tax Saver, Contra, and Small Cap.
   - I retrieve published facts only. I will not recommend buys, compare funds, or calculate returns.
4. Three example question chips (clickable, equal width, wrap on mobile)
   - What is the expense ratio of SBI Large Cap Direct Growth?
   - What is the ELSS lock-in period for SBI ELSS Tax Saver?
   - What is the minimum SIP for SBI Flexicap Direct Growth?
5. Ask row
   - Single multiline text area, placeholder: Type a factual question about an in-scope SBI scheme…
   - Primary button labeled Ask
   - Helper text under the field: Only a question is sent. Do not enter PAN, Aadhaar, account numbers, OTP, email, or phone.
6. Answer panel (empty state on first paint)
   - Empty copy: Answers appear here. Each reply includes one source link and a last-updated date.
   - When filled, show these labeled blocks only:
     Answer (body text, ≤3 sentences)
     Source (one clickable https URL, never a file path)
     Last updated from sources: YYYY-MM-DD
     Small repeated disclaimer: Facts-only. No investment advice.

Visual style
- Calm, high-trust Indian fintech FAQ. Think official document + modern product, not Groww’s trading home, not a bank login.
- Background: warm off-white / paper (#F7F4EE)
- Surface: white cards, 12–16px radius, hairline border, very light shadow
- Text: near-black (#1A1A1A), secondary slate
- Accent: restrained teal-green for Ask and example chips (#0F766E)
- Disclaimer banner: amber/gold background (#F5E6B8) with dark text, left accent bar, lock or info icon — must feel like a compliance notice
- Typography: clean sans (Inter / Plus Jakarta Sans). Title 22–28px. Body 14–16px. Generous line-height.
- No charts, candlesticks, NAV graphs, portfolio rings, “Invest now”, “Buy”, star ratings, or return percentages in the chrome.
- No login, signup, KYC, PAN, email, phone, or profile icon.
- No sidebar navigation, no settings, no history drawer, no dark-mode toggle required.
- Accessibility: 4.5:1 contrast, visible focus rings, large tap targets (44px).

Interaction notes for the mock
- Clicking an example chip fills the textarea and looks ready to submit
- Ask button is the only primary CTA
- Source is a real-looking groww.in URL, e.g. https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth
- Do not invent extra form fields

Generate the desktop FAQ screen as the default, with a clean HTML/CSS export in mind (semantic header, main, form, and answer region).
```

---

## Follow-up prompts (optional extra screens)

Use these in the same Stitch project after the primary screen.

### Loading state

```text
Same layout as the FAQ home. User has submitted “What is the expense ratio of SBI Large Cap Direct Growth?”. Textarea shows that question. Ask button is disabled. Answer panel shows a compact skeleton or spinner with the copy: Retrieving facts from the closed corpus… Do not add extra pages or navigation.
```

### Factual answer state

```text
Same layout. Answer panel filled:
Answer: As published on the Groww scheme page for SBI Large Cap Direct Growth, the expense ratio / TER is the figure shown there for the Direct Growth plan. This assistant does not advise whether to invest.
Source: https://groww.in/mutual-funds/sbi-large-cap-direct-plan-growth
Last updated from sources: 2026-08-24
Disclaimer under the card: Facts-only. No investment advice.
Source must be a prominent text link, not a raw file path. Keep the disclaimer banner at the top still visible.
```

### Refusal state (advisory)

```text
Same layout. User asked “Should I buy SBI Contra Fund?”. Answer panel uses a distinct but calm treatment (not an error scream):
Answer: I cannot recommend whether you should buy or sell this fund. I only report published scheme facts. For investor education, see the AMFI investor resources.
Source: https://www.amfiindia.com/investor
Last updated from sources: 2026-08-24
Keep the top disclaimer banner. No buy/sell buttons.
```

### Empty question error

```text
Same layout. User clicked Ask with an empty field. Show a compact inline validation under the textarea: Please type a factual question. Do not add a PAN/email field. Answer panel stays in empty state.
```

### Mobile (390×844)

```text
Adapt the same FAQ screen to a mobile phone. Disclaimer still visible without scrolling. Example chips stack full width. Ask button full width under the textarea. Answer card below. No hamburger menu, no bottom tab bar, no login.
```

---

## After export

1. Download Stitch HTML/CSS (and any assets).
2. Place files under `ui/` as a **React (Vite)** app that ports the Stitch layout (see `stitch_sbi_mutual_fund_faq_assistant/` for the original HTML).
3. Build with `cd ui && npm run build`. FastAPI serves `ui/dist`; `Ask` must `POST /chat` with `{ "question": "..." }` only.
4. Map the JSON fields `answer`, `source`, `last_updated_from_sources`, `disclaimer` into the answer panel.
5. Confirm the eval UI checklist: disclaimer above the fold, three examples, no PII fields, clickable `https` source.
