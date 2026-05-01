import json
import re
import time
from datetime import datetime, timezone
from openai import OpenAI
from flask import current_app
from app.extensions import db
from app.models import Article


VALID_SECTIONS = {
    "Travel Tech", "Airlines", "Hoteliers", "M&A",
    "Regulatory", "Emerging", "Executive", "Other",
}
VALID_REGIONS = {"mena", "apac", "south-asia", "north-america", "europe", "global"}
VALID_THEMES = {
    "consolidation", "competitive-dynamics", "commission-warfare", "tech-disruption",
    "regulatory-pressure", "asian-expansion", "new-product", "funding",
    "executive-move", "partnership",
}


def _client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=current_app.config["OPENROUTER_API_KEY"],
    )


PROMPT = """Article:
Title: {title}
Source: {source}
Summary: {summary}

Output JSON only, with this exact shape:
{{
  "section": "<one of: Travel Tech, Airlines, Hoteliers, M&A, Regulatory, Emerging, Executive, Other>",
  "regions": ["<zero or more of: mena, apac, south-asia, north-america, europe, global>"],
  "themes": ["<zero or more of: consolidation, competitive-dynamics, commission-warfare, tech-disruption, regulatory-pressure, asian-expansion, new-product, funding, executive-move, partnership>"],
  "capital_signal": <true/false: does the article reference funding, M&A, IPO, valuations, or commission/distribution economics?>
}}

Rules:
- Output JSON ONLY. No markdown fences. No commentary.
- "section" is exactly one value.
- Be conservative on themes — only tag if clearly applicable.
"""


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _validate(payload: dict) -> dict:
    section = payload.get("section", "Other")
    if section not in VALID_SECTIONS:
        section = "Other"
    regions = [r for r in (payload.get("regions") or []) if r in VALID_REGIONS]
    themes = [t for t in (payload.get("themes") or []) if t in VALID_THEMES]
    capital = bool(payload.get("capital_signal", False))
    return {"section": section, "regions": regions, "themes": themes, "capital_signal": capital}


def tag_one(article: Article) -> bool:
    client = _client()
    try:
        resp = client.chat.completions.create(
            model=current_app.config["LLM_MODEL"],
            messages=[
                {"role": "system", "content": "You tag travel-industry news. Output strict JSON only."},
                {"role": "user", "content": PROMPT.format(
                    title=article.title,
                    source=article.source.name,
                    summary=(article.summary or "")[:1500],
                )},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content
    except Exception as e:
        print(f"  LLM error on {article.id}: {e}")
        return False

    payload = _extract_json(raw)
    if not payload:
        print(f"  invalid JSON from LLM for {article.id}")
        return False

    clean = _validate(payload)
    article.section = clean["section"]
    article.regions = clean["regions"]
    article.themes = clean["themes"]
    article.capital_signal = clean["capital_signal"]
    article.tagged_at = datetime.now(timezone.utc)
    return True


def tag_untagged(limit: int = 200) -> int:
    pending = (
        Article.query.filter(Article.tagged_at.is_(None))
        .order_by(Article.published_at.desc())
        .limit(limit)
        .all()
    )
    n = 0
    for article in pending:
        if tag_one(article):
            n += 1
            if n % 10 == 0:
                db.session.commit()
                print(f"  ...committed {n}")
        time.sleep(0.2)  # gentle rate limit
    db.session.commit()
    print(f"Tagged: {n} / {len(pending)}")
    return n
