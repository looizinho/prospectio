# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

**Prospectio** is a Python CLI automation system for B2B lead generation and outreach. It runs a 4-stage pipeline: collect leads from Google Maps → qualify them with Codex AI → approve via interactive terminal UI → send personalized emails via Gmail. Intended for self-hosted deployment on a Raspberry Pi 4B 8GB.

The `prospector.py` entry point is the only CLI interface. All stages write to local JSON files in `data/`.

## Stack

- **Runtime:** Python 3.12.13 (managed via `mise`)
- **AI:** Anthropic SDK — `Codex-sonnet-4-20250514` for lead scoring and email generation
- **Scraping:** Playwright (Chromium, async) for Google Maps automation
- **UI:** Rich library for terminal panels, tables, and progress bars
- **Email:** Gmail SMTP with App Password (port 465, SSL)
- **Data:** Local JSON files (no database)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # then fill in credentials
```

Required `.env` vars: `ANTHROPIC_API_KEY`, `EMAIL_REMETENTE`, `EMAIL_SENHA_APP`, `EMAIL_NOME_REMETENTE`.

## CLI Commands

```bash
python prospector.py status          # Dashboard with counts per pipeline stage
python prospector.py coletar         # Scrape Google Maps (random query or --query "..." --max N)
python prospector.py triar           # AI-score pending leads (QUENTE/MORNO/FRIO)
python prospector.py aprovar         # Interactive terminal approval UI
python prospector.py enviar          # Generate + send personalized emails (--dry-run to preview)
python prospector.py email_teste     # Validate SMTP config by sending a test email
python prospector.py listar          # Show all approved leads in a table
python prospector.py pipeline        # Run all stages end-to-end
```

## Architecture

### Data Flow

```
leads_raw.json (status=pendente)
  → triagem.py → leads_triados.json (scored, status=triado)
    → aprovacao.py → leads_aprovados.json (status_aprovacao=aprovado)
      → email_sender.py → leads_aprovados.json (status_envio=enviado)
```

Each stage reads its input file and updates statuses in-place. Deduplication in `scraper.py` is by business name (case-insensitive).

### Core Modules

- **`core/scraper.py`** — Playwright async scraper for Google Maps. Scrolls the results panel, clicks each card, extracts nome/categoria/endereco/telefone/website/rating. Entry point: `executar_coleta()`.

- **`core/triagem.py`** — Sends each lead to Codex with a hardcoded customer profile (`PERFIL_LUIZ`). Returns score 1-10, classificacao (QUENTE/MORNO/FRIO), justificativa, dor_provavel, abordagem_sugerida, and recomendacao. Entry point: `triar_leads_pendentes()`.

- **`core/aprovacao.py`** — Rich-based interactive UI. For each unreviewed lead shows AI analysis and prompts [S]im/[N]ão/[P]ular/[Q]uitar. Collects email address on approval. Entry point: `fluxo_aprovacao()`.

- **`core/email_sender.py`** — Asks Codex to generate assunto + corpo_html + corpo_texto per lead, previews in terminal, confirms before sending. Entry point: `processar_fila_envio()`.

### Key Design Constraints

- API calls in `triagem.py` are **sequential** — intentional, to respect Anthropic free-tier rate limits.
- Playwright runs **headless Chromium** — requires a display-capable environment or `--no-sandbox` on Raspberry Pi.
- Gmail requires an **App Password** (not the regular account password); standard 2FA must be enabled.
- Google Maps scraping: safe limit is ~10 queries/day to avoid detection.

## Planned (Not Yet Implemented)

- Node.js/pnpm web dashboard frontend
- Telegram approval bot
- LinkedIn/Instagram scrapers
- Cron scheduling daemon
