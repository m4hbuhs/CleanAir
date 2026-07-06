"""
registry_parser.py

Loads Delhi UDISE+ School Capacity and Ward-level Census CSV datasets,
cleans and merges them on district_id, then pushes baseline infrastructure
metrics into Firestore for use by the Deficiency Scorer.
"""

import logging
from pathlib import Path

import pandas as pd
from firebase_admin import firestore

from backend.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

DATA_DIR = PROJECT_ROOT / "data"

DEFAULT_CENSUS_CSV = DATA_DIR / "delhi_census_demographics.csv"
DEFAULT_SCHOOL_CSV = DATA_DIR / "delhi_school_capacity.csv"


def load_census_data(csv_path: Path = DEFAULT_CENSUS_CSV) -> pd.DataFrame:
    """Load and clean Delhi ward-level census demographics."""
    df = pd.read_csv(csv_path)

    # Standardise column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"district_id", "total_population", "area_sq_km"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Census CSV missing columns: {missing}")

    # Drop rows with null keys
    df = df.dropna(subset=["district_id", "total_population", "area_sq_km"])

    # Compute population density (people / km²)
    df["population_density"] = (
        df["total_population"] / df["area_sq_km"]
    ).round(1)

    logger.info(f"Loaded {len(df)} census ward records from {csv_path.name}")
    return df


def load_school_data(csv_path: Path = DEFAULT_SCHOOL_CSV) -> pd.DataFrame:
    """Load and clean Delhi UDISE+ school capacity data."""
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    required = {"district_id", "total_capacity", "current_enrollment"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"School CSV missing columns: {missing}")

    df = df.dropna(subset=["district_id", "total_capacity", "current_enrollment"])

    logger.info(f"Loaded {len(df)} school records from {csv_path.name}")
    return df


def load_and_merge_registries(
    school_csv: Path = DEFAULT_SCHOOL_CSV,
    census_csv: Path = DEFAULT_CENSUS_CSV,
) -> pd.DataFrame:
    """
    Merge census demographics and school capacity data on district_id.

    Returns a district-level DataFrame with columns:
        district_id, total_population, area_sq_km, population_density,
        total_school_capacity, total_enrollment, school_capacity_ratio,
        num_schools
    """
    census = load_census_data(census_csv)
    schools = load_school_data(school_csv)

    # Aggregate census to district level
    census_agg = (
        census.groupby("district_id")
        .agg(
            total_population=("total_population", "sum"),
            area_sq_km=("area_sq_km", "sum"),
            num_wards=("district_id", "count"),
        )
        .reset_index()
    )
    census_agg["population_density"] = (
        census_agg["total_population"] / census_agg["area_sq_km"]
    ).round(1)

    # Aggregate schools to district level
    school_agg = (
        schools.groupby("district_id")
        .agg(
            total_school_capacity=("total_capacity", "sum"),
            total_enrollment=("current_enrollment", "sum"),
            num_schools=("district_id", "count"),
        )
        .reset_index()
    )

    # Sanitize join keys to prevent silent data dropping on mismatch
    census_agg["district_id"] = census_agg["district_id"].str.strip().str.upper()
    school_agg["district_id"] = school_agg["district_id"].str.strip().str.upper()

    pre_merge_count = len(census_agg)

    # Merge on district_id
    merged = pd.merge(census_agg, school_agg, on="district_id", how="left")
    
    if len(merged) < pre_merge_count:
        logger.warning(f"Data dropped during merge! Pre-merge rows: {pre_merge_count}, Post-merge rows: {len(merged)}")

    # School capacity ratio = enrollment / capacity (>1.0 means overcrowded)
    merged["school_capacity_ratio"] = (
        merged["total_enrollment"] / merged["total_school_capacity"]
    ).round(3)
    merged["school_capacity_ratio"] = merged["school_capacity_ratio"].fillna(0.0)

    # Normalize back to lower case for consistent downstream usage
    merged["district_id"] = merged["district_id"].str.lower()

    logger.info(f"Merged registry data for {len(merged)} districts")
    return merged


def push_baselines_to_firestore(
    school_csv: Path = DEFAULT_SCHOOL_CSV,
    census_csv: Path = DEFAULT_CENSUS_CSV,
) -> dict:
    """
    Load, merge, and push district-level baseline infrastructure metrics
    into the Firestore `district_baselines` collection.
    """
    merged = load_and_merge_registries(school_csv, census_csv)
    db = firestore.client()
    batch = db.batch()
    results = {}

    for _, row in merged.iterrows():
        district_id = row["district_id"]
        doc_ref = db.collection("district_baselines").document(district_id)

        payload = {
            "district_id": district_id,
            "total_population": int(row["total_population"]),
            "area_sq_km": float(row["area_sq_km"]),
            "population_density": float(row["population_density"]),
            "num_wards": int(row["num_wards"]),
            "total_school_capacity": int(row.get("total_school_capacity", 0)),
            "total_enrollment": int(row.get("total_enrollment", 0)),
            "school_capacity_ratio": float(row["school_capacity_ratio"]),
            "num_schools": int(row.get("num_schools", 0)),
            "source": "registry_parser",
        }
        batch.set(doc_ref, payload, merge=True)
        results[district_id] = payload

    batch.commit()
    logger.info(f"Pushed baselines for {len(results)} districts to Firestore")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import firebase_admin
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    result = push_baselines_to_firestore()
    for district, data in result.items():
        print(f"  {district}: pop_density={data['population_density']}, "
              f"school_ratio={data['school_capacity_ratio']}")
