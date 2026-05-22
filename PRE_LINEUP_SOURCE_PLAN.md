# Pre-Lineup Source Plan

Purpose: add a true `pre_lineup` path without leaking confirmed post-lineup information into pre-game evaluation.

## Current State

- 2021-2025 standardized `lineups.csv` files contain only `prediction_mode=confirmed_lineup`.
- `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv` contains only `confirmed_lineup` features.
- `FeatureBuilder(prediction_mode="pre_lineup")` now filters only `pre_lineup`, `projected`, or `expected` lineup rows. It does not fall back to confirmed rows when no pre-lineup rows exist.

## Source Candidates

| source | role | status | notes |
| --- | --- | --- | --- |
| MLB Stats API / MLB.com starting lineups | confirmed lineup source | keep for confirmed lineup | Useful once official lineups are posted. Not enough for projected lineups before announcement. |
| RotoWire daily lineups | expected and confirmed lineup source | candidate | Public pages expose expected/confirmed lineup states. Need ToS review before automation. |
| Lineups.com MLB lineups | expected and confirmed lineup source | candidate | Similar public expected/confirmed lineup signal. Need stable parsing and ToS review. |
| BALLDONTLIE MLB Lineups API | API candidate | candidate for 2026+ | Search result indicates pre-game lineups and probable pitchers from 2026 season. Need API terms, cost, schema, historical depth. |
| Manual snapshot CSV | fallback / smoke test | recommended first | Use a small hand-curated projected lineup CSV to validate schema and feature build before automating external collection. |

## Target Standard Columns

Required:

- `game_id`
- `team`
- `player_id`
- `batting_order`
- `prediction_mode`

Recommended:

- `lineup_source`
- `lineup_confidence`
- `is_available`
- `is_expected_starter`
- `rest_signal`
- `injury_status`
- `bats`
- `captured_at`

Accepted `prediction_mode` aliases:

- `pre_lineup`
- `projected`
- `expected`

## Validation Rules

- A `pre_lineup` feature build must not use `confirmed_lineup` rows.
- If no projected rows are available, lineup-derived features should remain null rather than silently backfilling confirmed lineups.
- Every external source snapshot should preserve `captured_at` so later evaluation can verify it was available before first pitch.
- Confirmed lineups remain the backtest upper-bound scenario, not the deployable pre-game score.

## Next Implementation Steps

1. Create a small `data/smoke_pre_lineup/lineups_projected.csv` with projected rows for a few historical games.
2. Run `build-features --prediction-mode pre_lineup` against the smoke source.
3. Compare feature null rates against confirmed-lineup features.
4. Choose one automated source only after schema and ToS review.
5. Add collector/normalizer for the chosen source.

## References

- MLB starting lineups: https://www.mlb.com/starting-lineups
- RotoWire daily MLB lineups: https://www.rotowire.com/baseball/daily-lineups.php
- Lineups.com MLB lineups: https://www.lineups.com/mlb/lineups/
- BALLDONTLIE MLB API: https://mlb.balldontlie.io/
