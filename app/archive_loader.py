"""Travel Monthly archive loader. Reads archive_issues.yaml at startup.

Each issue: { year, month, issue_no?, status, opener, headlines[] }
Headlines: { title, source_slug, section?, regions[]?, capital_signal? }

Source slugs are joined to the live Source table at render time so brand,
tier, and homepage_url all stay current.
"""
import yaml
from pathlib import Path
from datetime import date
from calendar import month_name

_ROOT = Path(__file__).resolve().parent.parent
_YAML = _ROOT / "archive_issues.yaml"

_issues_cache: list[dict] | None = None


def _load() -> list[dict]:
    global _issues_cache
    if _issues_cache is None:
        with open(_YAML) as f:
            data = yaml.safe_load(f) or []
        _issues_cache = sorted(
            data,
            key=lambda x: (x["year"], x["month"]),
        )
    return _issues_cache


def all_issues() -> list[dict]:
    """All issues, oldest first."""
    return _load()


def issue(year: int, month: int) -> dict | None:
    for it in _load():
        if it["year"] == year and it["month"] == month:
            return it
    return None


def timeline_months() -> list[dict]:
    """Build the full timeline from earliest issue → today, one entry per
    calendar month. Each entry: { year, month, label, status, issue_no?, has_data }.
    Months that fall before our archive starts get filled in too (none currently)."""
    issues = _load()
    if not issues:
        return []
    # Range = first issue → today
    first = issues[0]
    today = date.today()
    by_key = {(it["year"], it["month"]): it for it in issues}

    out = []
    y, m = first["year"], first["month"]
    while (y, m) <= (today.year, today.month):
        it = by_key.get((y, m))
        out.append({
            "year": y,
            "month": m,
            "label": month_name[m][:3].lower(),
            "month_full": month_name[m],
            "status": it["status"] if it else "missing",
            "issue_no": it.get("issue_no") if it else None,
            "has_data": it is not None,
            "is_current": (y == today.year and m == today.month),
        })
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def grouped_timeline() -> list[tuple[int, list[dict]]]:
    """Timeline grouped by year, newest year first, months newest first within."""
    months = timeline_months()
    by_year: dict[int, list[dict]] = {}
    for m in months:
        by_year.setdefault(m["year"], []).append(m)
    years_desc = sorted(by_year.keys(), reverse=True)
    for y in years_desc:
        by_year[y].sort(key=lambda m: m["month"], reverse=True)
    return [(y, by_year[y]) for y in years_desc]
