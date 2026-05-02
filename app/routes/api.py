from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, render_template, jsonify
from sqlalchemy import or_, func, case
from app.extensions import db
from app.models import Article, Source

bp = Blueprint("api", __name__)


WEGO_COMPETITORS = [
    "Almosafer", "Seera", "Tajawal", "Skyscanner", "Trip.com", "Traveloka",
    "Kayak", "Booking Holdings", "Booking.com", "Agoda", "Expedia",
    "MakeMyTrip", "ixigo", "Klook", "Hopper", "Tripadvisor",
]

LENSES = {
    "competitors": {"companies_any": ["Wego"] + WEGO_COMPETITORS},
    "capital":     {"sections": ["M&A"]},
    "demand":      {"sections": ["Hoteliers", "Airlines", "Emerging"]},
    "tech":        {"sections": ["Travel Tech"]},
}

DEFAULT_DAYS = 7
PRIMARY_REGIONS = ("mena", "apac", "south-asia", "global")

# For each window, the smaller "already-seen" window. Items inside the smaller
# window get pushed to the bottom of the bigger window's results so the user
# sees the new-to-this-window slice first.
WINDOW_TIERS = {1: None, 7: 1, 30: 7, 90: 30}


def _parse_date(s, default):
    if not s:
        return default
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return default


def _apply_lens(query, lens_key: str):
    spec = LENSES.get(lens_key)
    if not spec:
        return query
    if "sections" in spec:
        query = query.filter(Article.section.in_(spec["sections"]))
    if "companies_any" in spec:
        ors = [Article.companies.any(c) for c in spec["companies_any"]]
        query = query.filter(or_(*ors))
    return query


def _window_days() -> int:
    raw = request.args.get("days")
    if not raw:
        return DEFAULT_DAYS
    try:
        n = int(raw)
        return n if n in (1, 7, 30, 90) else DEFAULT_DAYS
    except ValueError:
        return DEFAULT_DAYS


def _query_from_request():
    lens = (request.args.get("lens") or "").strip()
    region = request.args.get("region")
    q = (request.args.get("q") or "").strip()

    now = datetime.now(timezone.utc)
    days = _window_days()
    smaller = WINDOW_TIERS.get(days)
    smaller_cutoff = (now - timedelta(days=smaller)) if smaller else None

    date_from = _parse_date(request.args.get("from"), now - timedelta(days=days))
    date_to = _parse_date(request.args.get("to"), now)

    query = Article.query.join(Source).filter(
        Article.published_at.between(date_from, date_to),
        Article.tagged_at.isnot(None),
        Article.travel_relevant.is_(True),
        Source.active.is_(True),
        Article.confidence != "drop",
    )
    query = _apply_lens(query, lens)
    if region:
        query = query.filter(Article.regions.any(region))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.summary.ilike(like)))

    if smaller_cutoff is not None:
        bucket = case((Article.published_at < smaller_cutoff, 0), else_=1)
        query = query.order_by(bucket.asc(), Article.score.desc(), Article.published_at.desc())
    else:
        query = query.order_by(Article.score.desc(), Article.published_at.desc())

    return query.all(), smaller_cutoff, smaller


@bp.route("/feed")
def feed():
    items, bucket_cutoff, smaller_days = _query_from_request()
    if request.headers.get("HX-Request") or "text/html" in request.headers.get("Accept", ""):
        return render_template(
            "_article_list.html",
            articles=items,
            bucket_cutoff=bucket_cutoff,
            bucket_smaller_days=smaller_days,
        )
    return jsonify({
        "items": [
            {
                "id": str(a.id),
                "title": a.title,
                "url": a.url,
                "source": a.source.name,
                "section": a.section,
                "regions": a.regions,
                "themes": a.themes,
                "companies": a.companies,
                "score": a.score,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in items
        ],
        "total": len(items),
    })


@bp.route("/health")
def health():
    return jsonify(ok=True)


@bp.route("/facets")
def facets():
    now = datetime.now(timezone.utc)
    days = _window_days()
    date_from = _parse_date(request.args.get("from"), now - timedelta(days=days))
    date_to = _parse_date(request.args.get("to"), now)

    base = Article.query.join(Source).filter(
        Article.published_at.between(date_from, date_to),
        Article.tagged_at.isnot(None),
        Article.travel_relevant.is_(True),
        Source.active.is_(True),
        Article.confidence != "drop",
    )

    lens_arg = (request.args.get("lens") or "").strip()
    region_arg = request.args.get("region")
    q = (request.args.get("q") or "").strip()

    def apply_other_filters(query, *, except_filter=None):
        if except_filter != "lens" and lens_arg:
            query = _apply_lens(query, lens_arg)
        if except_filter != "region" and region_arg:
            query = query.filter(Article.regions.any(region_arg))
        if q:
            like = f"%{q}%"
            query = query.filter(or_(Article.title.ilike(like), Article.summary.ilike(like)))
        return query

    total = apply_other_filters(base).count()

    lens_q = apply_other_filters(base, except_filter="lens")
    lens_counts = {}
    for key in LENSES:
        lens_counts[key] = _apply_lens(lens_q, key).count()

    region_q = apply_other_filters(base, except_filter="region")
    region_counts = {r: region_q.filter(Article.regions.any(r)).count() for r in PRIMARY_REGIONS}

    return jsonify({
        "total": total,
        "lenses": lens_counts,
        "regions": region_counts,
    })
