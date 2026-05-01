import re
from app.extensions import db
from app.models import Article, Company


_pattern_cache: dict[str, re.Pattern] = {}


def build_patterns():
    global _pattern_cache
    _pattern_cache = {}
    for c in Company.query.all():
        terms = [c.name] + (c.aliases or [])
        escaped = [re.escape(t) for t in terms if t]
        if not escaped:
            continue
        pattern = r"\b(?:" + "|".join(escaped) + r")\b"
        _pattern_cache[c.name] = re.compile(pattern, re.IGNORECASE)


def match_companies_one(article: Article) -> list[str]:
    if not _pattern_cache:
        build_patterns()
    haystack = f"{article.title or ''}  {article.summary or ''}"
    matches = []
    for company_name, pattern in _pattern_cache.items():
        if pattern.search(haystack):
            matches.append(company_name)
    return matches


def match_companies_all() -> int:
    build_patterns()
    n = 0
    for article in Article.query.all():
        matches = match_companies_one(article)
        if matches != (article.companies or []):
            article.companies = matches
            n += 1
    db.session.commit()
    print(f"Companies updated for {n} articles")
    return n
