from flask import Blueprint, render_template, request
from sqlalchemy import func
from app.extensions import db
from app.models import Source, Article

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    sources = Source.query.filter_by(active=True).order_by(Source.tier, Source.name).all()
    return render_template("index.html", sources=sources, request_args=request.args)


@bp.route("/methodology")
def methodology():
    return render_template("methodology.html")


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
