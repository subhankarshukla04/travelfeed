import yaml
from app import create_app
from app.extensions import db
from app.models import Source

app = create_app()

with app.app_context():
    with open("sources.yaml") as f:
        data = yaml.safe_load(f)

    yaml_slugs = {entry["slug"] for entry in data}

    for entry in data:
        existing = Source.query.filter_by(slug=entry["slug"]).first()
        if existing:
            for key in ("name", "tier", "region", "rss_url", "homepage_url"):
                if key in entry:
                    setattr(existing, key, entry[key])
            existing.active = True
        else:
            db.session.add(Source(**entry))

    deactivated = 0
    for src in Source.query.all():
        if src.slug not in yaml_slugs and src.active:
            src.active = False
            deactivated += 1

    db.session.commit()
    active = Source.query.filter_by(active=True).count()
    print(f"Sources synced: {active} active, {deactivated} deactivated")
