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
        return dt.strftime("%b %d")

    with app.app_context():
        db.create_all()

    return app
