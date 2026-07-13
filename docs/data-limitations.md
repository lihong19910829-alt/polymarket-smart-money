# Data Limitations

- Public API pagination can truncate history unless windows are recursively split.
- `/positions` is current state and must not replace trade history.
- Public Data API records can lack chain identifiers; chain logs are preferred when available.
- Similar behavior alone is weak evidence for identity clustering.
- Backtests must use post-signal executable prices with spread, slippage, capacity, and delay assumptions.
- The current backtest helper is intentionally conservative and does not assume a trade can fill at a smart-money wallet's own execution price.
- Market snapshot tables are not yet partition-managed; run retention jobs only after partition policy is implemented.
