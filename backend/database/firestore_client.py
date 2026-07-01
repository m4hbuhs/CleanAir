"""
Persistence layer using Streamlit session_state as in-memory mock DB.
When Firebase credentials are available, can be upgraded to Firestore.

For the hackathon demo, st.session_state provides:
- Zero setup (no Firebase project needed)
- Full CRUD functionality
- Persists within a single Streamlit session
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from backend.models.schemas import (
    CitizenReport,
    CitizenWallet,
    HotspotCluster,
    ViolationRecord,
)

logger = logging.getLogger(__name__)


class InMemoryDB:
    """
    In-memory database that mirrors Firestore collections.
    Uses dict storage; in production, swap with Firestore client calls.

    Collections:
    - reports: CitizenReport objects
    - wallets: CitizenWallet objects
    - hotspots: HotspotCluster objects
    - violations: ViolationRecord objects
    - predictions: Prediction history
    """

    def __init__(self):
        self._reports: dict[str, CitizenReport] = {}
        self._wallets: dict[str, CitizenWallet] = {}
        self._hotspots: dict[int, HotspotCluster] = {}
        self._violations: dict[str, ViolationRecord] = {}
        self._predictions: list[dict] = []

    # ── Reports ──────────────────────────────

    def add_report(self, report: CitizenReport) -> CitizenReport:
        """Save a citizen report. Generates ID if not set."""
        if not report.report_id:
            report.report_id = str(uuid.uuid4())[:8]
        self._reports[report.report_id] = report
        logger.info("Report saved: %s", report.report_id)
        return report

    def get_report(self, report_id: str) -> Optional[CitizenReport]:
        return self._reports.get(report_id)

    def get_all_reports(self) -> List[CitizenReport]:
        return sorted(
            self._reports.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )

    def get_reports_by_status(self, status: str) -> List[CitizenReport]:
        return [
            r for r in self._reports.values()
            if r.status.value == status
        ]

    def update_report_status(self, report_id: str, status: str) -> bool:
        report = self._reports.get(report_id)
        if report:
            from backend.models.schemas import ReportStatus
            report.status = ReportStatus(status)
            return True
        return False

    # ── Wallets ──────────────────────────────

    def get_wallet(self, user_id: str) -> CitizenWallet:
        """Get or create a citizen wallet."""
        if user_id not in self._wallets:
            self._wallets[user_id] = CitizenWallet(
                user_id=user_id,
                display_name=f"Citizen_{user_id[:6]}",
            )
        return self._wallets[user_id]

    def save_wallet(self, wallet: CitizenWallet) -> None:
        self._wallets[wallet.user_id] = wallet

    def get_all_wallets(self) -> List[CitizenWallet]:
        return list(self._wallets.values())

    # ── Hotspots ──────────────────────────────

    def save_hotspots(self, clusters: List[HotspotCluster]) -> None:
        self._hotspots.clear()
        for cluster in clusters:
            self._hotspots[cluster.cluster_id] = cluster

    def get_hotspots(self) -> List[HotspotCluster]:
        return list(self._hotspots.values())

    # ── Violations ──────────────────────────────

    def record_violation(
        self,
        report: CitizenReport,
    ) -> ViolationRecord:
        """
        Track repeated violations at a location.
        If an existing violation exists within 500m, increment count.
        """
        from backend.utils.geo_utils import haversine_km

        # Check for nearby existing violations
        for vid, violation in self._violations.items():
            dist = haversine_km(
                report.latitude, report.longitude,
                violation.latitude, violation.longitude,
            )
            if dist <= 0.5 and violation.violation_type == report.pollution_type.value:
                violation.occurrence_count += 1
                violation.last_reported = datetime.now(timezone.utc)
                violation.report_ids.append(report.report_id)
                return violation

        # New violation
        vid = str(uuid.uuid4())[:8]
        violation = ViolationRecord(
            location_label=f"Location ({report.latitude:.4f}, {report.longitude:.4f})",
            latitude=report.latitude,
            longitude=report.longitude,
            violation_type=report.pollution_type.value,
            report_ids=[report.report_id],
        )
        self._violations[vid] = violation
        return violation

    def get_violations(self, min_count: int = 2) -> List[ViolationRecord]:
        """Get locations with repeated violations."""
        return sorted(
            [v for v in self._violations.values() if v.occurrence_count >= min_count],
            key=lambda v: v.occurrence_count,
            reverse=True,
        )

    def get_all_violations(self) -> List[ViolationRecord]:
        return sorted(
            self._violations.values(),
            key=lambda v: v.occurrence_count,
            reverse=True,
        )

    # ── Predictions ──────────────────────────────

    def save_prediction(self, prediction_data: dict) -> None:
        prediction_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._predictions.append(prediction_data)

    def get_prediction_history(self, limit: int = 50) -> list[dict]:
        return self._predictions[-limit:]

    # ── Stats ──────────────────────────────

    def get_stats(self) -> dict:
        """Dashboard statistics."""
        reports = self.get_all_reports()
        today = datetime.now(timezone.utc).date()
        today_reports = [
            r for r in reports
            if r.created_at.date() == today
        ]

        return {
            "total_reports": len(reports),
            "today_reports": len(today_reports),
            "pending_reports": len([r for r in reports if r.status.value == "pending"]),
            "verified_reports": len([r for r in reports if r.status.value == "officer_validated"]),
            "active_hotspots": len(self._hotspots),
            "total_violations": len(self._violations),
            "total_users": len(self._wallets),
            "total_tokens_distributed": sum(w.total_tokens for w in self._wallets.values()),
        }


def init_db() -> InMemoryDB:
    """Initialize the in-memory database. Called once per Streamlit session."""
    return InMemoryDB()
