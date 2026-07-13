import hashlib
import json
from decimal import Decimal
from typing import Any


def normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    return address.strip().lower()


def stable_hash(payload: Any) -> str:
    def default(value: Any) -> str:
        if isinstance(value, Decimal):
            return str(value)
        return repr(value)

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=default)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def trade_uid_from_parts(
    *,
    source: str,
    wallet_address: str,
    condition_id: str,
    token_id: str,
    side: str,
    price: Decimal,
    size: Decimal,
    trade_at: str,
    transaction_hash: str | None = None,
    log_index: int | None = None,
) -> str:
    if transaction_hash and log_index is not None:
        return f"chain:{transaction_hash.lower()}:{log_index}"
    return f"{source}:{stable_hash([wallet_address.lower(), condition_id, token_id, side, str(price), str(size), trade_at])}"

