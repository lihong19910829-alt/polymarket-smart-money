import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
DATA_API_BASE_URL = "https://data-api.polymarket.com"
ALERT_MIN_CURRENT_PRICE = Decimal("0.02")
ALERT_MIN_OUTRIGHT_PRICE = Decimal("0.05")


EXPERTISE_RULES = [
    ("Politics", ("election", "president", "senate", "congress", "democratic", "republican", "nomination", "minister")),
    ("Sports", ("fifa", "world cup", "nba", "nfl", "mlb", "nhl", "ufc", "champions league", "super bowl")),
    ("Crypto", ("bitcoin", "btc", "ethereum", "eth", "solana", "sol", "xrp", "crypto", "airdrop")),
    ("Macro", ("fed", "rate", "inflation", "cpi", "gdp", "recession", "tariff", "oil")),
    ("Culture", ("movie", "album", "grammy", "oscar", "box office", "celebrity", "streaming")),
    ("Tech", ("openai", "apple", "tesla", "nvidia", "google", "meta", "ai", "spacex")),
]


def decimal_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(Decimal(str(value)))
    except Exception:
        return None


def decimal_value(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def clamp_decimal(value: Decimal, floor: Decimal = Decimal("0"), ceiling: Decimal = Decimal("100")) -> Decimal:
    return max(floor, min(ceiling, value))


def score_to_label(score: Decimal) -> str:
    if score >= Decimal("80"):
        return "strong"
    if score >= Decimal("60"):
        return "good"
    if score >= Decimal("40"):
        return "mixed"
    return "weak"


def short_address(value: Any) -> str | None:
    if value is None or value == "":
        return None
    raw = str(value).strip()
    return f"{raw[:4]}...{raw[-4:]}" if len(raw) > 10 else raw


def is_address_like_name(value: Any, address: Any = None) -> bool:
    if value is None or value == "":
        return False
    normalized = str(value).strip().lower()
    normalized_address = str(address or "").strip().lower()
    if normalized_address and normalized == normalized_address:
        return True
    compact = normalized.replace("...", "")
    if normalized.startswith("0x") and len(normalized) >= 10:
        return True
    return bool(normalized_address and compact and compact in normalized_address.replace("...", ""))


def display_name_from_row(row: dict[str, Any], address: Any) -> str | None:
    for key in ("name", "profileName", "pseudonym", "userName"):
        value = row.get(key)
        if value and not is_address_like_name(value, address):
            return str(value)
    return None


def profile_scores(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "quality_score": profile.get("quality_score"),
        "performance_score": profile.get("performance_score"),
        "hold_quality_score": profile.get("hold_quality_score"),
        "copyability_score": profile.get("copyability_score"),
        "copyability_label": profile.get("copyability_label"),
    }


def alert_wallet_summary(
    wallet: dict[str, Any],
    profile: dict[str, Any],
    *,
    primary: str | None,
    position: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "address": wallet.get("address"),
        "profile_url": wallet.get("profile_url"),
        "name": wallet.get("name"),
        "rating": profile.get("rating") or "WATCH",
        **profile_scores(profile),
        "expertise": primary,
        "rank": wallet.get("rank"),
    }
    if position:
        summary.update(
            {
                "entry_time": position.get("entry_time"),
                "size": position.get("size"),
                "avg_price": position.get("avg_price"),
                "current_price": position.get("current_price"),
            }
        )
    return summary


def parse_arrayish(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str):
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [item.strip().strip('"') for item in value.strip("[]").split(",") if item.strip()]
    return parsed if isinstance(parsed, list) else []


def current_price_from_row(row: dict[str, Any], outcome: Any) -> Any:
    direct = (
        row.get("curPrice")
        or row.get("currentPrice")
        or row.get("price")
        or row.get("markPrice")
        or row.get("lastPrice")
        or row.get("outcomePrice")
    )
    if direct not in {None, ""}:
        return direct

    current_value = decimal_value(row.get("currentValue") or row.get("value"))
    size = decimal_value(row.get("size") or row.get("amount") or row.get("balance"))
    if current_value is not None and size is not None and size > 0:
        return current_value / size

    prices = parse_arrayish(row.get("outcomePrices") or row.get("prices"))
    outcomes = parse_arrayish(row.get("outcomes"))
    outcome_index = row.get("outcomeIndex") or row.get("outcome_index")
    if outcome_index is not None:
        try:
            return prices[int(outcome_index)]
        except (IndexError, TypeError, ValueError):
            pass

    if outcome and outcomes and len(outcomes) == len(prices):
        normalized_outcome = str(outcome).strip().lower()
        for index, item in enumerate(outcomes):
            if str(item).strip().lower() == normalized_outcome:
                return prices[index]
    if len(prices) == 1:
        return prices[0]
    return None


def datetime_text(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def is_false(value: Any) -> bool:
    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no"}
    return False


def is_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def is_live_position(position: dict[str, Any]) -> bool:
    if is_true(position.get("closed")) or is_false(position.get("active")):
        return False
    size = decimal_value(position.get("size"))
    if size is not None and size <= 0:
        return False
    current_price = decimal_value(position.get("current_price"))
    if current_price is not None and current_price <= ALERT_MIN_CURRENT_PRICE:
        return False
    question = str(position.get("question") or "").lower()
    if "world cup" in question and "win" in question and (
        current_price is None or current_price < ALERT_MIN_OUTRIGHT_PRICE
    ):
        return False
    end_at = parse_datetime(position.get("end_date"))
    return end_at is None or end_at > datetime.now(UTC)


def as_list(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


async def fetch_json(url: str, params: dict[str, Any] | None = None) -> Any:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def fetch_json_with_client(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
) -> Any:
    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def normalize_live_market(row: dict[str, Any]) -> dict[str, Any]:
    market_id = str(row.get("id") or row.get("marketId") or row.get("conditionId") or "")
    outcomes = row.get("outcomes") or []
    prices = row.get("outcomePrices") or []
    if isinstance(outcomes, str):
        outcomes = [item.strip().strip('"') for item in outcomes.strip("[]").split(",") if item.strip()]
    if isinstance(prices, str):
        prices = [item.strip().strip('"') for item in prices.strip("[]").split(",") if item.strip()]
    return {
        "market_id": market_id,
        "question": row.get("question") or row.get("title") or market_id,
        "slug": row.get("slug"),
        "category": row.get("category") or row.get("groupItemTitle"),
        "active": row.get("active"),
        "closed": row.get("closed"),
        "volume_24h": decimal_text(row.get("volume24hr") or row.get("volume24h")),
        "volume_total": decimal_text(row.get("volume")),
        "liquidity": decimal_text(row.get("liquidity")),
        "end_date": row.get("endDate") or row.get("endDateIso"),
        "outcomes": outcomes[:4],
        "outcome_prices": prices[:4],
        "url": f"https://polymarket.com/event/{row.get('slug')}" if row.get("slug") else None,
    }


def normalize_live_leader(row: dict[str, Any], rank: int) -> dict[str, Any]:
    address = row.get("proxyWallet") or row.get("wallet") or row.get("address") or row.get("user")
    return {
        "rank": row.get("rank") or rank,
        "address": address,
        "profile_url": f"https://polymarket.com/profile/{address}" if address else None,
        "name": display_name_from_row(row, address),
        "pnl": decimal_text(row.get("pnl") or row.get("profit")),
        "volume": decimal_text(row.get("volume") or row.get("vol")),
        "raw": row,
    }


def infer_position_expertise(position: dict[str, Any]) -> str:
    haystack = " ".join(
        str(value or "")
        for value in [
            position.get("category"),
            position.get("question"),
            position.get("slug"),
            position.get("market_id"),
        ]
    ).lower()
    for label, keywords in EXPERTISE_RULES:
        if any(keyword in haystack for keyword in keywords):
            return label
    category = str(position.get("category") or "").strip()
    if category:
        return category[:40]
    return "General"


def wallet_expertise(positions: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for position in positions:
        label = infer_position_expertise(position)
        counts[label] = counts.get(label, 0) + 1
    if not counts:
        return {"primary": "Unknown", "secondary": [], "distribution": {}}

    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {
        "primary": ranked[0][0],
        "secondary": [label for label, _count in ranked[1:3]],
        "distribution": dict(ranked),
    }


def wallet_position_quality(wallet: dict[str, Any], positions: list[dict[str, Any]]) -> dict[str, Any]:
    live_positions = [position for position in positions if is_live_position(position)]
    pnl = decimal_value(wallet.get("pnl")) or Decimal("0")
    volume = decimal_value(wallet.get("volume")) or Decimal("0")

    performance_score = Decimal("35")
    if pnl > 0:
        performance_score += min(pnl / Decimal("20000"), Decimal("1")) * Decimal("45")
    elif pnl < 0:
        performance_score -= min(abs(pnl) / Decimal("10000"), Decimal("1")) * Decimal("20")
    if volume > 0 and pnl > 0:
        roi_proxy = pnl / volume
        performance_score += clamp_decimal(roi_proxy * Decimal("250"), Decimal("0"), Decimal("20"))
    performance_score = clamp_decimal(performance_score)

    holding_ages: list[Decimal] = []
    conviction_scores: list[Decimal] = []
    profitable_positions = 0
    priced_positions = 0
    now = datetime.now(UTC)
    for position in live_positions:
        entry_at = parse_datetime(position.get("entry_time"))
        if entry_at is not None:
            holding_ages.append(Decimal(str(max(0, (now - entry_at).total_seconds() / 86400))))

        avg_price = decimal_value(position.get("avg_price"))
        current_price = decimal_value(position.get("current_price"))
        if avg_price is not None and current_price is not None:
            priced_positions += 1
            if current_price >= avg_price:
                profitable_positions += 1
            conviction_scores.append(clamp_decimal((current_price - avg_price) * Decimal("100") + Decimal("50")))

    avg_holding_days = sum(holding_ages, Decimal("0")) / Decimal(len(holding_ages)) if holding_ages else Decimal("0")
    hold_score = Decimal("45")
    hold_score += min(avg_holding_days / Decimal("14"), Decimal("1")) * Decimal("25")
    if conviction_scores:
        hold_score += (sum(conviction_scores, Decimal("0")) / Decimal(len(conviction_scores)) - Decimal("50")) * Decimal("0.3")
    if live_positions:
        hold_score += min(Decimal(len(live_positions)) / Decimal("8"), Decimal("1")) * Decimal("10")
    hold_score = clamp_decimal(hold_score)

    churn_penalty = Decimal("0")
    if len(live_positions) >= 8 and avg_holding_days < Decimal("2"):
        churn_penalty += Decimal("18")
    elif len(live_positions) >= 5 and avg_holding_days < Decimal("1"):
        churn_penalty += Decimal("10")
    if volume > 0 and pnl <= 0:
        churn_penalty += Decimal("10")

    copyability_score = clamp_decimal(performance_score * Decimal("0.45") + hold_score * Decimal("0.45") - churn_penalty)
    if priced_positions:
        position_win_rate = Decimal(profitable_positions) / Decimal(priced_positions)
        copyability_score = clamp_decimal(copyability_score + (position_win_rate - Decimal("0.5")) * Decimal("20"))
    else:
        position_win_rate = None

    return {
        "performance_score": str(performance_score.quantize(Decimal("0.01"))),
        "hold_quality_score": str(hold_score.quantize(Decimal("0.01"))),
        "copyability_score": str(copyability_score.quantize(Decimal("0.01"))),
        "avg_open_holding_days": str(avg_holding_days.quantize(Decimal("0.01"))),
        "live_position_count": len(live_positions),
        "priced_position_count": priced_positions,
        "open_position_win_rate": str(position_win_rate.quantize(Decimal("0.01"))) if position_win_rate is not None else None,
        "churn_penalty": str(churn_penalty.quantize(Decimal("0.01"))),
        "copyability_label": score_to_label(copyability_score),
    }


def wallet_live_profile(wallet: dict[str, Any], positions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pnl = Decimal(wallet.get("pnl") or "0")
    volume = Decimal(wallet.get("volume") or "0")
    rank = int(wallet.get("rank") or 999999)
    positions = positions or []
    project_count = len({position.get("market_id") for position in positions if position.get("market_id")})

    position_quality = wallet_position_quality(wallet, positions)
    copyability = Decimal(position_quality["copyability_score"])

    quality = Decimal("35")
    if rank <= 10:
        quality += Decimal("25")
    elif rank <= 50:
        quality += Decimal("15")
    if pnl > 0:
        quality += min(pnl / Decimal("10000"), Decimal("1")) * Decimal("20")
    if volume > 0:
        quality += min(volume / Decimal("250000"), Decimal("1")) * Decimal("15")
    quality += min(Decimal(project_count) / Decimal("10"), Decimal("1")) * Decimal("5")
    quality += (copyability - Decimal("50")) * Decimal("0.2")
    quality = min(Decimal("100"), quality).quantize(Decimal("0.01"))

    if volume >= Decimal("1000000") and pnl > 0:
        label = "HIGH_VOLUME_WINNER"
    elif rank <= 20 and pnl > 0:
        label = "TOP_PNL"
    elif project_count >= 5:
        label = "DIVERSIFIED_ACTIVE"
    elif pnl < 0 and volume > Decimal("100000"):
        label = "HIGH_VOLUME_LOSS"
    else:
        label = "OBSERVATION"

    if quality >= Decimal("85"):
        rating = "S"
    elif quality >= Decimal("72"):
        rating = "A"
    elif quality >= Decimal("58"):
        rating = "B"
    elif quality >= Decimal("42"):
        rating = "C"
    else:
        rating = "WATCH"

    return {
        "label": label,
        "rating": rating,
        "quality_score": str(quality),
        **position_quality,
        "expertise": wallet_expertise(positions),
        "evidence": {
            "rank": rank,
            "reported_pnl": str(pnl),
            "reported_volume": str(volume),
            "open_project_count": project_count,
            "method": "live_leaderboard_and_current_positions_v2",
            "scoring_note": "Performance uses public leaderboard PnL/volume; hold quality and copyability use currently visible open positions as a conservative live proxy.",
        },
    }


def live_alerts(wallets: list[dict[str, Any]], *, limit: int = 30) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    same_direction: dict[tuple[str, str], dict[str, Any]] = {}

    for wallet in wallets:
        address = wallet.get("address")
        profile = wallet.get("classification") or {}
        expertise = profile.get("expertise") or {}
        primary = expertise.get("primary")
        rating = profile.get("rating") or "WATCH"
        positions = [position for position in wallet.get("positions", []) if is_live_position(position)]
        if primary and primary not in {"Unknown", "General"}:
            matches = [
                position
                for position in positions
                if infer_position_expertise(position) == primary
            ]
            if matches:
                first = matches[0]
                alerts.append(
                    {
                        "alert_type": "EXPERTISE_OPEN_POSITION",
                        "severity": "HIGH" if rating in {"S", "A"} else "WATCH",
                        "title": f"{primary} specialist opened/holds matching positions",
                        "wallet": address,
                        "profile_url": wallet.get("profile_url"),
                        "name": wallet.get("name"),
                        "rating": rating,
                        **profile_scores(profile),
                        "expertise": primary,
                        "market_id": first.get("market_id"),
                        "question": first.get("question"),
                        "url": first.get("url"),
                        "direction": first.get("outcome"),
                        "entry_time": first.get("entry_time"),
                        "size": first.get("size"),
                        "avg_price": first.get("avg_price"),
                        "current_price": first.get("current_price"),
                        "end_date": first.get("end_date"),
                        "matched_positions": len(matches),
                        "position_details": matches[:5],
                        "reason": "wallet current positions overlap its primary expertise",
                    }
                )

        for position in positions:
            market_id = str(position.get("market_id") or "")
            direction = str(position.get("outcome") or "").strip()
            if not market_id or not direction:
                continue
            key = (market_id, direction.lower())
            group = same_direction.setdefault(
                key,
                {
                    "market_id": market_id,
                    "question": position.get("question"),
                    "url": position.get("url"),
                    "direction": direction,
                    "wallets": [],
                },
            )
            if address and address not in {item["address"] for item in group["wallets"]}:
                group["wallets"].append(alert_wallet_summary(wallet, profile, primary=primary, position=position))

    for group in same_direction.values():
        wallet_count = len(group["wallets"])
        if wallet_count < 2:
            continue
        strong_count = sum(1 for wallet in group["wallets"] if wallet.get("rating") in {"S", "A"})
        alerts.append(
            {
                "alert_type": "SAME_DIRECTION_CLUSTER",
                "severity": "HIGH" if strong_count >= 2 else "WATCH",
                "title": "Multiple tracked wallets share the same direction",
                "market_id": group["market_id"],
                "question": group["question"],
                "url": group["url"],
                "direction": group["direction"],
                "wallet_count": wallet_count,
                "strong_wallet_count": strong_count,
                "wallets": group["wallets"],
                "reason": "same project and same outcome across multiple addresses",
            }
        )

    severity_rank = {"HIGH": 0, "WATCH": 1}
    alerts.sort(
        key=lambda alert: (
            severity_rank.get(str(alert.get("severity")), 9),
            str(alert.get("alert_type")),
            str(alert.get("question") or alert.get("wallet") or ""),
        )
    )
    return alerts[:limit]


def count_distribution(values: list[str | None]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def live_advanced_alerts(wallets: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    same_direction: dict[tuple[str, str], dict[str, Any]] = {}
    same_expertise: dict[tuple[str, str], dict[str, Any]] = {}

    for wallet in wallets:
        address = wallet.get("address")
        profile = wallet.get("classification") or {}
        expertise = profile.get("expertise") or {}
        primary = expertise.get("primary")
        wallet_summary = alert_wallet_summary(wallet, profile, primary=primary)
        positions = [position for position in wallet.get("positions", []) if is_live_position(position)]

        for position in positions:
            market_id = str(position.get("market_id") or "")
            direction = str(position.get("outcome") or "").strip()
            if not market_id or not direction or not address:
                continue

            direction_key = (market_id, direction.lower())
            direction_group = same_direction.setdefault(
                direction_key,
                {
                    "market_id": market_id,
                    "question": position.get("question"),
                    "url": position.get("url"),
                    "direction": direction,
                    "wallets": [],
                },
            )
            if address not in {item["address"] for item in direction_group["wallets"]}:
                direction_group["wallets"].append(
                    {
                        **wallet_summary,
                        "entry_time": position.get("entry_time"),
                        "size": position.get("size"),
                        "avg_price": position.get("avg_price"),
                        "current_price": position.get("current_price"),
                    }
                )

            if primary and primary not in {"Unknown", "General"}:
                expertise_key = (market_id, primary)
                expertise_group = same_expertise.setdefault(
                    expertise_key,
                    {
                        "market_id": market_id,
                        "question": position.get("question"),
                        "url": position.get("url"),
                        "expertise": primary,
                        "wallets": [],
                        "directions": [],
                    },
                )
                if address not in {item["address"] for item in expertise_group["wallets"]}:
                    expertise_group["wallets"].append(
                        {
                            **wallet_summary,
                            "entry_time": position.get("entry_time"),
                            "size": position.get("size"),
                            "avg_price": position.get("avg_price"),
                            "current_price": position.get("current_price"),
                        }
                    )
                    expertise_group["directions"].append(direction)

    for group in same_direction.values():
        wallet_count = len(group["wallets"])
        if wallet_count < 4:
            continue
        strong_count = sum(1 for wallet in group["wallets"] if wallet.get("rating") in {"S", "A"})
        alerts.append(
            {
                "alert_type": "ADVANCED_SAME_DIRECTION_CONSENSUS",
                "severity": "CRITICAL" if wallet_count >= 5 or strong_count >= 3 else "HIGH",
                "title": "4+ tracked wallets share the same market direction",
                "market_id": group["market_id"],
                "question": group["question"],
                "url": group["url"],
                "direction": group["direction"],
                "wallet_count": wallet_count,
                "strong_wallet_count": strong_count,
                "expertise_distribution": count_distribution(
                    [wallet.get("expertise") for wallet in group["wallets"]]
                ),
                "wallets": group["wallets"],
                "reason": "four or more tracked wallets hold the same outcome on the same market",
            }
        )

    for group in same_expertise.values():
        wallet_count = len(group["wallets"])
        direction_distribution = count_distribution(group["directions"])
        dominant_direction_count = max(direction_distribution.values(), default=0)
        strong_count = sum(1 for wallet in group["wallets"] if wallet.get("rating") in {"S", "A"})
        if wallet_count < 3 and not (wallet_count >= 2 and dominant_direction_count >= 2 and strong_count >= 1):
            continue
        alerts.append(
            {
                "alert_type": "ADVANCED_SAME_EXPERTISE_CONSENSUS",
                "severity": "CRITICAL"
                if dominant_direction_count >= 3 or (dominant_direction_count >= 2 and strong_count >= 2)
                else "HIGH",
                "title": "Same-expertise wallets converge in one market",
                "market_id": group["market_id"],
                "question": group["question"],
                "url": group["url"],
                "expertise": group["expertise"],
                "direction": next(iter(direction_distribution), None),
                "direction_distribution": direction_distribution,
                "wallet_count": wallet_count,
                "strong_wallet_count": strong_count,
                "wallets": group["wallets"],
                "reason": "same-expertise wallets are clustered in this market; two-wallet cases require same direction and at least one strong wallet",
            }
        )

    severity_rank = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
    alerts.sort(
        key=lambda alert: (
            severity_rank.get(str(alert.get("severity")), 9),
            -int(alert.get("wallet_count") or 0),
            str(alert.get("alert_type")),
            str(alert.get("question") or ""),
        )
    )
    return alerts[:limit]


def normalize_live_position(row: dict[str, Any]) -> dict[str, Any]:
    market_id = str(
        row.get("market")
        or row.get("marketId")
        or row.get("conditionId")
        or row.get("condition_id")
        or row.get("market_id")
        or ""
    )
    slug = row.get("slug") or row.get("eventSlug") or row.get("marketSlug")
    question = row.get("title") or row.get("question") or row.get("marketTitle") or row.get("eventTitle") or market_id
    outcome = row.get("outcome") or row.get("outcomeName")
    current_price = current_price_from_row(row, outcome)
    return {
        "market_id": market_id,
        "question": question,
        "slug": slug,
        "category": row.get("category") or row.get("eventCategory"),
        "active": row.get("active"),
        "closed": row.get("closed"),
        "end_date": row.get("endDate") or row.get("endDateIso") or row.get("marketEndDate"),
        "outcome": outcome,
        "size": decimal_text(row.get("size") or row.get("amount") or row.get("balance")),
        "avg_price": decimal_text(row.get("avgPrice") or row.get("averagePrice")),
        "current_price": decimal_text(current_price),
        "entry_time": datetime_text(
            row.get("entryTime")
            or row.get("createdAt")
            or row.get("created_at")
            or row.get("timestamp")
            or row.get("lastTradeTime")
        ),
        "cash_pnl": decimal_text(row.get("cashPnl") or row.get("realizedPnl") or row.get("pnl")),
        "percent_pnl": decimal_text(row.get("percentPnl") or row.get("percentPnL")),
        "url": f"https://polymarket.com/event/{slug}" if slug else None,
    }


async def live_wallet_positions(address: str, limit: int = 20) -> dict[str, Any]:
    payload = await fetch_json(
        f"{DATA_API_BASE_URL}/positions",
        {"user": address, "limit": limit, "offset": 0},
    )
    rows = as_list(payload, "positions", "data")
    return {
        "status": "ok",
        "source": "data-api.polymarket.com/positions",
        "fetched_at": datetime.now(UTC).isoformat(),
        "wallet": address,
        "positions": [normalize_live_position(row) for row in rows[:limit]],
    }


async def live_wallets_enriched(limit: int = 20, positions_per_wallet: int = 8) -> dict[str, Any]:
    leaderboard = await live_leaderboard(limit)
    wallets = leaderboard.get("wallets", [])
    async with httpx.AsyncClient(timeout=20) as client:
        position_payloads = []
        for wallet in wallets:
            address = wallet.get("address")
            if not address:
                position_payloads.append(None)
                continue
            try:
                payload = await fetch_json_with_client(
                    client,
                    f"{DATA_API_BASE_URL}/positions",
                    {"user": address, "limit": positions_per_wallet, "offset": 0},
                )
                position_payloads.append(payload)
            except Exception:
                position_payloads.append(None)

    enriched = []
    for wallet, payload in zip(wallets, position_payloads, strict=False):
        positions = [normalize_live_position(row) for row in as_list(payload, "positions", "data")[:positions_per_wallet]]
        profile = wallet_live_profile(wallet, positions)
        enriched.append({**wallet, "classification": profile, "positions": positions})

    return {
        "status": "ok",
        "source": "data-api.polymarket.com/v1/leaderboard + /positions",
        "fetched_at": datetime.now(UTC).isoformat(),
        "wallets": enriched,
        "alerts": live_alerts(enriched),
        "advanced_alerts": live_advanced_alerts(enriched),
    }


async def live_project_participants(project_key: str, limit: int = 30) -> dict[str, Any]:
    enriched = await live_wallets_enriched(limit=limit, positions_per_wallet=20)
    normalized_key = project_key.lower()
    participants = []
    for wallet in enriched.get("wallets", []):
        matches = []
        for position in wallet.get("positions", []):
            haystack = " ".join(
                str(value or "")
                for value in [
                    position.get("market_id"),
                    position.get("slug"),
                    position.get("question"),
                    position.get("category"),
                ]
            ).lower()
            if normalized_key in haystack:
                matches.append(position)
        if matches:
            participants.append(
                {
                    "address": wallet.get("address"),
                    "profile_url": wallet.get("profile_url"),
                    "rank": wallet.get("rank"),
                    "name": wallet.get("name"),
                    "classification": wallet.get("classification"),
                    "positions": matches,
                }
            )
    return {
        "status": "ok",
        "source": "live_leaderboard_position_scan",
        "fetched_at": datetime.now(UTC).isoformat(),
        "project_key": project_key,
        "scanned_wallets": len(enriched.get("wallets", [])),
        "participants": participants,
        "alerts": live_alerts(participants),
        "advanced_alerts": live_advanced_alerts(participants),
    }


async def live_markets(limit: int = 20) -> dict[str, Any]:
    payload = await fetch_json(
        f"{GAMMA_BASE_URL}/markets",
        {"active": "true", "closed": "false", "limit": limit, "offset": 0},
    )
    rows = as_list(payload, "markets", "data")
    normalized = [normalize_live_market(row) for row in rows]
    normalized.sort(key=lambda row: Decimal(row["volume_24h"] or row["volume_total"] or "0"), reverse=True)
    return {
        "status": "ok",
        "source": "gamma-api.polymarket.com/markets",
        "fetched_at": datetime.now(UTC).isoformat(),
        "markets": normalized[:limit],
    }


async def live_leaderboard(limit: int = 20) -> dict[str, Any]:
    payload = await fetch_json(
        f"{DATA_API_BASE_URL}/v1/leaderboard",
        {
            "category": "OVERALL",
            "timePeriod": "MONTH",
            "orderBy": "PNL",
            "limit": limit,
            "offset": 0,
        },
    )
    rows = as_list(payload, "leaderboard", "data", "users")
    return {
        "status": "ok",
        "source": "data-api.polymarket.com/v1/leaderboard",
        "fetched_at": datetime.now(UTC).isoformat(),
        "wallets": [normalize_live_leader(row, index + 1) for index, row in enumerate(rows[:limit])],
    }


async def live_overview(limit: int = 20) -> dict[str, Any]:
    markets_result: dict[str, Any]
    leaderboard_result: dict[str, Any]
    try:
        markets_result = await live_markets(limit)
    except Exception as exc:
        markets_result = {"status": "error", "error": str(exc), "markets": []}
    try:
        leaderboard_result = await live_leaderboard(limit)
    except Exception as exc:
        leaderboard_result = {"status": "error", "error": str(exc), "wallets": []}
    return {
        "status": "ok",
        "mode": "live_public_api",
        "realtime": True,
        "refresh_policy": "fresh public API request per dashboard load",
        "fetched_at": datetime.now(UTC).isoformat(),
        "markets": markets_result,
        "leaderboard": leaderboard_result,
    }
