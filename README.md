# travelfeed

Travel-tech, airline, and hospitality news. Aggregated from trade press and regional sources, ranked by likely strategic relevance.

## What this is

A single-URL dashboard that ingests RSS feeds from 14 travel-industry sources (Skift, Phocuswire, WiT, Bloomberg, Reuters, Gulf News, Zawya, Economic Times, etc.), tags each article with section / region / theme via an LLM, and scores it for partnership-relevance to a strategy reader.

Built as the input layer for travel-tech competitive intelligence. The editorial layer (writing, curation) is left to the reader.

## Stack

- Flask 3 + Flask-SQLAlchemy
- PostgreSQL (Neon)
- HTMX + Alpine.js + Tailwind (CDN)
- OpenRouter (Gemini Flash) for LLM tagging
- Render Web + Render Cron Job for hosting

## Methodology — how scoring works

Each article gets a 0–100 relevance score:

```
score = source_tier_weight        (1–25)
      + theme_match                (0–25, capped)
      + region_boost               (0–15, capped — MENA/APAC weighted higher)
      + company_match              (0–15, capped — tracked travel co's)
      + capital_signal_flag        (+10 if funding / M&A / commission topic)
      + recency_decay              (0–10, linear over 30 days)
```

Tagging uses a structured-JSON LLM prompt with strict enum validation; out-of-vocabulary section / region / theme values are dropped, never displayed.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your DATABASE_URL and OPENROUTER_API_KEY

python scripts/seed_sources.py
python scripts/seed_companies.py

flask ingest
flask tag --limit 100
flask match-companies
flask score

flask run
# Visit http://localhost:5000
```

Or in one shot:

```bash
flask refresh --limit 200
```

## Sources

Defined in `sources.yaml`. Currently 14 active feeds across global trade press, business press, MENA regional, APAC regional, and South Asia.

## Built by

Subhankar Shukla · subhankarshukla.vercel.app
