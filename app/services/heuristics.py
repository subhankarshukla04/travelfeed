"""Rule-based tagging — fast, free, no LLM needed.

Runs BEFORE the LLM tagger to populate confident sections/regions cheaply.
LLM tagging then only processes articles still missing tags, or refines.

Capital_signal is detected purely by regex — no LLM needed.
"""
import re
from datetime import datetime, timezone
from app.extensions import db
from app.models import Article


# Section keyword rules — first match wins.
SECTION_RULES = [
    ("M&A", [
        r"\bacqui(?:re|red|ring|sition)\b", r"\bmerger\b", r"\bbuyout\b",
        r"\bIPO\b", r"\binvestment round\b", r"\bSeries [A-E]\b",
        r"\braised \$\d", r"\bvaluation of \$\d", r"\b\$\d+(?:\.\d+)?[MB]n? (?:funding|round|deal)",
    ]),
    ("Executive", [
        r"\bappoints?\b", r"\b(?:names|named) (?:new |the new )?(?:CEO|CFO|COO|CTO|chairman|president)\b",
        r"\bsteps down\b", r"\bresigns?\b", r"\bdeparts?\b", r"\bjoins as\b",
        r"\b(?:chief executive|chief financial|chief operating) officer\b",
    ]),
    ("Regulatory", [
        r"\bregulator(?:s|y)?\b", r"\bcompetition authority\b", r"\bantitrust\b",
        r"\bDOJ\b", r"\bbanned?\b", r"\bfined?\b", r"\blawsuit\b", r"\bsettlement\b",
        r"\bcompliance\b", r"\bsanction(?:s|ed)\b", r"\bGDPR\b", r"\bDOT\b",
    ]),
    ("Airlines", [
        r"\bairlines?\b", r"\bflight(?:s)?\b", r"\baircraft\b", r"\baviation\b",
        r"\bcabin\b", r"\bairport\b", r"\broute(?:s)? (?:between|from|to)\b",
        r"\bBoeing\b", r"\bAirbus\b", r"\bATR\b", r"\bjet\b",
    ]),
    ("Hoteliers", [
        r"\bhotel(?:s|ier|iers)?\b", r"\bresort(?:s)?\b", r"\bbedbank\b",
        r"\boccupancy\b", r"\bRevPAR\b", r"\bADR\b", r"\bhospitality\b",
        r"\b(?:luxury|midscale|economy) (?:brand|chain|segment)\b",
    ]),
    ("Travel Tech", [
        r"\b(?:meta)?search\b", r"\bOTA\b", r"\bGDS\b", r"\bAPI\b",
        r"\bplatform\b", r"\bSaaS\b", r"\bbooking engine\b",
        r"\bpayment(?:s)?\b", r"\bdistribution\b",
    ]),
    ("Emerging", [
        r"\bblockchain\b", r"\bcrypto(?:currency)?\b", r"\bNFT\b",
        r"\bspace tour(?:ism|ist)\b", r"\b(?:AI|GenAI|LLM|generative AI)\b",
        r"\bvirtual reality\b", r"\bmetaverse\b",
    ]),
]


REGION_RULES = {
    "mena": [
        r"\b(?:UAE|Dubai|Abu Dhabi|Saudi(?: Arabia)?|Riyadh|Jeddah|Bahrain|Qatar|Doha|Oman|Muscat|Kuwait|Egypt|Cairo|Jordan|Amman|Lebanon|Beirut|Morocco|Casablanca|Tunisia|GCC|Middle East|MENA)\b",
        r"\b(?:Emirates Airlines|Etihad|Qatar Airways|flydubai|Saudia|Almosafer|Tajawal|Cleartrip)\b",
    ],
    "apac": [
        r"\b(?:Singapore|Bangkok|Thailand|Vietnam|Hanoi|Ho Chi Minh|Indonesia|Jakarta|Bali|Malaysia|Kuala Lumpur|Philippines|Manila|Hong Kong|Tokyo|Japan|Korea|Seoul|Taiwan|Taipei|China|Beijing|Shanghai|Asia[- ]Pacific|APAC|Southeast Asia)\b",
        r"\b(?:Singapore Airlines|Cathay Pacific|ANA|JAL|Korean Air|AirAsia|Lion Air|Garuda|Scoot|Trip\.com|Ctrip|Traveloka|Klook|Agoda)\b",
    ],
    "south-asia": [
        r"\b(?:India|Mumbai|Bangalore|Delhi|New Delhi|Hyderabad|Chennai|Bengaluru|Pakistan|Karachi|Lahore|Bangladesh|Dhaka|Sri Lanka|Colombo|Nepal|Bhutan)\b",
        r"\b(?:IndiGo|Air India|SpiceJet|Vistara|MakeMyTrip|EaseMyTrip|Yatra|Cleartrip|Goibibo|Ixigo)\b",
    ],
    "north-america": [
        r"\b(?:United States|U\.S\.|US |USA|American|Canada|Toronto|New York|San Francisco|Chicago|Texas|Florida|California|Mexico)\b",
        r"\b(?:United Airlines|Delta|Southwest|JetBlue|Air Canada|Alaska Airlines|Spirit|Frontier)\b",
    ],
    "europe": [
        r"\b(?:UK|United Kingdom|Britain|London|France|Paris|Germany|Berlin|Munich|Spain|Madrid|Barcelona|Italy|Rome|Milan|Netherlands|Amsterdam|Sweden|Stockholm|Norway|Switzerland|Zurich|Greece|Portugal|Ireland|Dublin|Europe|EU)\b",
        r"\b(?:British Airways|Lufthansa|Air France|KLM|Ryanair|easyJet|Wizz Air|TAP|Iberia)\b",
    ],
}


CAPITAL_SIGNAL_PATTERNS = [
    r"\bacqui(?:re|red|ring|sition|res)\b", r"\bmerger\b", r"\bbuyout\b",
    r"\bIPO\b", r"\bgoes? public\b", r"\b(?:Series |Round )[A-E]\b",
    r"\braised \$", r"\b\$\d+(?:\.\d+)?[MB]n?\s+(?:funding|round|deal|investment)\b",
    r"\bvaluation\b", r"\binvestor(?:s)?\b", r"\bventure capital\b",
    r"\bcommission(?:s)?\b", r"\bdistribution (?:economics|fee)\b",
    r"\bfundrais(?:e|ing)\b", r"\bequity\b", r"\bventure round\b",
    r"\b(?:pre-seed|seed|growth|late-stage) (?:round|funding)\b",
]


THEME_RULES = {
    "consolidation": [r"\bconsolidat", r"\bacquir", r"\bmerg", r"\brollup\b"],
    "competitive-dynamics": [r"\b(?:competit|rival|head[- ]to[- ]head|market share|gain(?:s|ed)? ground)\b"],
    "commission-warfare": [r"\bcommission(?:s)?\b", r"\bdistribution\b.{0,30}\b(?:cut|reduce|war)\b"],
    "tech-disruption": [r"\b(?:disrupt|automat|AI|machine learning|LLM)\b"],
    "regulatory-pressure": [r"\b(?:regulator|antitrust|fine|ban|lawsuit|sanction)\b"],
    "asian-expansion": [r"\b(?:expand|launch|entry|enter)\b.{0,40}\b(?:Asia|APAC|India|Singapore|China|Indonesia|Vietnam|Japan)\b"],
    "new-product": [r"\b(?:launches?|unveils?|introduces?|debuts?)\b.{0,40}\b(?:product|platform|service|app|tool|feature)\b"],
    "funding": [r"\b(?:raised|funding|round|invest|valuation|IPO|Series [A-E])\b"],
    "executive-move": [r"\b(?:appointed|hires|joins|steps down|resigns|departs|new (?:CEO|CFO|COO|CTO|chairman))\b"],
    "partnership": [r"\b(?:partner(?:s|ed|ship)|collaborat|alliance|joint venture|teams up with)\b"],
}


# Compile all patterns once
_compiled_section = [
    (sec, [re.compile(p, re.IGNORECASE) for p in patterns])
    for sec, patterns in SECTION_RULES
]
_compiled_region = {
    region: [re.compile(p, re.IGNORECASE) for p in patterns]
    for region, patterns in REGION_RULES.items()
}
_compiled_capital = [re.compile(p, re.IGNORECASE) for p in CAPITAL_SIGNAL_PATTERNS]
_compiled_theme = {
    theme: [re.compile(p, re.IGNORECASE) for p in patterns]
    for theme, patterns in THEME_RULES.items()
}


def detect_section(text: str) -> str:
    """First-match-wins section detection. Defaults to 'Travel Tech' if no clear match."""
    for section, patterns in _compiled_section:
        if any(p.search(text) for p in patterns):
            return section
    return "Travel Tech"


def detect_regions(text: str) -> list[str]:
    return [region for region, patterns in _compiled_region.items()
            if any(p.search(text) for p in patterns)]


def detect_capital_signal(text: str) -> bool:
    return any(p.search(text) for p in _compiled_capital)


def detect_themes(text: str) -> list[str]:
    return [theme for theme, patterns in _compiled_theme.items()
            if any(p.search(text) for p in patterns)]


def heuristic_tag_one(article: Article) -> bool:
    haystack = f"{article.title or ''}  {article.summary or ''}"
    if not haystack.strip():
        return False
    article.section = detect_section(haystack)
    article.regions = detect_regions(haystack) or ["global"]
    article.themes = detect_themes(haystack)
    article.capital_signal = detect_capital_signal(haystack)
    article.tagged_at = datetime.now(timezone.utc)
    return True


def heuristic_tag_all(only_untagged: bool = True) -> int:
    query = Article.query
    if only_untagged:
        query = query.filter(Article.tagged_at.is_(None))
    n = 0
    for article in query.all():
        if heuristic_tag_one(article):
            n += 1
            if n % 50 == 0:
                db.session.commit()
    db.session.commit()
    print(f"Heuristic-tagged: {n}")
    return n
