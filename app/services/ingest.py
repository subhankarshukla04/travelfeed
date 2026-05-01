import feedparser
import requests
from datetime import datetime, timezone
from time import mktime
from dateutil import parser as dateparser
from bs4 import BeautifulSoup
from app.extensions import db
from app.models import Source, Article
from app.services.relevance import is_travel_relevant
from app.services.companies import match_companies_one

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 12


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)[:2000]


def _clean_title(title: str, source_name: str) -> str:
    """Strip ' - PublisherName' / ' | PublisherName' / ' - CoStar' tail Google News appends.
    Strip leading 'News | ' / 'Article | ' breadcrumbs from CoStar/etc."""
    if not title:
        return ""
    t = title.strip()
    # Strip leading "News | " / "Article | " breadcrumb
    for prefix in ("News | ", "Article | ", "NEWS | "):
        if t.startswith(prefix):
            t = t[len(prefix):]
    # Strip trailing " - <publisher>"
    for sep in (" - ", " | ", " — ", " – "):
        if sep in t:
            head, _, tail = t.rpartition(sep)
            if head and len(tail) <= 60 and any(ch.isalpha() for ch in tail):
                t = head
                break
    return t.strip()[:500]


def _parse_date(entry):
    if entry.get("published_parsed"):
        return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
    if entry.get("updated_parsed"):
        return datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
    for key in ("published", "updated", "pubDate"):
        if entry.get(key):
            try:
                dt = dateparser.parse(entry[key])
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return datetime.now(timezone.utc)


def fetch_feed(rss_url: str) -> bytes:
    r = requests.get(rss_url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content


def ingest_source(source: Source) -> int:
    inserted = 0
    try:
        raw = fetch_feed(source.rss_url)
    except Exception as e:
        print(f"  fetch FAIL {source.slug}: {e}")
        return 0

    parsed = feedparser.parse(raw)
    if parsed.bozo and not parsed.entries:
        print(f"  parse FAIL {source.slug}: {parsed.bozo_exception}")
        return 0

    for entry in parsed.entries:
        url = entry.get("link")
        title = entry.get("title")
        if not url or not title:
            continue
        if Article.query.filter_by(url=url).first():
            continue
        try:
            tags = [t.term for t in entry.get("tags", [])] if entry.get("tags") else []
        except Exception:
            tags = []
        clean_title = _clean_title(title, source.name)
        clean_summary = _strip_html(entry.get("summary", ""))
        article = Article(
            source_id=source.id,
            url=url,
            title=clean_title,
            summary=clean_summary,
            published_at=_parse_date(entry),
            raw_meta={"author": entry.get("author"), "tags": tags},
            travel_relevant=is_travel_relevant(
                source.slug, clean_title, clean_summary, has_company_match=False
            ),
        )
        db.session.add(article)
        inserted += 1

    source.last_fetched_at = datetime.now(timezone.utc)
    db.session.commit()
    print(f"  {source.slug}: +{inserted}")
    return inserted


def ingest_all() -> int:
    total = 0
    for src in Source.query.filter_by(active=True).all():
        if not src.rss_url:
            continue
        total += ingest_source(src)
    print(f"Ingest total: +{total}")
    return total
