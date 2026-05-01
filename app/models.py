from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Source(db.Model):
    __tablename__ = "sources"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    tier = db.Column(db.Integer, nullable=False)
    region = db.Column(db.String, nullable=False)
    rss_url = db.Column(db.String)
    homepage_url = db.Column(db.String, nullable=False)
    active = db.Column(db.Boolean, default=True)
    last_fetched_at = db.Column(db.DateTime(timezone=True))


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = db.Column(UUID(as_uuid=True), db.ForeignKey("sources.id"), nullable=False, index=True)
    url = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    summary = db.Column(db.Text)
    published_at = db.Column(db.DateTime(timezone=True), index=True)
    fetched_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    score = db.Column(db.Float, default=0, index=True)
    section = db.Column(db.String, index=True)
    regions = db.Column(ARRAY(db.String), default=list)
    themes = db.Column(ARRAY(db.String), default=list)
    companies = db.Column(ARRAY(db.String), default=list)
    capital_signal = db.Column(db.Boolean, default=False)
    raw_meta = db.Column(JSONB)
    tagged_at = db.Column(db.DateTime(timezone=True))

    source = db.relationship("Source", backref="articles")


class Company(db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    aliases = db.Column(ARRAY(db.String), default=list)
