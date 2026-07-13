from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "live-dashboard-snapshot.html"


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": "polymarket-smart-money/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def rows(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def decimal_text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    try:
        return f"{Decimal(str(value)):,.2f}"
    except (InvalidOperation, ValueError):
        return "-"


def text(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def safe_html(value: Any) -> str:
    return (
        text(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def market_url(slug: Any) -> str | None:
    if not slug:
        return None
    slug_text = urllib.parse.quote(str(slug), safe="")
    return f"https://polymarket.com/event/{slug_text}"


def normalize_markets(payload: Any) -> list[dict[str, Any]]:
    normalized = []
    for row in rows(payload, "markets", "data"):
        volume = row.get("volume24hr") or row.get("volume24h") or row.get("volume")
        normalized.append(
            {
                "question": row.get("question") or row.get("title") or row.get("slug"),
                "category": row.get("category") or row.get("groupItemTitle"),
                "volume": volume,
                "liquidity": row.get("liquidity"),
                "url": market_url(row.get("slug")),
            }
        )

    def sort_key(item: dict[str, Any]) -> Decimal:
        try:
            return Decimal(str(item.get("volume") or "0"))
        except InvalidOperation:
            return Decimal("0")

    normalized.sort(key=sort_key, reverse=True)
    return normalized[:20]


def normalize_wallets(payload: Any) -> list[dict[str, Any]]:
    normalized = []
    for index, row in enumerate(rows(payload, "leaderboard", "data", "users")[:20], start=1):
        normalized.append(
            {
                "rank": row.get("rank") or index,
                "address": row.get("proxyWallet") or row.get("wallet") or row.get("address") or row.get("user"),
                "name": row.get("name") or row.get("profileName") or row.get("pseudonym"),
                "pnl": row.get("pnl") or row.get("profit"),
                "volume": row.get("volume") or row.get("vol"),
            }
        )
    return normalized


def render(markets: list[dict[str, Any]], wallets: list[dict[str, Any]], fetched_at: str) -> str:
    market_rows = "\n".join(
        f"""
        <tr>
          <td>{f'<a href="{safe_html(row["url"])}" target="_blank" rel="noreferrer">{safe_html(row["question"])}</a>' if row.get("url") else safe_html(row.get("question"))}</td>
          <td>{safe_html(row.get("category"))}</td>
          <td>{decimal_text(row.get("volume"))}</td>
          <td>{decimal_text(row.get("liquidity"))}</td>
        </tr>"""
        for row in markets
    )
    wallet_rows = "\n".join(
        f"""
        <tr>
          <td>{safe_html(row.get("rank"))}</td>
          <td><code>{safe_html(row.get("address"))}</code></td>
          <td>{safe_html(row.get("name"))}</td>
          <td>{decimal_text(row.get("pnl"))}</td>
          <td>{decimal_text(row.get("volume"))}</td>
        </tr>"""
        for row in wallets
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Polymarket Live Snapshot</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #172026; background: #f4f7f9; }}
    header {{ padding: 22px 28px; background: #12343b; color: white; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    header p {{ margin: 0; color: #cfe2e6; }}
    main {{ padding: 24px; display: grid; gap: 18px; }}
    .metrics {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .metric, section {{ background: white; border: 1px solid #dce4ea; border-radius: 8px; padding: 18px; }}
    .metric span {{ display: block; color: #667985; font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 24px; }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #edf1f4; padding: 10px 8px; text-align: left; vertical-align: top; }}
    th {{ color: #667985; font-size: 12px; text-transform: uppercase; }}
    code {{ background: #eef3f5; border-radius: 4px; padding: 2px 5px; }}
    a {{ color: #0f6b8a; }}
  </style>
</head>
<body>
  <header>
    <h1>Polymarket Live Snapshot</h1>
    <p>Fetched from Polymarket public APIs at {safe_html(fetched_at)}.</p>
  </header>
  <main>
    <div class="metrics">
      <div class="metric"><span>Mode</span><strong>live snapshot</strong></div>
      <div class="metric"><span>Markets</span><strong>{len(markets)}</strong></div>
      <div class="metric"><span>Leaderboard</span><strong>{len(wallets)}</strong></div>
      <div class="metric"><span>Source</span><strong>Polymarket</strong></div>
    </div>
    <section>
      <h2>Active Markets</h2>
      <table>
        <thead><tr><th>Market</th><th>Category</th><th>Volume</th><th>Liquidity</th></tr></thead>
        <tbody>{market_rows}</tbody>
      </table>
    </section>
    <section>
      <h2>Leaderboard</h2>
      <table>
        <thead><tr><th>Rank</th><th>Wallet</th><th>Name</th><th>PnL</th><th>Volume</th></tr></thead>
        <tbody>{wallet_rows}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    markets_payload = fetch_json(
        "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=40&offset=0"
    )
    leaderboard_payload = fetch_json(
        "https://data-api.polymarket.com/v1/leaderboard?category=OVERALL&timePeriod=MONTH&orderBy=PNL&limit=20&offset=0"
    )
    fetched_at = datetime.now(UTC).isoformat()
    html = render(normalize_markets(markets_payload), normalize_wallets(leaderboard_payload), fetched_at)
    html = re.sub(r"\n{3,}", "\n\n", html)
    OUTPUT.write_text(html, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
