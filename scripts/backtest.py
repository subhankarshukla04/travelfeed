"""Backtest scoring against Nedyalko's past Travel Monthly issues.

Usage:
    python scripts/backtest.py backtest/issue_2025_03.txt backtest/issue_2025_04.txt

Each input file is a list of cited URLs, one per line.
"""
import sys
from urllib.parse import urlparse
from app import create_app
from app.models import Article


def url_stem(url: str) -> str:
    p = urlparse(url)
    return f"{p.netloc}{p.path}".rstrip("/").lower()


app = create_app()

with app.app_context():
    cited = []
    for path in sys.argv[1:]:
        with open(path) as f:
            cited.extend([u.strip() for u in f if u.strip().startswith("http")])

    cited_stems = set(url_stem(u) for u in cited)
    print(f"Cited URLs: {len(cited)} ({len(cited_stems)} unique stems)")

    db_stems = {url_stem(a.url) for a in Article.query.all()}
    in_db = cited_stems & db_stems
    print(f"Cited URLs found in DB: {len(in_db)} / {len(cited_stems)}")

    top100 = (
        Article.query.filter(Article.tagged_at.isnot(None))
        .order_by(Article.score.desc())
        .limit(100)
        .all()
    )
    top100_stems = {url_stem(a.url) for a in top100}

    in_top100 = cited_stems & top100_stems
    if cited_stems:
        recall = len(in_top100) / len(cited_stems)
        print(f"Recall@100: {recall:.0%} ({len(in_top100)}/{len(cited_stems)})")

    cited_domains = set(urlparse(u).netloc for u in cited)
    print(f"Cited URL domains: {len(cited_domains)}")
    for d in sorted(cited_domains):
        print(f"  {d}")
