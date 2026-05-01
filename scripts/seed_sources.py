import yaml
from app import create_app
from app.extensions import db
from app.models import Source

app = create_app()

with app.app_context():
    with open("sources.yaml") as f:
        data = yaml.safe_load(f)

    for entry in data:
        existing = Source.query.filter_by(slug=entry["slug"]).first()
        if existing:
            for key in ("name", "tier", "region", "rss_url", "homepage_url"):
                if key in entry:
                    setattr(existing, key, entry[key])
            existing.active = True
        else:
            db.session.add(Source(**entry))

    db.session.commit()
    print(f"Sources synced: {Source.query.count()} total")
