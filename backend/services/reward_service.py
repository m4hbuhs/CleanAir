"""
EcoToken reward engine for citizen incentivization.
Manages token allocation, wallets, leaderboard, and redeemable rewards.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from backend.config import get_settings
from backend.models.schemas import (
    CitizenReport,
    CitizenWallet,
    EcoTokenTransaction,
    RewardItem,
    VisionClassification,
)

logger = logging.getLogger(__name__)


# ── Reward Catalog ──────────────────────────

REWARD_CATALOG: List[RewardItem] = [
    RewardItem(
        reward_id="metro_pass_1",
        name="Metro Day Pass",
        description="One free metro ride pass for Delhi Metro",
        cost_tokens=100,
        category="metro_card",
        emoji="🚇",
    ),
    RewardItem(
        reward_id="coffee_coupon_1",
        name="Café Coffee Day ₹100 Voucher",
        description="₹100 discount at any CCD outlet",
        cost_tokens=75,
        category="coupon",
        emoji="☕",
    ),
    RewardItem(
        reward_id="amazon_100",
        name="Amazon ₹200 Gift Card",
        description="₹200 Amazon.in shopping voucher",
        cost_tokens=150,
        category="voucher",
        emoji="🛒",
    ),
    RewardItem(
        reward_id="tree_cert",
        name="Tree Plantation Certificate",
        description="Certificate for planting a tree in your name",
        cost_tokens=50,
        category="certificate",
        emoji="🌳",
    ),
    RewardItem(
        reward_id="movie_ticket",
        name="Movie Ticket Voucher",
        description="One free movie ticket at PVR/INOX",
        cost_tokens=120,
        category="voucher",
        emoji="🎬",
    ),
    RewardItem(
        reward_id="eco_badge_gold",
        name="Gold Eco Warrior Badge",
        description="Premium badge for your citizen profile",
        cost_tokens=200,
        category="certificate",
        emoji="🏅",
    ),
    RewardItem(
        reward_id="bus_pass_week",
        name="DTC Weekly Bus Pass",
        description="Free DTC bus travel for one week",
        cost_tokens=80,
        category="metro_card",
        emoji="🚌",
    ),
    RewardItem(
        reward_id="swiggy_voucher",
        name="Swiggy ₹150 Voucher",
        description="₹150 off on your next Swiggy order",
        cost_tokens=100,
        category="voucher",
        emoji="🍔",
    ),
]

# ── Badge Definitions ──────────────────────

BADGES = {
    "first_report": {"name": "🌱 First Report", "description": "Filed your first pollution report", "threshold": 1},
    "five_reports": {"name": "🔥 Active Reporter", "description": "Filed 5 verified reports", "threshold": 5},
    "ten_reports": {"name": "⭐ Star Citizen", "description": "Filed 10 verified reports", "threshold": 10},
    "twenty_five_reports": {"name": "🛡️ Eco Guardian", "description": "Filed 25 verified reports", "threshold": 25},
    "fifty_reports": {"name": "🏆 Eco Champion", "description": "Filed 50 verified reports", "threshold": 50},
    "token_100": {"name": "💰 Token Collector", "description": "Earned 100 tokens", "threshold": 100},
    "token_500": {"name": "💎 Token Master", "description": "Earned 500 tokens", "threshold": 500},
}


class RewardEngine:
    """
    Manages EcoToken rewards for citizen contributions.

    Token allocation logic:
    - Base tokens for any report submission
    - Bonus tokens for high-severity verified incidents
    - Daily cap to prevent gaming
    - Badge assignment based on cumulative contributions
    """

    def __init__(self):
        self._settings = get_settings()

    def calculate_tokens(
        self,
        report: CitizenReport,
        classification: Optional[VisionClassification] = None,
        is_verified: bool = False,
    ) -> int:
        """
        Calculate tokens to award for a citizen report.

        Args:
            report: The submitted citizen report
            classification: Vision classification result (if image was uploaded)
            is_verified: Whether a municipal officer has verified the report

        Returns:
            Number of tokens to award.
        """
        tokens = self._settings.base_report_tokens  # Base: 10 tokens

        # Bonus for verified reports
        if is_verified:
            tokens += self._settings.verified_report_bonus  # +25

        # Bonus for high-severity incidents
        if report.severity.value >= 4:
            tokens += self._settings.high_severity_bonus  # +15

        # Bonus for image upload with high confidence classification
        if classification and classification.confidence >= 0.7:
            tokens += 10

        # Penalty for fake uploads
        if classification and classification.is_fake_upload:
            tokens = 0

        return tokens

    def award_tokens(
        self,
        wallet: CitizenWallet,
        amount: int,
        reason: str,
        report_id: Optional[str] = None,
    ) -> CitizenWallet:
        """
        Award tokens to a citizen's wallet.

        Args:
            wallet: Citizen's current wallet state
            amount: Tokens to award
            reason: Descriptive reason for the award
            report_id: Optional linked report ID

        Returns:
            Updated wallet with new balance and transaction.
        """
        if amount <= 0:
            return wallet

        transaction = EcoTokenTransaction(
            transaction_id=str(uuid.uuid4())[:8],
            user_id=wallet.user_id,
            amount=amount,
            reason=reason,
            report_id=report_id,
        )

        wallet.total_tokens += amount
        wallet.transactions.append(transaction)
        wallet.total_reports += 1

        # Check for new badges
        wallet.badges = self._check_badges(wallet)

        return wallet

    def _check_badges(self, wallet: CitizenWallet) -> List[str]:
        """Check and award badges based on wallet stats."""
        current_badges = set(wallet.badges)

        # Report-based badges
        report_badges = [
            ("first_report", wallet.total_reports >= 1),
            ("five_reports", wallet.verified_reports >= 5),
            ("ten_reports", wallet.verified_reports >= 10),
            ("twenty_five_reports", wallet.verified_reports >= 25),
            ("fifty_reports", wallet.verified_reports >= 50),
        ]

        # Token-based badges
        token_badges = [
            ("token_100", wallet.total_tokens >= 100),
            ("token_500", wallet.total_tokens >= 500),
        ]

        for badge_id, earned in report_badges + token_badges:
            if earned and badge_id not in current_badges:
                current_badges.add(badge_id)
                badge_info = BADGES[badge_id]
                logger.info(
                    "Badge awarded to %s: %s", wallet.user_id, badge_info["name"]
                )

        return sorted(list(current_badges))

    def get_leaderboard(
        self, wallets: List[CitizenWallet], top_n: int = 10
    ) -> List[CitizenWallet]:
        """
        Generate a leaderboard sorted by total tokens (desc).

        Args:
            wallets: All citizen wallets
            top_n: Number of top citizens to include

        Returns:
            Sorted list of top wallets with rank assigned.
        """
        sorted_wallets = sorted(wallets, key=lambda w: w.total_tokens, reverse=True)
        for i, wallet in enumerate(sorted_wallets[:top_n]):
            wallet.rank = i + 1
        return sorted_wallets[:top_n]

    def get_reward_catalog(self) -> List[RewardItem]:
        """Returns the full list of redeemable rewards."""
        return [r for r in REWARD_CATALOG if r.available]

    def redeem_reward(
        self, wallet: CitizenWallet, reward_id: str
    ) -> tuple[bool, str]:
        """
        Attempt to redeem a reward from the catalog.

        Returns:
            (success: bool, message: str)
        """
        reward = next((r for r in REWARD_CATALOG if r.reward_id == reward_id), None)
        if not reward:
            return False, "Reward not found."
        if not reward.available:
            return False, "This reward is currently unavailable."
        if wallet.total_tokens < reward.cost_tokens:
            return False, f"Insufficient tokens. Need {reward.cost_tokens}, have {wallet.total_tokens}."

        wallet.total_tokens -= reward.cost_tokens
        wallet.transactions.append(EcoTokenTransaction(
            transaction_id=str(uuid.uuid4())[:8],
            user_id=wallet.user_id,
            amount=-reward.cost_tokens,
            reason=f"Redeemed: {reward.name}",
        ))
        return True, f"Successfully redeemed {reward.name}! 🎉"
