from datetime import datetime, timezone
from app.extensions import db
from app.models import Article


# Weights tuned to the citation pattern in Ned's 14-issue actual archive
# (Skift + PhocusWire = 44% of stories; M&A/capital = 38%; APAC > MENA > Europe).
SOURCE_TIER_WEIGHTS = {1: 25, 2: 18, 3: 10}

THEME_VALUES = {
    "consolidation": 10, "commission-warfare": 9, "funding": 9,
    "tech-disruption": 7, "competitive-dynamics": 6, "asian-expansion": 6,
    "partnership": 5, "regulatory-pressure": 5, "new-product": 4, "executive-move": 4,
}

# Ned's region split: global 54 / apac 22 / europe 14 / na 13 / mena 10 / sa 8.
# Wego's BD lens skews mena/apac/sa, so weighted up — but europe + na get real weight too.
REGION_BOOSTS = {"mena": 8, "apac": 8, "south-asia": 7, "europe": 4, "north-america": 4, "global": 2}


def compute_score(article: Article) -> float:
    score = 0.0
    score += SOURCE_TIER_WEIGHTS.get(article.source.tier, 0)
    score += min(sum(THEME_VALUES.get(t, 0) for t in (article.themes or [])), 25)
    score += min(sum(REGION_BOOSTS.get(r, 0) for r in (article.regions or [])), 15)
    score += min(len(article.companies or []) * 5, 15)
    if article.capital_signal:
        score += 14  # 38% of Ned's archive — capital signal is a primary axis, not a side flag
    if article.published_at:
        age_days = max(0, (datetime.now(timezone.utc) - article.published_at).days)
        score += max(0.0, 10 - (age_days / 3))
    return round(score, 2)


def score_all() -> int:
    n = 0
    for article in Article.query.all():
        new_score = compute_score(article)
        if abs((article.score or 0) - new_score) > 0.01:
            article.score = new_score
            n += 1
    db.session.commit()
    print(f"Re-scored {n} articles")
    return n
