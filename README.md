# Voizgger

**Voice-to-Ledger for the Informal Economy** — built for the Meta AI Hackathon.

> A market trader speaks: *"I sell three bags of rice and one bag of beans for twenty thousand Naira. The customer paid fifteen thousand, and he still owes five thousand."*
> Voizgger returns a structured ledger, a debt-tracking SMS in the customer's language, a visual audit of the shelf — and a printable invoice. In seconds.

---

## The Problem

Over **1.8 billion people** work in the informal economy. In Nigeria alone, tens of millions of market traders run their businesses on memory and paper notebooks:

- **No records** → no credit history → no access to loans
- **Debts tracked in the head** → forgotten, disputed, lost income
- **Paper ledgers** → destroyed by rain, fire, or a misplaced bag

Existing bookkeeping apps fail here because they demand **typing, English literacy, and smartphone fluency** from people whose workflow is *talking*.

## The Insight

Traders already narrate every transaction out loud — to customers, apprentices, themselves. Voizgger captures that narration and turns it into accounting infrastructure. **Zero typing. Zero forms. Speak, and the ledger writes itself.**

## What It Does

| Capability | How it works |
|---|---|
| 🎙️ **Voice-to-Ledger** | A voice note in English, **Pidgin, Yorùbá, Hausa, or Igbo** is transcribed by **Meta Muse Voice Transcribe** and parsed into items, quantities, amounts paid, and debts owed |
| 🌍 **Instant Translation** | The transcript, summary, and follow-up SMS switch between the 5 languages in one tap — the ledger stays accurate while communication stays local |
| 🧠 **Deep Audit Mode** | A `reasoning_effort` toggle escalates Muse Spark to high-effort reasoning for complex debts (conditional payments, discounts, partial settlements) |
| 🛡️ **Confidence Ledger** | Every extraction carries an AI confidence score; items below 80% are flagged amber — **the AI assists, the trader decides** |
| 📷 **Visual Stock Audit** | Snap a photo of the shelf — the vision model counts remaining stock and cross-checks it against what the voice note claims was sold, catching errors and shrinkage |
| 🧾 **Auto-Invoices** | Every voice note becomes a printable/downloadable invoice with one tap |
| 🌙 **Dark Mode** | Built for real-world use, day or night in the market |

## Why It Wins

Voizgger is not a demo wrapper around an LLM. It is a **multimodal, agentic pipeline** engineered around the constraints of the people it serves:

1. **Impact** — digitizes the informal economy without changing a single habit; creates the credit histories that unlock microloans
2. **Meta AI depth** — ASR (code-switching across Nigerian languages), high-effort reasoning, vision-based audit: three distinct model capabilities composed into one product
3. **Trust engineering** — confidence scores and human-in-the-loop verification acknowledge that AI is not infallible
4. **Local context** — Pidgin/Yorùbá/Hausa/Igbo aren't a gimmick; they're the difference between adoption and abandonment

## Architecture

```
🎙️ Voice Note (any supported language)
        │
        ▼
┌─────────────────────┐     WAV (ffmpeg, 16kHz mono)
│  Muse Voice          │ ◄──────────────────────────
│  Transcribe (ASR)    │
└─────────┬───────────┘
          │ transcript
          ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Muse Spark          │ ──► │  Structured Ledger    │
│  (JSON extraction +  │     │  items · qty · paid   │
│   reasoning_effort)  │     │  owed · confidence    │
└─────────┬───────────┘     └──────────┬───────────┘
          │                            │
          ▼                            ▼
┌─────────────────────┐     ┌──────────────────────┐
│  Follow-up SMS       │     │  Printable Invoice    │
│  (in customer's      │     │  (auto-generated)     │
│   language)          │     └──────────────────────┘
└─────────────────────┘
          │
📷 Shelf Photo ──► ┌──────────────────────┐
                   │  Vision Stock Audit   │
                   │  count vs. claimed    │
                   │  sales → consistency  │
                   └──────────────────────┘
```

## Tech Stack

- **ASR** — Meta Muse Voice Transcribe
- **Reasoning & Extraction** — Meta Muse Spark (structured JSON, `reasoning_effort` control)
- **Visual Audit** — Meta vision model (stock counting & verification)
- **Backend** — FastAPI (Python 3.10+), ffmpeg audio pipeline
- **Frontend** — Vanilla HTML/CSS/JS (no build step, runs anywhere)
- **Persistence** — `localStorage` for invoices & preferences (hackathon scope; V2 → database + auth)

## Getting Started

### Prerequisites

- Python 3.10+
- **FFmpeg** on your PATH
  - Windows: [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/) → add `bin` to PATH
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

### Setup

```bash
git clone https://github.com/yourusername/voizgger.git
cd voizgger

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
MODEL_API_KEY=your_meta_api_key_here
```

Run:

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**

### Try it in 10 seconds

Click **Load Demo Data** — a complete transaction with translation, confidence flags, and invoice generation, no API key required.

## Project Structure

```
app/
├── main.py              # FastAPI entry
├── api/endpoints.py     # /analyze_voice · /translate · /verify_stock
├── core/config.py       # model & client config
└── services/meta_ai.py  # ASR → reasoning → translation → vision audit
templates/index.html     # single-page UI (Dashboard · Invoices · Customers)
static/
├── css/style.css        # design system, dark mode, print styles
└── js/app.js            # view routing, language switching, invoice store
```

## Roadmap

- [ ] **Customer CRM** — auto-built profiles, per-customer debt history, one-tap WhatsApp reminders, trust scores *(architecture ready — see the Customers tab)*
- [ ] **Offline-first PWA** — record voice notes with no connectivity, sync when back online
- [ ] **Credit scoring export** — anonymized transaction history → microloan eligibility reports for partner banks
- [ ] **Multi-user accounts** — traders + apprentices with role-based access

## Engineering Scope Note

Built under hackathon time constraints with a deliberate priority: **100% of effort on the core AI pipeline** (ASR, reasoning, visual audit) rather than breadth of CRUD screens. The data model and API surface are designed to scale into full invoicing and CRM without rework.

---

*Powered by Meta AI · Built with Muse & Vision models*
