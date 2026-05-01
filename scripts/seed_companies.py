import yaml
from app import create_app
from app.extensions import db
from app.models import Company

app = create_app()

with app.app_context():
    with open("companies.yaml") as f:
        data = yaml.safe_load(f)

    for entry in data:
        existing = Company.query.filter_by(name=entry["name"]).first()
        if existing:
            existing.aliases = entry.get("aliases", [])
        else:
            db.session.add(Company(name=entry["name"], aliases=entry.get("aliases", [])))

    db.session.commit()
    print(f"Companies synced: {Company.query.count()} total")
