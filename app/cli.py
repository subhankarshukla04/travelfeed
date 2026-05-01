import click
from flask.cli import with_appcontext
from app.services.ingest import ingest_all
from app.services.tag import tag_untagged
from app.services.score import score_all
from app.services.companies import match_companies_all
from app.services.heuristics import heuristic_tag_all


def register_cli(app):
    @app.cli.command("ingest")
    @with_appcontext
    def ingest():
        """Fetch RSS feeds and store new articles."""
        ingest_all()

    @app.cli.command("heuristic-tag")
    @click.option("--all", "tag_all", is_flag=True, help="Re-tag everything, not just untagged")
    @with_appcontext
    def heuristic_tag(tag_all):
        """Rule-based section/region/theme tagging — fast, free, no LLM."""
        heuristic_tag_all(only_untagged=not tag_all)

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

    @app.cli.command("backfill-relevance")
    @with_appcontext
    def backfill_relevance():
        """Re-evaluate travel_relevant for all existing articles."""
        from app.models import Article
        from app.extensions import db
        from app.services.relevance import is_travel_relevant
        n_changed = 0
        for a in Article.query.all():
            has_co = bool(a.companies)
            new_val = is_travel_relevant(a.source.slug, a.title, a.summary, has_co)
            if new_val != a.travel_relevant:
                a.travel_relevant = new_val
                n_changed += 1
        db.session.commit()
        print(f"travel_relevant updated for {n_changed} articles")

    @app.cli.command("refresh")
    @click.option("--limit", default=200, type=int)
    @click.option("--use-llm/--no-llm", default=False, help="Run LLM tagger after heuristic")
    @with_appcontext
    def refresh(limit, use_llm):
        """Full pipeline: ingest -> heuristic-tag -> [llm-tag] -> match -> score."""
        ingest_all()
        heuristic_tag_all(only_untagged=True)
        if use_llm:
            tag_untagged(limit=limit)
        match_companies_all()
        score_all()
