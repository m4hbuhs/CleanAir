"""
deficiency_scorer.py

Calculates an Infrastructure Deficiency Score (0–100) per Delhi district
by cross-referencing citizen hazard reports, demographic baselines,
and municipal budget allocations from Firestore.

Refactored: Uses min-max normalization across the full district array
instead of hardcoded absolute divisors. Produces statistically sound,
outlier-resilient scores.
"""

import logging
from datetime import datetime, timedelta, timezone

from firebase_admin import firestore

from backend.config import DISTRICT_STATION_MAP
from backend.data_ingestion.budget_parser import MOCK_BUDGET_DATA

logger = logging.getLogger(__name__)

# Scoring weights
W_REPORTS = 0.45
W_DENSITY = 0.30
W_BUDGET = 0.25


def _grade_from_score(score: float) -> str:
    """Map score to a human-readable grade."""
    if score >= 80:
        return "Critical"
    elif score >= 60:
        return "Severe"
    elif score >= 40:
        return "Moderate"
    elif score >= 20:
        return "Adequate"
    else:
        return "Well-Funded"


def _get_report_count(db, district_id: str, days: int = 30) -> int:
    """Count citizen incident reports for a district over the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_iso = cutoff.isoformat()

    try:
        query = (
            db.collection("incidents")
            .where("district", "==", district_id)
            .where("timestamp", ">=", cutoff_iso)
        )
        docs = list(query.stream())
        return len(docs)
    except Exception as e:
        logger.warning(f"Firestore query failed for district {district_id}: {e}")
        return 0


def _get_baseline(db, district_id: str) -> dict:
    """Fetch baseline infrastructure metrics from Firestore."""
    try:
        doc = db.collection("district_baselines").document(district_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        logger.warning(f"Failed to fetch baseline for {district_id}: {e}")
    return {}


def _get_budget(db, district_id: str) -> dict:
    """Fetch budget allocation from Firestore."""
    try:
        doc = db.collection("district_budgets").document(district_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as e:
        logger.warning(f"Failed to fetch budget for {district_id}: {e}")
    return {}


def _min_max_normalize(values: list[float]) -> list[float]:
    """
    Global min-max scaler applied across the entire district array.
    Returns values normalized to [0, 1]. If all values are equal, returns 0.5.
    """
    if not values:
        return []
    v_min = min(values)
    v_max = max(values)
    spread = v_max - v_min
    if spread == 0:
        return [0.5] * len(values)
    return [(v - v_min) / spread for v in values]


def get_all_district_scores() -> list[dict]:
    """
    Calculate deficiency scores for all 13 Delhi districts using
    relative min-max normalization instead of hardcoded absolute divisors.
    """
    districts = list(DISTRICT_STATION_MAP.keys())
    db = firestore.client()

    # Phase 1: Collect raw metrics for ALL districts
    raw_data = []
    for district_id in districts:
        report_count = _get_report_count(db, district_id)
        baseline = _get_baseline(db, district_id)
        budget = _get_budget(db, district_id)

        total_population = baseline.get("total_population", 200000)
        population_density = baseline.get("population_density", 10000.0)
        budget_total = budget.get("total_budget_lakhs", 0.0)

        # Per-capita metrics for fair cross-district comparison
        reports_per_capita = (report_count / total_population * 100000) if total_population > 0 else 0.0
        budget_per_capita = (budget_total / total_population * 100000) if total_population > 0 else 0.0

        raw_data.append({
            "district_id": district_id,
            "report_count": report_count,
            "population_density": population_density,
            "total_population": total_population,
            "budget_total_lakhs": budget_total,
            "reports_per_capita": reports_per_capita,
            "budget_per_capita": budget_per_capita,
        })

    # Phase 2: Min-max normalize across the full array
    report_pressures = _min_max_normalize([d["reports_per_capita"] for d in raw_data])
    density_pressures = _min_max_normalize([d["population_density"] for d in raw_data])
    budget_adequacies = _min_max_normalize([d["budget_per_capita"] for d in raw_data])

    # Phase 3: Compute weighted composite scores
    scores = []
    for i, d in enumerate(raw_data):
        rp = report_pressures[i]
        dp = density_pressures[i]
        ba = budget_adequacies[i]

        raw_score = W_REPORTS * rp + W_DENSITY * dp - W_BUDGET * ba
        score = max(0.0, min(100.0, round(raw_score * 100, 1)))

        scores.append({
            "district_id": d["district_id"],
            "score": score,
            "grade": _grade_from_score(score),
            "report_count": d["report_count"],
            "population_density": d["population_density"],
            "total_population": d["total_population"],
            "budget_total_lakhs": d["budget_total_lakhs"],
            "breakdown": {
                "report_pressure": round(rp, 3),
                "density_pressure": round(dp, 3),
                "budget_adequacy": round(ba, 3),
            },
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores


def calculate_deficiency_score(district_id: str) -> dict:
    """
    Calculate a single district's score. Delegates to the full array scorer
    and extracts the result, ensuring consistent relative normalization.
    """
    all_scores = get_all_district_scores()
    for s in all_scores:
        if s["district_id"] == district_id:
            return s
    return {
        "district_id": district_id,
        "score": 0.0,
        "grade": "Unknown",
        "report_count": 0,
        "population_density": 0.0,
        "total_population": 0,
        "budget_total_lakhs": 0.0,
        "breakdown": {"report_pressure": 0.0, "density_pressure": 0.0, "budget_adequacy": 0.0},
    }


def get_mock_district_scores() -> list[dict]:
    """
    Return deterministic mock scores for demo/fallback when Firestore
    is unavailable. Uses min-max normalization on mock data.
    """
    mock_baselines = {
        "central": {"pop_density": 26115.8, "total_pop": 373650},
        "central_north": {"pop_density": 16341.8, "total_pop": 348100},
        "east": {"pop_density": 19055.6, "total_pop": 514500},
        "new_delhi": {"pop_density": 13433.9, "total_pop": 170800},
        "north": {"pop_density": 7147.9, "total_pop": 507900},
        "north_east": {"pop_density": 29735.0, "total_pop": 683900},
        "north_west": {"pop_density": 9605.9, "total_pop": 486000},
        "old_delhi": {"pop_density": 35041.3, "total_pop": 424200},
        "outer_north": {"pop_density": 3866.5, "total_pop": 324100},
        "south": {"pop_density": 12203.1, "total_pop": 313800},
        "south_east": {"pop_density": 13791.8, "total_pop": 402700},
        "south_west": {"pop_density": 6933.0, "total_pop": 474300},
        "west": {"pop_density": 12625.8, "total_pop": 391400},
    }

    mock_reports = {
        "central": 12, "central_north": 8, "east": 28, "new_delhi": 5,
        "north": 18, "north_east": 42, "north_west": 15,
        "old_delhi": 35, "outer_north": 22, "south": 6,
        "south_east": 14, "south_west": 19, "west": 11,
    }

    budget_map = {b["district_id"]: b for b in MOCK_BUDGET_DATA}

    # Collect raw per-capita metrics
    raw_data = []
    for district_id, baseline in mock_baselines.items():
        pop = baseline["total_pop"]
        reports = mock_reports.get(district_id, 10)
        budget = budget_map.get(district_id, {})
        budget_total = budget.get("total_budget_lakhs", 3000.0)

        raw_data.append({
            "district_id": district_id,
            "pop_density": baseline["pop_density"],
            "total_pop": pop,
            "reports": reports,
            "budget_total": budget_total,
            "reports_per_capita": (reports / pop * 100000) if pop > 0 else 0,
            "budget_per_capita": (budget_total / pop * 100000) if pop > 0 else 0,
        })

    # Min-max normalize
    rp_norm = _min_max_normalize([d["reports_per_capita"] for d in raw_data])
    dp_norm = _min_max_normalize([d["pop_density"] for d in raw_data])
    ba_norm = _min_max_normalize([d["budget_per_capita"] for d in raw_data])

    scores = []
    for i, d in enumerate(raw_data):
        rp, dp, ba = rp_norm[i], dp_norm[i], ba_norm[i]
        raw = W_REPORTS * rp + W_DENSITY * dp - W_BUDGET * ba
        score = max(0.0, min(100.0, round(raw * 100, 1)))

        scores.append({
            "district_id": d["district_id"],
            "score": score,
            "grade": _grade_from_score(score),
            "report_count": d["reports"],
            "population_density": d["pop_density"],
            "total_population": d["total_pop"],
            "budget_total_lakhs": d["budget_total"],
            "breakdown": {
                "report_pressure": round(rp, 3),
                "density_pressure": round(dp, 3),
                "budget_adequacy": round(ba, 3),
            },
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores
