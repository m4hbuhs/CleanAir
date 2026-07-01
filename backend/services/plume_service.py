"""
Gaussian plume dispersion model for pollution visualization.
Models how a pollution plume spreads based on wind vector and AQI intensity.
"""

import numpy as np
import pandas as pd


def generate_plume_geometry(
    lat: float,
    lon: float,
    wind_u: float,
    wind_v: float,
    aqi_weight: float,
    num_steps: int = 50,
    lateral_samples: int = 5,
    step_scale: float = 15.0,
    source_points: int = 20,
) -> pd.DataFrame:
    """
    Generate a synthetic Gaussian plume dispersion pattern.

    The model traces particle movement downwind from the source,
    applying lateral Gaussian dispersion at each step. Used for
    heatmap visualization — NOT for regulatory dispersion modeling.

    Args:
        lat: Source latitude (decimal degrees)
        lon: Source longitude (decimal degrees)
        wind_u: East-west wind component (m/s, from feature engineering)
        wind_v: North-south wind component (m/s, from feature engineering)
        aqi_weight: Pollution intensity weight (typically the predicted AQI)
        num_steps: Number of downwind steps to trace
        lateral_samples: Random lateral samples per step (Gaussian spread)
        step_scale: Spatial step multiplier (meters per step)
        source_points: Additional dense points at the emission source

    Returns:
        DataFrame with columns: latitude, longitude, weight
        Suitable for Pydeck HeatmapLayer rendering.
    """
    points = []

    # Coordinate scaling factors
    lat_scale = 111_000.0  # meters per degree latitude
    lon_scale = 111_000.0 * np.cos(np.radians(lat))

    # Handle zero-wind case
    if abs(wind_u) < 0.01 and abs(wind_v) < 0.01:
        # Calm conditions → radial spread
        for r in range(1, num_steps + 1):
            for theta in np.linspace(0, 2 * np.pi, lateral_samples * 2, endpoint=False):
                dist = r * step_scale
                p_lat = lat + (dist * np.sin(theta)) / lat_scale
                p_lon = lon + (dist * np.cos(theta)) / lon_scale
                intensity = aqi_weight / (1.0 + (r * 0.15))
                points.append({
                    "latitude": p_lat,
                    "longitude": p_lon,
                    "weight": max(5.0, intensity),
                })
        # Source hotspot
        for _ in range(source_points):
            points.append({
                "latitude": lat + np.random.normal(0, 0.0003),
                "longitude": lon + np.random.normal(0, 0.0003),
                "weight": aqi_weight * 1.5,
            })
        return pd.DataFrame(points)

    # Wind-driven dispersion
    for step in range(1, num_steps + 1):
        # Downwind position
        step_lat = lat + (wind_v * step * step_scale) / lat_scale
        step_lon = lon + (wind_u * step * step_scale) / lon_scale

        # Lateral Gaussian spread increases with distance
        lateral_variance = 0.05 * step
        crosswind_offsets = np.random.normal(0, lateral_variance, lateral_samples)

        for offset in crosswind_offsets:
            # Crosswind displacement (perpendicular to wind direction)
            p_lat = step_lat + (offset * wind_u * 5) / lat_scale
            p_lon = step_lon - (offset * wind_v * 5) / lon_scale

            # Intensity decays with distance from source
            intensity = aqi_weight / (1.0 + (step * 0.1))
            points.append({
                "latitude": p_lat,
                "longitude": p_lon,
                "weight": max(5.0, intensity),
            })

    # Dense source points for the emission hotspot
    for _ in range(source_points):
        points.append({
            "latitude": lat + np.random.normal(0, 0.0002),
            "longitude": lon + np.random.normal(0, 0.0002),
            "weight": aqi_weight * 1.5,
        })

    return pd.DataFrame(points)


def estimate_plume_reach_km(wind_speed: float, stability_class: str = "D") -> float:
    """
    Rough estimate of how far the plume reaches (km) based on wind speed.

    Uses simplified Pasquill stability classes:
    A-B: Unstable (rapid dispersion)
    C-D: Neutral (moderate dispersion)
    E-F: Stable (slow dispersion, travels farther)

    Returns:
        Estimated plume reach in kilometers.
    """
    stability_multipliers = {
        "A": 0.5, "B": 0.7, "C": 0.85,
        "D": 1.0, "E": 1.3, "F": 1.6,
    }
    multiplier = stability_multipliers.get(stability_class, 1.0)
    # Base reach: wind_speed * 0.5 km, adjusted by stability
    return round(wind_speed * 0.5 * multiplier, 2)
