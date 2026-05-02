import json
from datetime import datetime, timezone, timedelta
from collections import Counter
from flask import Blueprint, render_template, request, abort
from sqlalchemy import func, or_
from app.extensions import db
from app.models import Source, Article
from app.archive_loader import all_issues, issue as get_issue, grouped_timeline, timeline_months
from app.routes.api import WEGO_COMPETITORS

bp = Blueprint("pages", __name__)


PINNED_COMPANIES = [
    "Wego", "Almosafer", "Seera", "Tajawal", "Riyadh Air",
    "MakeMyTrip", "ixigo", "IndiGo",
    "Klook", "Trip.com",
]


def _wego_watch(limit=5, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    targets = ["Wego"] + WEGO_COMPETITORS
    ors = [Article.companies.any(c) for c in targets]
    rows = (
        Article.query.join(Source)
        .filter(
            Article.travel_relevant.is_(True),
            Article.tagged_at.isnot(None),
            Article.published_at >= cutoff,
            Source.active.is_(True),
            or_(*ors),
        )
        .order_by(Article.score.desc(), Article.published_at.desc())
        .limit(limit)
        .all()
    )
    return rows


def _top_companies(limit=14, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        Article.query
        .filter(Article.travel_relevant.is_(True),
                Article.tagged_at.isnot(None),
                Article.published_at >= cutoff)
        .with_entities(Article.companies)
        .all()
    )
    counter = Counter()
    for (companies,) in rows:
        for c in (companies or []):
            counter[c] += 1

    pinned = [{"name": n, "n": counter.get(n, 0), "pinned": True} for n in PINNED_COMPANIES]
    seen = set(PINNED_COMPANIES)
    overflow = [
        {"name": n, "n": k, "pinned": False}
        for n, k in counter.most_common()
        if n not in seen
    ]
    return (pinned + overflow)[:limit]


def _top_themes(limit=10, days=30):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        Article.query
        .filter(Article.travel_relevant.is_(True),
                Article.tagged_at.isnot(None),
                Article.published_at >= cutoff)
        .with_entities(Article.themes)
        .all()
    )
    counter = Counter()
    for (themes,) in rows:
        for t in (themes or []):
            counter[t] += 1
    return [{"name": n, "n": k} for n, k in counter.most_common(limit)]


def _source_lookup() -> dict:
    return {s.slug: s for s in Source.query.all()}


def _render_shell(mode: str, archive: dict | None = None,
                  archive_grouped=None, prev_iss=None, next_iss=None):
    """Single page shell — used by /, /archive, /archive/<y>/<m>.
    Mode determines what fills the main article column."""
    sources = Source.query.filter_by(active=True).order_by(Source.tier, Source.name).all()
    sources_json = json.dumps([
        {"slug": s.slug, "name": s.name, "tier": s.tier, "region": s.region}
        for s in sources
    ])
    return render_template(
        "index.html",
        mode=mode,
        archive=archive,
        archive_grouped=archive_grouped,
        archive_sources=_source_lookup() if archive else {},
        prev_iss=prev_iss,
        next_iss=next_iss,
        all_issues=all_issues() if mode == "archive_index" else None,
        sources=sources,
        sources_json=sources_json,
        top_companies=_top_companies(),
        top_themes=_top_themes(),
        wego_watch=_wego_watch() if mode == "live" else [],
        request_args=request.args,
        timeline=grouped_timeline() if mode != "live" else [],
    )


@bp.route("/")
def index():
    return _render_shell(mode="live")


@bp.route("/archive")
def archive_index():
    return _render_shell(mode="archive_index")


@bp.route("/archive/<int:year>/<int:month>")
def archive_issue(year: int, month: int):
    iss = get_issue(year, month)
    if not iss:
        abort(404)

    section_order = ["M&A", "Travel Tech", "Airlines", "Hoteliers",
                     "Emerging", "Executive", "Regulatory"]
    grouped: dict[str, list] = {}
    for h in iss.get("headlines", []):
        sec = h.get("section") or "Travel Tech"
        grouped.setdefault(sec, []).append(h)
    grouped_ordered = [(sec, grouped[sec]) for sec in section_order if sec in grouped]

    timeline = grouped_timeline()
    flat_with_data = [m for _, months in timeline for m in months if m["has_data"]]
    flat_with_data.sort(key=lambda m: (m["year"], m["month"]))
    cur_idx = next((i for i, m in enumerate(flat_with_data)
                    if m["year"] == year and m["month"] == month), None)
    prev_iss = flat_with_data[cur_idx - 1] if cur_idx and cur_idx > 0 else None
    next_iss = flat_with_data[cur_idx + 1] if cur_idx is not None and cur_idx + 1 < len(flat_with_data) else None

    return _render_shell(
        mode="archive",
        archive=iss,
        archive_grouped=grouped_ordered,
        prev_iss=prev_iss,
        next_iss=next_iss,
    )


@bp.route("/methodology")
def methodology():
    return render_template("methodology.html")


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/sources")
def sources():
    rows = (
        db.session.query(
            Source.slug, Source.name, Source.tier, Source.region, Source.homepage_url,
            func.count(Article.id).label("n"),
            func.count(Article.id).filter(Article.travel_relevant.is_(True)).label("n_relevant"),
            func.max(Article.published_at).label("latest"),
        )
        .outerjoin(Article, Article.source_id == Source.id)
        .filter(Source.active.is_(True))
        .group_by(Source.id)
        .order_by(Source.tier, Source.name)
        .all()
    )
    return render_template("sources.html", rows=rows)
