"""Reusable Data Quality calculations extracted from the SSi Query screen.

This module contains no Elasticsearch or AWS calls.  It is intended to be
called by the Daily Alerts orchestration code after the News and r/WSB
documents have been retrieved for a period.

Source code used for the extraction:
    GetCompositeSentiment/news_dq.py
    GetCompositeSentiment/reddit_dq.py

Confirmed Daily Alerts behaviour:
* News and r/WSB are scored independently.
* An eligible News host without a configured DQ score passes through at 1.0x.
* A News host outside ``eligible_news_hosts`` is filtered when that allow-list
  is supplied.
* r/WSB uses the Query-screen dead/normal/amplification zones unchanged.
* DQ changes effective buzz contribution; it does not modify sentiment.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union


# Default NewsAPI Top Headlines scores used by the Query screen.
DEFAULT_NEWS_DQ_SCORES: Dict[str, float] = {
    "ABC News": 0.8,
    "ABC News (AU)": 0.64,
    "Al Jazeera English": 0.8,
    "Ars Technica": 0.9,
    "Associated Press": 0.8,
    "Australian Financial Review": 0.8,
    "Axios": 0.8,
    "BBC News": 0.64,
    "BBC Sport": 0.48,
    "Bleacher Report": 0.6,
    "Bloomberg": 1.0,
    "Breitbart News": 0.8,
    "Business Insider": 1.0,
    "Business Insider (UK)": 0.8,
    "Buzzfeed": 0.6,
    "CBC News": 0.8,
    "CBS News": 0.8,
    "CNN": 0.8,
    "Crypto Coins News": 0.9,
    "Engadget": 0.9,
    "Entertainment Weekly": 0.6,
    "ESPN": 0.6,
    "ESPN Cric Info": 0.6,
    "Financial Post": 1.0,
    "Football Italia": 0.36,
    "Fortune": 1.0,
    "FourFourTwo": 0.48,
    "Fox News": 0.8,
    "Fox Sports": 0.6,
    "Google News": 0.8,
    "Google News (Australia)": 0.64,
    "Google News (Canada)": 0.8,
    "Google News (India)": 0.64,
    "Google News (UK)": 0.64,
    "Hacker News": 0.9,
    "IGN": 0.6,
    "Independent": 0.64,
    "Mashable": 0.6,
    "Medical News Today": 0.8,
    "MSNBC": 0.8,
    "MTV News": 0.6,
    "MTV News (UK)": 0.48,
    "National Geographic": 0.8,
    "National Review": 0.8,
    "NBC News": 0.8,
    "News24": 0.48,
    "New Scientist": 0.8,
    "News.com.au": 0.64,
    "Newsweek": 0.8,
    "New York Magazine": 0.8,
    "Next Big Future": 0.8,
    "NFL News": 0.6,
    "NHL News": 0.6,
    "Politico": 0.8,
    "Polygon": 0.6,
    "Recode": 0.9,
    "Reddit /r/all": 0.8,
    "Reuters": 0.8,
    "RTE": 0.48,
    "TalkSport": 0.48,
    "TechCrunch": 0.9,
    "TechRadar": 0.9,
    "The American Conservative": 0.8,
    "The Globe And Mail": 0.8,
    "The Hill": 0.8,
    "The Hindu": 0.64,
    "The Huffington Post": 0.8,
    "The Irish Times": 0.48,
    "The Jerusalem Post": 0.64,
    "The Lad Bible": 0.48,
    "The Next Web": 0.9,
    "The Sport Bible": 0.48,
    "The Times of India": 0.64,
    "The Verge": 0.9,
    "The Wall Street Journal": 1.0,
    "The Washington Post": 0.8,
    "The Washington Times": 0.8,
    "Time": 0.8,
    "USA Today": 0.8,
    "Vice News": 0.8,
    "Wired": 0.9,
}


DEFAULT_REDDIT_COMPONENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "Credibility": {
        "karma": 0.60,
        "distinguished": 0.30,
        "authorPremium": 0.10,
    },
    "Usefulness": {
        "score": 0.70,
        "stickied": 0.20,
        "totalAwardsReceived": 0.10,
    },
}

REDDIT_DIMENSION_WEIGHTS = {"Credibility": 0.70, "Usefulness": 0.30}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _minmax(value: Any, minimum: float, maximum: float) -> float:
    """Match the Query-screen batch min/max normalization."""
    if maximum == minimum:
        return 0.0
    return (_as_float(value) - minimum) / (maximum - minimum)


def _range(rows: Sequence[Mapping[str, Any]], field: str) -> Tuple[float, float]:
    values = [_as_float(row[field]) for row in rows if row.get(field) is not None]
    if not values:
        return 0.0, 1.0
    return min(values), max(values)


def news_weight_map(
    configured: Optional[
        Union[Iterable[Mapping[str, Any]], Mapping[str, float]]
    ] = None,
) -> Dict[str, float]:
    """Convert Query-screen ``[{name, Muliply}]`` data or a mapping to scores."""
    if configured is None:
        return dict(DEFAULT_NEWS_DQ_SCORES)
    if isinstance(configured, Mapping):
        return {str(key): float(value) for key, value in configured.items()}
    return {
        str(row["name"]): float(row["Muliply"])
        for row in configured
        if row.get("name") is not None and row.get("Muliply") is not None
    }


def news_multiplier(dq_score: Optional[float]) -> float:
    """Query-screen News multiplier bands."""
    if dq_score is None:
        return 1.0
    score = float(dq_score)
    if score <= 0.80:
        return 1.0
    if score <= 0.90:
        return 1.8
    return 3.0


def news_effective_weight(
    host: Optional[str],
    configured_scores: Optional[
        Union[Iterable[Mapping[str, Any]], Mapping[str, float]]
    ] = None,
    eligible_news_hosts: Optional[Iterable[str]] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Return one News document's effective DQ buzz contribution and metadata.

    Known host: ``DQ score * band multiplier`` (Query-screen formula).
    Eligible but unmapped host: neutral contribution of 1.0 (confirmed rule).
    Ineligible host: contribution 0.0 when an eligibility allow-list is supplied.
    """
    scores = news_weight_map(configured_scores)
    eligible: Optional[Set[str]] = (
        set(eligible_news_hosts) if eligible_news_hosts is not None else None
    )

    if eligible is not None and host not in eligible:
        return 0.0, {
            "dq_score": None,
            "dq_multiplier": 0.0,
            "dq_weight": 0.0,
            "dq_status": "ineligible",
        }

    score = scores.get(host)
    if score is None:
        return 1.0, {
            "dq_score": None,
            "dq_multiplier": 1.0,
            "dq_weight": 1.0,
            "dq_status": "eligible_unmapped",
        }

    multiplier = news_multiplier(score)
    effective = score * multiplier
    return effective, {
        "dq_score": score,
        "dq_multiplier": multiplier,
        "dq_weight": effective,
        "dq_status": "weighted",
    }


def apply_news_dq(
    documents: Sequence[Mapping[str, Any]],
    configured_scores: Optional[
        Union[Iterable[Mapping[str, Any]], Mapping[str, float]]
    ] = None,
    eligible_news_hosts: Optional[Iterable[str]] = None,
    host_field: str = "Host",
) -> List[Dict[str, Any]]:
    """Annotate News documents without changing their sentiment fields."""
    # Materialize once so callers may safely supply generators.
    scores = news_weight_map(configured_scores)
    eligible = (
        set(eligible_news_hosts) if eligible_news_hosts is not None else None
    )
    output: List[Dict[str, Any]] = []
    for source in documents:
        row = dict(source)
        weight, metadata = news_effective_weight(
            row.get(host_field), scores, eligible
        )
        row.update(metadata)
        row["dq_filtered"] = weight == 0.0
        output.append(row)
    return output


def reddit_dq_weight(dq_score: Optional[float]) -> float:
    """Query-screen r/WSB dead, normal and quadratic amplification zones."""
    if dq_score is None or float(dq_score) <= 0.20:
        return 0.0
    score = float(dq_score)
    if score <= 0.60:
        return 1.0
    x = (score - 0.60) / 0.40
    return 1.0 + 5.0 * (x**2)


def apply_reddit_dq(
    documents: Sequence[Mapping[str, Any]],
    component_weights: Optional[Mapping[str, Mapping[str, float]]] = None,
) -> List[Dict[str, Any]]:
    """Calculate Query-screen DQ score and effective buzz weight for r/WSB.

    Normalization deliberately occurs across the supplied batch, as in the
    Query-screen implementation.  Supply the same document population that the
    existing query would process for the period.
    """
    if not documents:
        return []

    weights = component_weights or DEFAULT_REDDIT_COMPONENT_WEIGHTS
    required_fields = {
        "stickied",
        "author_premium",
        "author_total_karma",
        "total_awards_received",
        "Score",
    }
    if not required_fields.issubset(documents[0].keys()):
        output: List[Dict[str, Any]] = []
        for source in documents:
            row = dict(source)
            row.update(
                {
                    "credibility": 0.0,
                    "usefulness": 0.0,
                    "DQ": 0.0,
                    "dq_weight": 0.0,
                    "dq_filtered": True,
                    "dq_status": "missing_required_fields",
                }
            )
            output.append(row)
        return output

    karma_min, karma_max = _range(documents, "author_total_karma")
    score_min, score_max = _range(documents, "Score")
    awards_min, awards_max = _range(documents, "total_awards_received")

    output: List[Dict[str, Any]] = []
    for source in documents:
        row = dict(source)

        distinguished = row.get("distinguished")
        distinguished_value = (
            1.0 if distinguished == "admin" else 0.5 if distinguished == "moderator" else 0.0
        )
        author_premium = 1.0 if row.get("author_premium", False) else 0.0
        karma = _minmax(row.get("author_total_karma"), karma_min, karma_max)
        score = _minmax(row.get("Score"), score_min, score_max)
        stickied = 1.0 if (
            row.get("stickied") is True or str(row.get("stickied")).lower() == "true"
        ) else 0.0
        awards = _minmax(
            row.get("total_awards_received"), awards_min, awards_max
        )

        credibility_raw = (
            weights["Credibility"]["distinguished"] * distinguished_value
            + weights["Credibility"]["authorPremium"] * author_premium
            + weights["Credibility"]["karma"] * karma
        )
        usefulness_raw = (
            weights["Usefulness"]["score"] * score
            + weights["Usefulness"]["stickied"] * stickied
            + weights["Usefulness"]["totalAwardsReceived"] * awards
        )
        # Preserve the Query-screen output semantics: the stored component
        # values already include their 70% / 30% dimension weights.
        credibility = REDDIT_DIMENSION_WEIGHTS["Credibility"] * credibility_raw
        usefulness = REDDIT_DIMENSION_WEIGHTS["Usefulness"] * usefulness_raw
        dq_score = min(credibility + usefulness, 0.999)
        effective = reddit_dq_weight(dq_score)

        row["credibility"] = credibility
        row["usefulness"] = usefulness
        row["DQ"] = dq_score
        row["dq_weight"] = effective
        row["dq_filtered"] = effective == 0.0
        row["dq_status"] = "filtered" if effective == 0.0 else "weighted"
        output.append(row)

    return output


def effective_buzz(documents: Sequence[Mapping[str, Any]]) -> float:
    """Return the effective DQ document count for one source and period."""
    return sum(_as_float(row.get("dq_weight")) for row in documents)


def percentage_change(current: float, previous: float) -> float:
    """Calculate a safe percentage change for DQ buzz."""
    current_value = float(current)
    previous_value = float(previous)
    if previous_value == 0.0:
        return 0.0
    return ((current_value - previous_value) / previous_value) * 100.0
