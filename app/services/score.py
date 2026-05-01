from datetime import datetime, timezone
from app.extensions import db
from app.models import Article


SOURCE_TIER_WEIGHTS = {1: 25, 2: 20, 3: 15, 4: 10, 5: 8, 6: 5}

THEME_VALUES = {
    "consolidation": 8, "competitive-dynamics": 6, "commission-warfare": 8,
    "tech-disruption": 7, "regulatory-pressure": 5, "asian-expansion": 6,
    "new-product": 4, "funding": 7, "executive-move": 4, "partnership": 6,
}

REGION_BOOSTS = {"mena": 8, "apac": 8, "south-asia": 6, "global": 2}


def compute_score(article: Article) -> float:
    score = 0.0
    score += SOURCE_TIER_WEIGHTS.get(article.source.tier, 0)
    score += min(sum(THEME_VALUES.get(t, 0) for t in (article.themes or [])), 25)
    score += min(sum(REGION_BOOSTS.get(r, 0) for r in (article.regions or [])), 15)
    score += min(len(article.companies or []) * 5, 15)
    if article.capital_signal:
        score += 10
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
