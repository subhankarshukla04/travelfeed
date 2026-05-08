#!/usr/bin/env bash
set -euo pipefail

PROJECT="$HOME/Desktop/claude code/travelfeed"
LOG="$PROJECT/cron.log"

cd "$PROJECT"
set -a
source .env
set +a

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="
  ./.venv/bin/python -m flask refresh --use-llm --limit 200
} >> "$LOG" 2>&1
