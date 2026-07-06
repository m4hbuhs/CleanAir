"""
budget_parser.py

Parses unstructured MCD (Municipal Corporation of Delhi) Budget Estimate PDFs
using the Gemini 2.5 Flash model. Extracts per-district budget allocations for
Sanitation, Road Maintenance, and Environment, then pushes to Firestore.

Refactored: Uses Pydantic schema + native `response_mime_type` to force
structured JSON output, eliminating fragile manual text parsing.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
import google.generativeai as genai
from firebase_admin import firestore

from backend.config import get_settings, PROJECT_ROOT

logger = logging.getLogger(__name__)


# --- Pydantic Schema for LLM-enforced structured output ---

class BudgetExtraction(BaseModel):
    """Single district budget extraction result."""
    district_id: str = Field(description="Snake_case Delhi district ID")
    district_name: str = Field(default="", description="Human-readable district name")
    sanitation_budget_lakhs: float = Field(default=0.0, description="Sanitation budget in lakhs")
    road_maintenance_budget_lakhs: float = Field(default=0.0, description="Road maintenance budget in lakhs")
    environment_budget_lakhs: float = Field(default=0.0, description="Environment budget in lakhs")
    total_budget_lakhs: float = Field(default=0.0, description="Sum of all three category budgets in lakhs")
    fiscal_year: str = Field(default="2025-26", description="Fiscal year string")


EXTRACTION_PROMPT = """You are a municipal budget data extraction specialist.

Analyze the attached MCD (Municipal Corporation of Delhi) Budget Estimate document.

Extract the budget allocations **per district** for EXACTLY these three categories:
1. **Sanitation** — includes solid waste management, drain cleaning, sewerage
2. **Road Maintenance** — includes road repair, construction, footpaths, street lighting
3. **Environment** — includes pollution control, tree plantation, parks, green initiatives

Rules:
- All budget values must be in **lakhs (₹)**.
- Use snake_case district IDs matching the Delhi administrative districts:
  central, central_north, east, new_delhi, north, north_east, north_west,
  old_delhi, outer_north, south, south_east, south_west, west
- `total_budget_lakhs` = sum of the three category budgets.
- If a district is not mentioned, omit it entirely.
- If a value cannot be determined, use 0.
"""

# Fallback mock data for demo/testing when no PDF is available
MOCK_BUDGET_DATA = [
    {"district_id": "central", "district_name": "Central Delhi", "sanitation_budget_lakhs": 1850, "road_maintenance_budget_lakhs": 2200, "environment_budget_lakhs": 680, "total_budget_lakhs": 4730, "fiscal_year": "2025-26"},
    {"district_id": "central_north", "district_name": "Central North Delhi", "sanitation_budget_lakhs": 1420, "road_maintenance_budget_lakhs": 1800, "environment_budget_lakhs": 520, "total_budget_lakhs": 3740, "fiscal_year": "2025-26"},
    {"district_id": "east", "district_name": "East Delhi", "sanitation_budget_lakhs": 2100, "road_maintenance_budget_lakhs": 2500, "environment_budget_lakhs": 450, "total_budget_lakhs": 5050, "fiscal_year": "2025-26"},
    {"district_id": "new_delhi", "district_name": "New Delhi", "sanitation_budget_lakhs": 3200, "road_maintenance_budget_lakhs": 3800, "environment_budget_lakhs": 1200, "total_budget_lakhs": 8200, "fiscal_year": "2025-26"},
    {"district_id": "north", "district_name": "North Delhi", "sanitation_budget_lakhs": 1650, "road_maintenance_budget_lakhs": 1900, "environment_budget_lakhs": 380, "total_budget_lakhs": 3930, "fiscal_year": "2025-26"},
    {"district_id": "north_east", "district_name": "North East Delhi", "sanitation_budget_lakhs": 980, "road_maintenance_budget_lakhs": 1100, "environment_budget_lakhs": 220, "total_budget_lakhs": 2300, "fiscal_year": "2025-26"},
    {"district_id": "north_west", "district_name": "North West Delhi", "sanitation_budget_lakhs": 1800, "road_maintenance_budget_lakhs": 2100, "environment_budget_lakhs": 550, "total_budget_lakhs": 4450, "fiscal_year": "2025-26"},
    {"district_id": "old_delhi", "district_name": "Old Delhi", "sanitation_budget_lakhs": 1200, "road_maintenance_budget_lakhs": 1400, "environment_budget_lakhs": 280, "total_budget_lakhs": 2880, "fiscal_year": "2025-26"},
    {"district_id": "outer_north", "district_name": "Outer North Delhi", "sanitation_budget_lakhs": 1100, "road_maintenance_budget_lakhs": 1300, "environment_budget_lakhs": 310, "total_budget_lakhs": 2710, "fiscal_year": "2025-26"},
    {"district_id": "south", "district_name": "South Delhi", "sanitation_budget_lakhs": 2800, "road_maintenance_budget_lakhs": 3200, "environment_budget_lakhs": 950, "total_budget_lakhs": 6950, "fiscal_year": "2025-26"},
    {"district_id": "south_east", "district_name": "South East Delhi", "sanitation_budget_lakhs": 1950, "road_maintenance_budget_lakhs": 2300, "environment_budget_lakhs": 620, "total_budget_lakhs": 4870, "fiscal_year": "2025-26"},
    {"district_id": "south_west", "district_name": "South West Delhi", "sanitation_budget_lakhs": 1750, "road_maintenance_budget_lakhs": 2000, "environment_budget_lakhs": 480, "total_budget_lakhs": 4230, "fiscal_year": "2025-26"},
    {"district_id": "west", "district_name": "West Delhi", "sanitation_budget_lakhs": 1600, "road_maintenance_budget_lakhs": 1850, "environment_budget_lakhs": 420, "total_budget_lakhs": 3870, "fiscal_year": "2025-26"},
]


def parse_budget_pdf(pdf_path: str) -> list[dict]:
    """
    Parse an MCD budget PDF using Gemini 2.5 Flash with native structured
    output (response_mime_type + response_schema) to guarantee valid JSON.
    Eliminates fragile manual string parsing of LLM output.
    """
    settings = get_settings()
    api_key = settings.gemini_api_key

    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Returning mock budget data.")
        return MOCK_BUDGET_DATA

    genai.configure(api_key=api_key)

    pdf_bytes = Path(pdf_path).read_bytes()

    # Use native structured output: force Gemini to return validated JSON
    model = genai.GenerativeModel(
        settings.gemini_model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=list[BudgetExtraction],
            temperature=0.1,
            max_output_tokens=4096,
        ),
    )

    response = model.generate_content([
        EXTRACTION_PROMPT,
        {"mime_type": "application/pdf", "data": pdf_bytes},
    ])

    # With response_mime_type="application/json", response.text is always
    # clean JSON — no markdown fences, no preamble, no manual stripping.
    try:
        parsed = json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error(f"Gemini structured output still invalid: {e}\nRaw: {response.text[:500]}")
        logger.warning("Falling back to mock budget data.")
        return MOCK_BUDGET_DATA

    if not isinstance(parsed, list):
        parsed = [parsed]

    # Validate each entry through Pydantic
    validated = []
    for entry in parsed:
        try:
            item = BudgetExtraction(**entry)
            validated.append(item.model_dump())
        except Exception as e:
            logger.warning(f"Skipping invalid budget entry: {e}")

    logger.info(f"Extracted & validated budget data for {len(validated)} districts from PDF")
    return validated if validated else MOCK_BUDGET_DATA


def get_mock_budgets() -> list[dict]:
    """Return mock budget data for demo/development."""
    return MOCK_BUDGET_DATA


def push_budgets_to_firestore(
    budget_data: Optional[list[dict]] = None,
    pdf_path: Optional[str] = None,
) -> dict:
    """
    Push parsed budget data into Firestore `district_budgets` collection.
    
    If budget_data is provided, use it directly.
    If pdf_path is provided, parse it first.
    If neither, use mock data.
    """
    if budget_data is None:
        if pdf_path:
            budget_data = parse_budget_pdf(pdf_path)
        else:
            logger.info("No PDF path given. Using mock budget data.")
            budget_data = get_mock_budgets()

    db = firestore.client()
    batch = db.batch()
    results = {}

    for entry in budget_data:
        district_id = entry.get("district_id", "unknown")
        doc_ref = db.collection("district_budgets").document(district_id)

        payload = {
            "district_id": district_id,
            "district_name": entry.get("district_name", district_id.replace("_", " ").title()),
            "sanitation_budget_lakhs": float(entry.get("sanitation_budget_lakhs", 0)),
            "road_maintenance_budget_lakhs": float(entry.get("road_maintenance_budget_lakhs", 0)),
            "environment_budget_lakhs": float(entry.get("environment_budget_lakhs", 0)),
            "total_budget_lakhs": float(entry.get("total_budget_lakhs", 0)),
            "fiscal_year": entry.get("fiscal_year", "2025-26"),
            "source": "budget_parser",
        }
        batch.set(doc_ref, payload, merge=True)
        results[district_id] = payload

    batch.commit()
    logger.info(f"Pushed budget data for {len(results)} districts to Firestore")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import firebase_admin
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    result = push_budgets_to_firestore()
    for district, data in result.items():
        print(f"  {district}: total=₹{data['total_budget_lakhs']}L "
              f"(sanitation={data['sanitation_budget_lakhs']}L, "
              f"roads={data['road_maintenance_budget_lakhs']}L, "
              f"env={data['environment_budget_lakhs']}L)")
