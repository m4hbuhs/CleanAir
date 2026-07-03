"""
Satellite data provider for the Virtual Sensor Network.

Provides an abstraction layer for satellite-derived environmental features
(aerosol optical depth, thermal anomalies, smoke detection, etc.).

Currently uses a mock provider reading from data/mock_satellite.json.
Designed so real providers (Google Earth Engine, CAMS, etc.) can be
swapped in via the satellite_provider config setting.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from backend.config import get_settings, DATA_DIR
from backend.models.schemas import SatelliteFeatures
from backend.utils.geo_utils import haversine_km

logger = logging.getLogger(__name__)


class SatelliteProvider(ABC):
    """
    Abstract base class for satellite data providers.

    Subclass this and implement fetch() to integrate a real satellite
    API such as Google Earth Engine, CAMS, or Sentinel Hub.
    """

    @abstractmethod
    def fetch(self, latitude: float, longitude: float) -> SatelliteFeatures:
        """Fetch satellite features for a given location."""
        ...


class MockSatelliteProvider(SatelliteProvider):
    """
    Mock satellite provider that interpolates from static grid data.

    Reads from data/mock_satellite.json and returns the features
    of the nearest grid cell to the requested location, with
    distance-based interpolation for AOD.
    """

    def __init__(self):
        self._data: Optional[list] = None
        self._load()

    def _load(self) -> None:
        """Load mock satellite data from disk."""
        path = DATA_DIR / "mock_satellite.json"
        if not path.exists():
            logger.warning("Mock satellite data not found at %s", path)
            self._data = []
            return

        try:
            with open(path, "r") as f:
                raw = json.load(f)
            self._data = raw.get("delhi_grid_cells", [])
            logger.info(
                "Loaded %d mock satellite grid cells", len(self._data)
            )
        except Exception as e:
            logger.error("Failed to load mock satellite data: %s", e)
            self._data = []

    def _get_nearest_cell(self, latitude: float, longitude: float) -> dict:
        """Helper to find the nearest mock cell."""
        if not self._data:
            return {}

        best_cell = self._data[0]
        best_dist = float("inf")
        for cell in self._data:
            dist = haversine_km(latitude, longitude, cell["latitude"], cell["longitude"])
            if dist < best_dist:
                best_dist = dist
                best_cell = cell
        return best_cell

    def fetch(self, latitude: float, longitude: float) -> SatelliteFeatures:
        """
        Find the nearest mock satellite grid cell and return its features.
        """
        best_cell = self._get_nearest_cell(latitude, longitude)
        if not best_cell:
            return SatelliteFeatures(source="mock_unavailable")

        return SatelliteFeatures(
            aerosol_optical_depth=float(best_cell.get("aod", 0.0)),
            dust=float(best_cell.get("aod", 0.0)) * 10.0,  # Rough proxy
            uv_index=5.0,  # Default for Delhi latitude
            land_surface_temp=40.0,  # Default summer Delhi
            thermal_anomaly=bool(best_cell.get("thermal_anomaly", False)),
            smoke_detected=bool(best_cell.get("smoke_detected", False)),
            source=str(best_cell.get("source", "mock")),
        )

    def detect_smoke(self, latitude: float, longitude: float) -> bool:
        """Check if smoke is detected via spectral analysis in satellite imagery."""
        cell = self._get_nearest_cell(latitude, longitude)
        return bool(cell.get("smoke_detected", False))

    def detect_fire(self, latitude: float, longitude: float) -> bool:
        """Check if thermal anomaly/fire is detected."""
        cell = self._get_nearest_cell(latitude, longitude)
        return bool(cell.get("thermal_anomaly", False))

    def detect_dust(self, latitude: float, longitude: float) -> bool:
        """Check if heavy dust (high AOD) is detected."""
        cell = self._get_nearest_cell(latitude, longitude)
        aod = float(cell.get("aod", 0.0))
        return aod > 0.6  # High aerosol optical depth threshold for dust

    def generate_satellite_features(self, latitude: float, longitude: float) -> dict:
        """Generate a complete dictionary of satellite-derived features."""
        features = self.fetch(latitude, longitude)
        return {
            "satellite_smoke": int(features.smoke_detected),
            "satellite_fire": int(features.thermal_anomaly),
            "satellite_dust": 1 if features.dust > 5.0 else 0,
            "satellite_aod": features.aerosol_optical_depth,
            "satellite_temp": features.land_surface_temp
        }

# ── Provider registry ──────────────────────────

_PROVIDERS = {
    "mock": MockSatelliteProvider,
    # Future: "earth_engine": GoogleEarthEngineProvider,
    # Future: "cams": CamsProvider,
}


def fetch_satellite_features(
    latitude: float,
    longitude: float,
) -> SatelliteFeatures:
    """
    Fetch satellite-derived features for a location using the
    configured provider.

    Returns:
        SatelliteFeatures with AOD, dust, UV, thermal anomaly, etc.
    """
    settings = get_settings()
    provider_cls = _PROVIDERS.get(settings.satellite_provider, MockSatelliteProvider)
    provider = provider_cls()
    return provider.fetch(latitude, longitude)
