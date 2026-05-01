from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
from flask import Flask
from app.config import Config
from app.extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    from app.routes.pages import bp as pages_bp
    from app.routes.api import bp as api_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    from app.cli import register_cli
    register_cli(app)

    @app.template_filter("humanize_date")
    def humanize_date(dt):
        if not dt:
            return ""
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        if delta.total_seconds() < 60:
            return "just now"
        if delta.total_seconds() < 3600:
            m = int(delta.total_seconds() // 60)
            return f"{m}m ago"
        if delta.total_seconds() < 86400:
            h = int(delta.total_seconds() // 3600)
            return f"{h}h ago"
        if delta.days < 7:
            return f"{delta.days}d ago"
        return dt.strftime("%b %d")

    @app.template_filter("archive_url")
    def archive_url(h, source=None):
        if isinstance(h, dict) and h.get("url"):
            return h["url"]
        title = h["title"] if isinstance(h, dict) else getattr(h, "title", "")
        src_name = source.name if source else ""
        q = f"{title} {src_name}".strip()
        return f"https://news.google.com/search?q={quote_plus(q)}"

    @app.template_filter("group_by_date")
    def group_by_date(articles):
        now = datetime.now(timezone.utc)
        today = now.date()
        groups = {"Today": [], "Yesterday": [], "This week": [], "Earlier": []}
        for a in articles:
            d = a.published_at.date() if a.published_at else today
            if d == today:
                groups["Today"].append(a)
            elif d == today - timedelta(days=1):
                groups["Yesterday"].append(a)
            elif (today - d).days < 7:
                groups["This week"].append(a)
            else:
                groups["Earlier"].append(a)
        return [(label, items) for label, items in groups.items() if items]

    with app.app_context():
        db.create_all()

    return app
