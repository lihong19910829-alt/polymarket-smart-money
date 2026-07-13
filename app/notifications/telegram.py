from typing import Any

import httpx

from app.core.config import get_settings


def render_signal_message(signal: dict[str, Any]) -> str:
    participants = signal.get("participant_summary", {})
    risks = signal.get("risk_flags", [])
    return "\n".join(
        [
            "[Polymarket Smart Money Consensus]",
            f"Market: {signal.get('market_id')}",
            f"Direction: {signal.get('direction')}",
            f"Current price: {signal.get('current_price')}",
            f"Weighted entry: {signal.get('weighted_entry_price')}",
            f"Price drift: {signal.get('price_drift')}",
            f"Consensus score: {signal.get('score')}",
            f"Copyability: {signal.get('copyability_score')}",
            "",
            "Participants:",
            f"S: {participants.get('s_count', 0)} A: {participants.get('a_count', 0)} B: {participants.get('b_count', 0)}",
            f"Independent wallets: {participants.get('wallet_count', 0)}",
            f"Independent clusters: {participants.get('cluster_count', 0)}",
            "",
            "Risks:",
            *(f"- {risk}" for risk in risks[:8]),
            "",
            "This is analysis only, not an auto-trading instruction.",
        ]
    )


async def send_telegram_message(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("telegram credentials are not configured")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": text})
        response.raise_for_status()
    return True

