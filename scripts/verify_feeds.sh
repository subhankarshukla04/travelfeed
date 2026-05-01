#!/usr/bin/env bash
# Verify all RSS feeds in sources.yaml are reachable and return valid feed XML.
# Usage: bash scripts/verify_feeds.sh

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

verify_feed() {
  feed_url="$1"
  feed_name="$2"
  http_status=$(curl -sS -o /tmp/feed_test.xml -w "%{http_code}" -A "$UA" -L --max-time 10 "$feed_url" 2>/dev/null)
  byte_size=$(wc -c < /tmp/feed_test.xml | tr -d ' ')
  if [ "$http_status" = "200" ] && [ "$byte_size" -gt 500 ]; then
    if grep -q -E '<rss|<feed|<atom' /tmp/feed_test.xml; then
      echo "PASS  $feed_name  ($byte_size bytes)"
    else
      echo "DEGRD $feed_name  ($byte_size bytes)"
    fi
  else
    echo "FAIL  $feed_name  (HTTP $http_status)"
  fi
}

# Parse sources.yaml URLs (rough — relies on yaml format we control)
python3 - <<'PYEOF'
import yaml
with open("sources.yaml") as f:
    data = yaml.safe_load(f)
for s in data:
    print(f"{s['rss_url']}\t{s['name']}")
PYEOF
