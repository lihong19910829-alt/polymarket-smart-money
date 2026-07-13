# Scoring

Wallet quality uses explainable components:

- Profit factor.
- Win rate.
- Positive month ratio.
- Sample size.
- Volume.
- Data completeness.

Risk currently penalizes drawdown relative to volume and incomplete data. Copyability is quality minus a risk haircut. Tiers are assigned as `S`, `A`, `B`, `C`, `OBSERVATION`, `LOW_QUALITY`, or `INSUFFICIENT_DATA`.

The evidence JSON stores every component used to compute the score.

