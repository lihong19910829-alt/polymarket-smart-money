# Strategy Inference

V1 uses deterministic labels until enough historical data exists for walk-forward modeling:

- `HOLD_TO_RESOLUTION`
- `MOMENTUM`
- `MARKET_MAKING`
- `UNEXPLAINED`

The classifier returns confidence and evidence. The rule generator refuses to invent unsupported stories and marks wallets as `UNEXPLAINED` when the evidence is weak.

Future model training should use time splits and event isolation, never random train/test splits.

