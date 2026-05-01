# travelfeed

Travel-tech, airline, and hospitality news. Aggregated from trade press and regional sources, ranked by likely strategic relevance.

## What this is

A single-URL dashboard that ingests RSS feeds from 14 travel-industry sources (Skift, Phocuswire, WiT, Bloomberg, Reuters, CNBC, Gulf News, Zawya, The National, Economic Times, etc.), filters out non-travel noise, tags each article with section / region / theme, matches against a list of tracked travel companies, and scores for likely strategic relevance.

Built as the input layer for travel-tech competitive intelligence. The editorial layer (writing, curation) is left to the reader.

## Stack

- Flask 3 + Flask-SQLAlchemy
- PostgreSQL (Neon in production, local Postgres in dev)
- HTMX + Alpine.js + Tailwind (CDN)
- Heuristic regex tagger (free, instant, runs first)
- OpenRouter (Gemini Flash) for LLM tagger refinement
- Render Web + Render Cron Job for hosting

## Pipeline

```
RSS feeds  ──►  ingest  ──►  travel-relevance filter
                  │              │
                  ▼              ▼
             dedup by URL    drop non-travel
                                 │
                                 ▼
                        heuristic tag (free)
                                 │
                                 ▼
                        LLM tag refinement (optional)
                                 │
                                 ▼
                        company entity match
                                 │
                                 ▼
                            score
                                 │
                                 ▼
                        /api/feed (filtered + sorted)
```

## Score formula

```
score = source_tier_weight        (1–25)
      + theme_match               (0–25, capped)
      + region_boost              (0–15 — MENA/APAC weighted higher)
      + company_match             (0–15 — tracked travel co's)
      + capital_signal            (+10 if funding/M&A/commission topic)
      + recency_decay             (0–10, linear over 30 days)
```

## Local development

Requires Python 3.11+, local PostgreSQL.

```bash
make install                                  # venv + deps
createdb travelfeed_dev                       # one-time
cp .env.example .env                          # then edit with real values
make seed                                     # sources + companies
make refresh                                  # ingest + heuristic-tag + match + score
make dev                                      # http://localhost:5055
```

With LLM tagging (needs valid OPENROUTER_API_KEY):
```bash
make refresh-llm
```

## Common commands

```bash
make ingest        # fetch new RSS items
make heuristic     # rule-based tagging (free, instant)
make tag           # LLM tagging (needs API key)
make match         # entity match for companies
make score         # recompute scores
make relevance     # backfill travel_relevant flag
make stats         # print DB row counts
make dev           # boot local server
```

## Sources

14 feeds locked after Hour 0 RSS verification. See `sources.yaml`. Live counts and freshness at `/sources` once running.

| Tier | Sources |
|---|---|
| 1 (trade press) | Skift, Phocuswire, WiT, Travel Daily Media |
| 2 (tech + business) | TechCrunch, Bloomberg, Reuters |
| 3 (regional + aviation) | CNBC, Simple Flying, Gulf News, Zawya, The National, Economic Times |

## Deploy

`render.yaml` defines two services:
- Web: free tier (consider upgrading to Starter for instant cold-starts)
- Cron: Starter tier ($7/mo) — runs `flask refresh` every 4 hours

Push to GitHub, connect via Render Blueprint, set `DATABASE_URL` and `OPENROUTER_API_KEY` secrets in the dashboard.

## Architecture notes

- **Idempotent seeds.** Re-running `make seed` updates rather than duplicates.
- **Heuristic-first tagging.** Free regex pass populates section/region/theme/capital_signal before any LLM call. LLM tagger only refines what's left.
- **Strict enum validation.** Out-of-vocabulary tags from the LLM are dropped, never stored.
- **Travel-relevance gate.** Articles without travel keywords or tracked-company mentions are filtered out at ingest time.
- **Word-boundary entity match.** "Booking" matches "Booking.com" but not "booking the meeting."
- **Real User-Agent on every fetch.** Default Python UA gets blocked by Cloudflare on some sources.
- **Timezone-aware throughout.** All datetimes stored as `timestamp with time zone`.

## License & privacy

No analytics. No tracking. No accounts. No newsletter signup. Articles link straight out to source.

Built by Subhankar Shukla · subhankarshukla.vercel.app
