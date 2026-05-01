"""Travel-relevance filter — keeps the feed focused on actual travel stories.

Tier-1 travel-specific sources (Skift, Phocuswire, WiT, TDM, Simple Flying)
are auto-relevant. Other sources must mention travel keywords or a
tracked travel company in title/summary.
"""
import re

TRAVEL_KEYWORD_PATTERN = re.compile(
    r"\b("
    r"travel(?:s|ing|ler|lers)?|tourism|tourist(?:s)?|hospitality|aviation|"
    r"airline(?:s)?|airport(?:s)?|airfare|flight(?:s)?|aircraft|"
    r"hotel(?:s|ier|iers)?|resort(?:s)?|lodging|accommodation(?:s)?|"
    r"booking(?:s|\.com)?|reservation(?:s)?|OTA|metasearch|"
    r"trip(?:s)?|vacation(?:s)?|destination(?:s)?|cruise(?:s)?|"
    r"luxury travel|business travel|leisure travel|"
    r"Boeing|Airbus|GDS|Sabre|Amadeus|Travelport|"
    r"check[- ]in|boarding pass|baggage|cabin crew|loyalty programme|frequent flyer"
    r")\b",
    re.IGNORECASE,
)

# Tier-1 sources are pre-filtered (the publication itself is travel-only)
AUTO_RELEVANT_SLUGS = {
    "skift", "phocuswire", "webintravel", "traveldailymedia",
    "simpleflying", "techcrunch-travel", "bloomberg-travel",
    "reuters-travel", "cnbc-travel", "gulf-news", "zawya",
    "thenational", "economictimes",
}


def is_travel_relevant(source_slug: str, title: str, summary: str, has_company_match: bool) -> bool:
    if source_slug in AUTO_RELEVANT_SLUGS:
        # Even auto-relevant sources need at least a travel keyword OR company match
        # to filter out Google-News-RSS query bleed-through (e.g., "Bloomberg site:bloomberg.com (travel OR ...)" still returns occasional misses)
        haystack = f"{title or ''}  {summary or ''}"
        if TRAVEL_KEYWORD_PATTERN.search(haystack) or has_company_match:
            return True
        # For tier-1 trade press, trust the source even without explicit keyword
        if source_slug in {"skift", "phocuswire", "webintravel", "traveldailymedia", "simpleflying"}:
            return True
        return False

    # Non-listed sources (e.g., generic TechCrunch): need explicit travel signal
    haystack = f"{title or ''}  {summary or ''}"
    return bool(TRAVEL_KEYWORD_PATTERN.search(haystack)) or has_company_match
