"""
🏆 EcoTokens — Citizen rewards, wallet, leaderboard, and redemption.
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="EcoTokens | CleanAir", page_icon="🏆", layout="wide")

st.markdown("""
<div style="background: linear-gradient(135deg, #f57f17 0%, #ff8f00 50%, #f57f17 100%);
     padding: 2rem; border-radius: 16px; margin-bottom: 1.5rem;
     border: 1px solid rgba(255, 179, 0, 0.3); box-shadow: 0 8px 32px rgba(245, 127, 23, 0.4);">
    <h1 style="color: white; margin: 0; font-size: 2rem;">🏆 EcoToken Rewards</h1>
    <p style="color: #fff9c4; margin-top: 0.5rem;">
        Earn tokens for reporting pollution. Redeem for metro cards, vouchers, and certificates.
    </p>
</div>
""", unsafe_allow_html=True)

if "db" not in st.session_state:
    st.warning("⚠️ Please visit the main page first.")
    st.stop()

db = st.session_state.db
current_user = st.session_state.current_user
wallet = db.get_wallet(current_user)

# ── Wallet Overview ──────────────────────────
st.markdown("### 💰 Your Wallet")

w1, w2, w3, w4 = st.columns(4)
with w1:
    st.markdown(f"""
    <div style="background: linear-gradient(145deg, #1a1f2e, #252b3b); border: 1px solid rgba(255, 179, 0, 0.3);
         border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem; font-weight: 700; color: #FFB300;">🪙 {wallet.total_tokens}</div>
        <div style="color: #aaa; font-size: 0.85rem; text-transform: uppercase;">Total Tokens</div>
    </div>
    """, unsafe_allow_html=True)
with w2:
    st.markdown(f"""
    <div style="background: linear-gradient(145deg, #1a1f2e, #252b3b); border: 1px solid rgba(76, 175, 80, 0.3);
         border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem; font-weight: 700; color: #4CAF50;">📊 {wallet.total_reports}</div>
        <div style="color: #aaa; font-size: 0.85rem; text-transform: uppercase;">Total Reports</div>
    </div>
    """, unsafe_allow_html=True)
with w3:
    st.markdown(f"""
    <div style="background: linear-gradient(145deg, #1a1f2e, #252b3b); border: 1px solid rgba(33, 150, 243, 0.3);
         border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem; font-weight: 700; color: #2196F3;">✅ {wallet.verified_reports}</div>
        <div style="color: #aaa; font-size: 0.85rem; text-transform: uppercase;">Verified Reports</div>
    </div>
    """, unsafe_allow_html=True)
with w4:
    st.markdown(f"""
    <div style="background: linear-gradient(145deg, #1a1f2e, #252b3b); border: 1px solid rgba(156, 39, 176, 0.3);
         border-radius: 12px; padding: 1.5rem; text-align: center;">
        <div style="font-size: 2.5rem; font-weight: 700; color: #9C27B0;">🏅 {len(wallet.badges)}</div>
        <div style="color: #aaa; font-size: 0.85rem; text-transform: uppercase;">Badges Earned</div>
    </div>
    """, unsafe_allow_html=True)

# ── Badges ──────────────────────────────
st.markdown("---")
st.markdown("### 🏅 Your Badges")

from backend.services.reward_service import BADGES

if wallet.badges:
    badge_cols = st.columns(min(len(wallet.badges), 4))
    for i, badge_id in enumerate(wallet.badges):
        badge = BADGES.get(badge_id, {})
        with badge_cols[i % len(badge_cols)]:
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #1a2a1a, #1f3d1f); border: 1px solid #4CAF5044;
                 border-radius: 12px; padding: 1rem; text-align: center; margin: 0.25rem 0;">
                <div style="font-size: 1.5rem;">{badge.get('name', badge_id)}</div>
                <div style="color: #888; font-size: 0.75rem;">{badge.get('description', '')}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("No badges yet. Submit your first pollution report to earn the 🌱 First Report badge!")

# ── Leaderboard ──────────────────────────────
st.markdown("---")
st.markdown("### 🏆 Community Leaderboard")

from backend.services.reward_service import RewardEngine
reward_engine = RewardEngine()
all_wallets = db.get_all_wallets()
leaderboard = reward_engine.get_leaderboard(all_wallets, top_n=10)

if leaderboard:
    lb_data = []
    for w in leaderboard:
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(w.rank, f"#{w.rank}")
        is_me = "⭐" if w.user_id == current_user else ""
        lb_data.append({
            "Rank": rank_emoji,
            "Citizen": f"{w.display_name} {is_me}",
            "🪙 Tokens": w.total_tokens,
            "📊 Reports": w.total_reports,
            "✅ Verified": w.verified_reports,
            "🏅 Badges": len(w.badges),
        })

    st.dataframe(pd.DataFrame(lb_data), use_container_width=True, hide_index=True)
else:
    st.info("No citizens on the leaderboard yet.")

# ── Reward Catalog ──────────────────────────────
st.markdown("---")
st.markdown("### 🎁 Redeem Rewards")

catalog = reward_engine.get_reward_catalog()

reward_cols = st.columns(4)
for i, reward in enumerate(catalog):
    with reward_cols[i % 4]:
        can_afford = wallet.total_tokens >= reward.cost_tokens
        border_color = "rgba(76, 175, 80, 0.3)" if can_afford else "rgba(100, 100, 100, 0.2)"
        opacity = "1.0" if can_afford else "0.5"

        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #1a1f2e, #252b3b);
             border: 1px solid {border_color}; border-radius: 12px; padding: 1rem;
             text-align: center; margin-bottom: 0.5rem; opacity: {opacity};">
            <div style="font-size: 2rem;">{reward.emoji}</div>
            <div style="font-weight: 600; color: #fafafa; margin: 0.3rem 0;">{reward.name}</div>
            <div style="color: #888; font-size: 0.75rem;">{reward.description}</div>
            <div style="color: #FFB300; font-weight: 700; margin-top: 0.5rem;">🪙 {reward.cost_tokens}</div>
        </div>
        """, unsafe_allow_html=True)

        if can_afford:
            if st.button(f"Redeem", key=f"redeem_{reward.reward_id}", use_container_width=True):
                success, msg = reward_engine.redeem_reward(wallet, reward.reward_id)
                db.save_wallet(wallet)
                if success:
                    st.balloons()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

# ── Transaction History ──────────────────────────────
st.markdown("---")
st.markdown("### 📜 Transaction History")

if wallet.transactions:
    tx_data = []
    for tx in reversed(wallet.transactions[-20:]):
        tx_data.append({
            "ID": tx.transaction_id,
            "Amount": f"{'🪙 +' if tx.amount > 0 else '🔻 '}{tx.amount}",
            "Reason": tx.reason,
            "Time": tx.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    st.dataframe(pd.DataFrame(tx_data), use_container_width=True, hide_index=True)
else:
    st.info("No transactions yet. Submit a report to earn your first tokens!")
