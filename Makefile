.PHONY: help install seed ingest tag heuristic score relevance refresh dev clean db-reset stats

help:
	@echo "travelfeed — common commands"
	@echo ""
	@echo "  make install        Create venv and install deps"
	@echo "  make seed           Seed sources + companies"
	@echo "  make ingest         Fetch new RSS items"
	@echo "  make heuristic      Heuristic-tag untagged articles (free, instant)"
	@echo "  make tag            LLM-tag untagged articles (needs OPENROUTER_API_KEY)"
	@echo "  make score          Recompute relevance scores"
	@echo "  make relevance      Backfill travel_relevant for existing articles"
	@echo "  make refresh        Full pipeline: ingest -> heuristic -> match -> score"
	@echo "  make refresh-llm    Full pipeline including LLM tagging step"
	@echo "  make dev            Run dev server on :5055"
	@echo "  make stats          Print article + tag stats"
	@echo "  make db-reset       DROP and recreate the local dev DB. Destructive."
	@echo "  make clean          Remove venv + caches"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

seed:
	. .venv/bin/activate && PYTHONPATH=. python scripts/seed_sources.py
	. .venv/bin/activate && PYTHONPATH=. python scripts/seed_companies.py

ingest:
	. .venv/bin/activate && flask ingest

heuristic:
	. .venv/bin/activate && flask heuristic-tag

tag:
	. .venv/bin/activate && flask tag --limit 200

score:
	. .venv/bin/activate && flask score

relevance:
	. .venv/bin/activate && flask backfill-relevance

match:
	. .venv/bin/activate && flask match-companies

refresh:
	. .venv/bin/activate && flask refresh

refresh-llm:
	. .venv/bin/activate && flask refresh --use-llm --limit 300

dev:
	. .venv/bin/activate && flask run --port 5055

stats:
	@psql travelfeed_dev -c "SELECT 'sources' AS table, COUNT(*) FROM sources UNION ALL SELECT 'companies', COUNT(*) FROM companies UNION ALL SELECT 'articles total', COUNT(*) FROM articles UNION ALL SELECT 'articles relevant', COUNT(*) FROM articles WHERE travel_relevant UNION ALL SELECT 'articles tagged', COUNT(*) FROM articles WHERE tagged_at IS NOT NULL;"

db-reset:
	@read -p "DROP local travelfeed_dev DB? [y/N] " ans && [ "$$ans" = "y" ]
	dropdb --if-exists travelfeed_dev
	createdb travelfeed_dev
	@echo "Local DB reset. Run 'make seed' next."

clean:
	rm -rf .venv __pycache__ app/__pycache__ app/*/__pycache__ scripts/__pycache__
