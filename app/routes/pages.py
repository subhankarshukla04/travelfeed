from flask import Blueprint, render_template, request
from app.models import Source

bp = Blueprint("pages", __name__)


@bp.route("/")
def index():
    sources = Source.query.filter_by(active=True).order_by(Source.tier, Source.name).all()
    return render_template("index.html", sources=sources, request_args=request.args)
