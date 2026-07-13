# Scheduling

The worker uses APScheduler in UTC.

Default jobs:

- Gamma market catalog every 5 minutes.
- Leaderboard discovery daily at 02:00 UTC.
- Holder discovery every 6 hours.

Recommended next jobs:

- CLOB snapshot capture every 1 to 5 minutes by market liquidity tier.
- S/A wallet position refresh at staggered minute marks.
- Data-quality scan after each large backfill and at least daily.
- Backtest refresh after monthly reclassification.
- Daily summary at 00:30 UTC.
- Monthly reclassification on the first day of the month at 03:00 UTC.
