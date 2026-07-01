"""
Hotspot detection service using DBSCAN clustering.
Identifies geographic clusters of citizen pollution reports.
"""

import logging
from typing import List, Optional

import numpy as np

from backend.config import get_settings
from backend.models.schemas import CitizenReport, HotspotCluster
from backend.utils.aqi_categories import classify_aqi

logger = logging.getLogger(__name__)


def detect_hotspots(
    reports: List[CitizenReport],
    eps_km: Optional[float] = None,
    min_samples: Optional[int] = None,
) -> List[HotspotCluster]:
    """
    Detect pollution hotspots using DBSCAN on citizen report coordinates.

    DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
    is ideal here because:
    - Does not require specifying number of clusters
    - Finds clusters of arbitrary shape
    - Identifies noise points (isolated reports)
    - Works well with geographic coordinates

    Args:
        reports: List of citizen reports with lat/lon coordinates
        eps_km: Maximum distance between reports in a cluster (km)
        min_samples: Minimum reports to form a cluster

    Returns:
        List of HotspotCluster objects, sorted by severity (desc).
    """
    if len(reports) < 2:
        return []

    settings = get_settings()
    eps = eps_km or settings.dbscan_eps_km
    min_pts = min_samples or settings.dbscan_min_samples

    # Extract coordinates as numpy array
    coords = np.array([
        [r.latitude, r.longitude] for r in reports
    ])

    # Convert eps from km to approximate radians for haversine
    # 1 radian ≈ 6371 km
    eps_radians = eps / 6371.0

    try:
        from sklearn.cluster import DBSCAN
        from sklearn.metrics.pairwise import haversine_distances

        # DBSCAN with haversine metric (requires radians input)
        coords_radians = np.radians(coords)
        clustering = DBSCAN(
            eps=eps_radians,
            min_samples=min_pts,
            metric="haversine",
        ).fit(coords_radians)

        labels = clustering.labels_

    except ImportError:
        logger.warning("scikit-learn not available. Using simple distance-based clustering.")
        labels = _simple_clustering(coords, eps, min_pts)

    # Build cluster objects from labels
    clusters: List[HotspotCluster] = []
    unique_labels = set(labels)
    unique_labels.discard(-1)  # Remove noise label

    for cluster_id in sorted(unique_labels):
        cluster_mask = labels == cluster_id
        cluster_reports = [r for r, m in zip(reports, cluster_mask) if m]
        cluster_coords = coords[cluster_mask]

        if len(cluster_reports) < min_pts:
            continue

        # Cluster center (centroid)
        center_lat = float(np.mean(cluster_coords[:, 0]))
        center_lon = float(np.mean(cluster_coords[:, 1]))

        # Cluster radius (max distance from center to any point)
        from backend.utils.geo_utils import haversine_km
        distances = [
            haversine_km(center_lat, center_lon, r.latitude, r.longitude)
            for r in cluster_reports
        ]
        radius = max(distances) if distances else 0.5

        # Severity statistics
        severities = [r.severity.value for r in cluster_reports]
        avg_severity = float(np.mean(severities))

        # Dominant pollution type
        type_counts: dict[str, int] = {}
        for r in cluster_reports:
            t = r.pollution_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        dominant_type = max(type_counts, key=type_counts.get) if type_counts else "Unknown"

        # Estimated affected population (rough: Delhi avg density ~11,000/km²)
        area_km2 = 3.14159 * radius ** 2
        affected_pop = int(area_km2 * 11000)

        # Estimated AQI for the cluster center
        avg_aqi = None
        risk = "Unknown"

        cluster = HotspotCluster(
            cluster_id=int(cluster_id),
            center_latitude=round(center_lat, 6),
            center_longitude=round(center_lon, 6),
            radius_km=round(radius, 2),
            report_count=len(cluster_reports),
            avg_severity=round(avg_severity, 1),
            dominant_pollution_type=dominant_type,
            estimated_affected_population=affected_pop,
            estimated_aqi=avg_aqi,
            risk_level=risk,
        )
        clusters.append(cluster)

    # Sort by severity (highest first)
    clusters.sort(key=lambda c: c.avg_severity, reverse=True)
    logger.info("Detected %d hotspot clusters from %d reports", len(clusters), len(reports))
    return clusters


def _simple_clustering(
    coords: np.ndarray,
    eps_km: float,
    min_samples: int,
) -> np.ndarray:
    """
    Simple distance-based clustering fallback when sklearn is unavailable.
    Not as good as DBSCAN but functional for demo.
    """
    from backend.utils.geo_utils import haversine_km

    n = len(coords)
    labels = np.full(n, -1, dtype=int)
    visited = np.zeros(n, dtype=bool)
    cluster_id = 0

    for i in range(n):
        if visited[i]:
            continue
        visited[i] = True

        # Find neighbors
        neighbors = []
        for j in range(n):
            if i != j:
                dist = haversine_km(coords[i, 0], coords[i, 1], coords[j, 0], coords[j, 1])
                if dist <= eps_km:
                    neighbors.append(j)

        if len(neighbors) + 1 >= min_samples:
            labels[i] = cluster_id
            for j in neighbors:
                if not visited[j]:
                    visited[j] = True
                    labels[j] = cluster_id
            cluster_id += 1

    return labels


def get_severity_summary(clusters: List[HotspotCluster]) -> dict:
    """
    Generate a summary of all detected hotspots.

    Returns:
        Dict with total_clusters, critical_count, high_count,
        total_reports, total_affected_population.
    """
    if not clusters:
        return {
            "total_clusters": 0,
            "critical_count": 0,
            "high_count": 0,
            "total_reports": 0,
            "total_affected_population": 0,
        }

    return {
        "total_clusters": len(clusters),
        "critical_count": sum(1 for c in clusters if c.avg_severity >= 4),
        "high_count": sum(1 for c in clusters if 3 <= c.avg_severity < 4),
        "total_reports": sum(c.report_count for c in clusters),
        "total_affected_population": sum(c.estimated_affected_population for c in clusters),
    }
