"""
Claim-quality classifier.

Trained on the 25 fabrications + 22 speculative entries the previous archive audit
caught. Each rule encodes a pattern that turned out to be unreliable in hindsight.

Output:
  - confidence: "ok" | "low" | "drop"
  - flags: list of human-readable reasons
"""
import re
from typing import Iterable

# Patterns that produced false claims in the archive audit. The bar is intentionally
# conservative — false positives just show an "unverified" badge; they don't hide
# the article. Only egregious fabrications get "drop".

# 1) Specific dollar funding rounds for STILL-PRIVATE travel-tech companies.
#    Klook, Hopper, Sonder pre-bankruptcy etc. — these were the worst offenders
#    in the archive. Live press releases naming them with a specific size at a
#    specific valuation should be cross-checked, not trusted at face.
PRIVATE_TRAVEL_FIRMS = [
    "klook", "hopper", "sonder", "wego", "tajawal",
    "almosafer", "cleartrip", "easemytrip", "yatra",
    "tripactions", "navan", "selfbook", "duetto",
]

FUNDING_ROUND = re.compile(
    r"\b(series\s+[a-h]|pre-?ipo|secondary|spac|s-?1|drhp)\b.*?\$\d", re.I
)
DOLLAR_AT_VAL = re.compile(
    r"\$\d+(\.\d+)?\s*(b|bn|billion|m|mn|million)\b.*?\bvaluat", re.I
)

# 2) Specific AI/conversion-lift percentages — Booking, ChatGPT, Trip Planner etc.
#    The archive had a dozen "X% AI-mediated" claims none of which had a primary source.
AI_PERCENTAGE = re.compile(
    r"\b(ai|chatgpt|llm|operator|gpt|agent)\b.{0,60}?\b\d{1,2}\s*%", re.I
)

# 3) Forward-looking confident specifics — "Vision 2030 trajectory", "on track for",
#    "expected to reach", combined with a precise number. Aspirational, not factual.
FORWARD_CONFIDENT = re.compile(
    r"\b(on track for|trajectory|expected to (reach|hit)|to reach|target hit early)\b.{0,40}?\d", re.I
)

# 4) "Officially launches" or "completes acquisition" without a primary source —
#    these were the Etihad/Air Italy and Saudi PIF/Hawaiian fabrication families.
OFFICIAL_LAUNCH = re.compile(
    r"\b(officially launch(es|ed)|completes (the )?acquisition|merger close[ds]?|deal close[ds]?)\b", re.I
)

# 5) IPO/listing claims for companies that haven't IPO'd. Klook, Wego (pre-2024),
#    Hopper. If headline says "[private firm] IPOs / lists / files S-1" — flag.
IPO_LISTING = re.compile(
    r"\b(ipo|listing|s-?1|drhp|files? (final|with|for)|prices? (its )?(ipo|offering))\b", re.I
)

# 6) Wrong-aircraft / wrong-fleet claims. We saw "Boeing 737 MAX to Riyadh Air"
#    (RA flies 787-9) and "A330neo to Riyadh Air" (RA ordered A321neo). Detect
#    aircraft–airline pairings that contradict the public fleet record.
AIRCRAFT_FLEET_REGISTRY = {
    "riyadh air": {"boeing 787-9", "787-9", "787", "a321neo", "airbus a321"},
    # carrier name -> publicly known fleet types (whitelist). Pairings outside it = flag.
}
AIRCRAFT_MENTION = re.compile(
    r"\b(boeing\s*\d{3}-?\d?[a-z]?|airbus\s*a\d{3}(neo|xlr)?|a\d{3}(-\d{3})?)\b", re.I
)

# 7) Confused-event traps. "Saudi Olympic 2034" (it's FIFA 2034, not Olympic).
KNOWN_BAD_PAIRS = [
    (re.compile(r"saudi.{0,30}olympic.{0,30}2034", re.I), "Saudi 2034 is FIFA WC, not Olympics"),
    (re.compile(r"klook\s+ipo", re.I), "Klook still private (as of cutoff)"),
    (re.compile(r"jetblue.{0,40}spirit.{0,30}(close|completes|merger)", re.I), "DOJ blocked JetBlue/Spirit; no close"),
    (re.compile(r"openai\s+atlas\s+browser", re.I), "OpenAI product is Operator, not Atlas"),
]

# 8) Sycophantic / self-promotional patterns (NUS NOC, BD pipeline, etc.) —
#    obvious tells in the archive that we don't want resurfacing in live data.
SYCOPHANTIC = re.compile(r"\b(nus noc|interns? join|BD pipeline)\b", re.I)


def classify(title: str, summary: str | None = None,
             companies: Iterable[str] | None = None) -> tuple[str, list[str]]:
    """Return (confidence, flags).

    confidence: 'ok' (no flag), 'low' (one or more soft flags), 'drop' (hard reject).
    flags: machine-readable reason codes for surfacing in UI.
    """
    text = f"{title or ''} {summary or ''}"
    lower = text.lower()
    flags: list[str] = []
    drop = False

    # Hard rejects first
    if SYCOPHANTIC.search(lower):
        return "drop", ["sycophantic-self-reference"]
    for pat, reason in KNOWN_BAD_PAIRS:
        if pat.search(lower):
            flags.append(f"known-bad: {reason}")
            drop = True

    # Soft flags
    has_private = any(c in lower for c in PRIVATE_TRAVEL_FIRMS)
    if has_private and (FUNDING_ROUND.search(text) or DOLLAR_AT_VAL.search(text)):
        flags.append("private-firm-funding-specifics")

    if has_private and IPO_LISTING.search(text):
        flags.append("private-firm-ipo-claim")

    if AI_PERCENTAGE.search(text):
        flags.append("ai-percentage-unverified")

    if FORWARD_CONFIDENT.search(text):
        flags.append("forward-aspirational")

    if OFFICIAL_LAUNCH.search(text) and "press release" not in lower and "according to" not in lower:
        flags.append("official-event-needs-source")

    # Aircraft-fleet contradiction check
    for carrier, fleet in AIRCRAFT_FLEET_REGISTRY.items():
        if carrier in lower:
            mentioned = AIRCRAFT_MENTION.findall(text)
            for m in mentioned:
                token = m[0] if isinstance(m, tuple) else m
                token = token.lower().replace(" ", "")
                # crude normalised compare
                if not any(f.replace(" ", "").replace("-", "") in token.replace("-", "") for f in fleet):
                    flags.append(f"fleet-mismatch:{carrier}")
                    break

    if drop:
        return "drop", flags
    if flags:
        return "low", flags
    return "ok", []
