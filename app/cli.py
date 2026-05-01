import click
from flask.cli import with_appcontext
from app.services.ingest import ingest_all
from app.services.tag import tag_untagged
from app.services.score import score_all
from app.services.companies import match_companies_all


def register_cli(app):
    @app.cli.command("ingest")
    @with_appcontext
    def ingest():
        """Fetch RSS feeds and store new articles."""
        ingest_all()

    @app.cli.command("tag")
    @click.option("--limit", default=200, type=int)
    @with_appcontext
    def tag(limit):
        """Run LLM tagging on untagged articles."""
        tag_untagged(limit=limit)

    @app.cli.command("match-companies")
    @with_appcontext
    def match_companies():
        """Run regex entity match for companies."""
        match_companies_all()

    @app.cli.command("score")
    @with_appcontext
    def score():
        """Compute relevance scores for all articles."""
        score_all()

    @app.cli.command("refresh")
    @click.option("--limit", default=200, type=int)
    @with_appcontext
    def refresh(limit):
        """Full pipeline: ingest -> tag -> match -> score."""
        ingest_all()
        tag_untagged(limit=limit)
        match_companies_all()
        score_all()
