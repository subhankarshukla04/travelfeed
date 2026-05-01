from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, render_template, jsonify
from sqlalchemy import or_
from app.models import Article, Source

bp = Blueprint("api", __name__)


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


def _query_from_request():
    section = request.args.get("section")
    region = request.args.get("region")
    source_slug = request.args.get("source")
    q = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "score")
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = min(100, max(1, int(request.args.get("per_page", 30) or 30)))

    now = datetime.now(timezone.utc)
    date_from = _parse_date(request.args.get("from"), now - timedelta(days=30))
    date_to = _parse_date(request.args.get("to"), now)

    query = Article.query.join(Source).filter(
        Article.published_at.between(date_from, date_to),
        Article.tagged_at.isnot(None),
    )
    if section:
        query = query.filter(Article.section == section)
    if region:
        query = query.filter(Article.regions.any(region))
    if source_slug:
        query = query.filter(Source.slug == source_slug)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Article.title.ilike(like), Article.summary.ilike(like)))

    if sort == "date":
        query = query.order_by(Article.published_at.desc())
    else:
        query = query.order_by(Article.score.desc(), Article.published_at.desc())

    return query.paginate(page=page, per_page=per_page, error_out=False)


@bp.route("/feed")
def feed():
    pagination = _query_from_request()
    if request.headers.get("HX-Request") or "text/html" in request.headers.get("Accept", ""):
        return render_template("_article_list.html", articles=pagination.items, pagination=pagination)
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
            for a in pagination.items
        ],
        "page": pagination.page,
        "pages": pagination.pages,
    })


@bp.route("/health")
def health():
    return jsonify(ok=True)
