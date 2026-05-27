# Pre-Lineup Source Plan

Purpose: add a true `pre_lineup` path without leaking confirmed post-lineup information into pre-game evaluation.

## Current State

- 2021-2025 standardized `lineups.csv` files contain only `prediction_mode=confirmed_lineup`.
- `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv` contains only `confirmed_lineup` features.
- `FeatureBuilder(prediction_mode="pre_lineup")` now filters only `pre_lineup`, `projected`, or `expected` lineup rows. It does not fall back to confirmed rows when no pre-lineup rows exist.

## Source Candidates

| source | role | status | notes |
| --- | --- | --- | --- |
| MLB Stats API / MLB.com starting lineups | official pre-game lineup snapshot | MVP implemented | Free and keyless. Useful once official lineups are posted, typically closer to first pitch. Not a speculative projected lineup source before announcement. |
| RotoWire daily lineups | expected and confirmed lineup source | candidate | Public pages expose expected/confirmed lineup states. Need ToS review before automation. |
| Lineups.com MLB lineups | expected and confirmed lineup source | candidate | Similar public expected/confirmed lineup signal. Need stable parsing and ToS review. |
| BALLDONTLIE MLB Lineups API | API candidate | MVP implemented | Public API candidate for 2026+ pre-game lineups and probable pitchers. Collector/normalizer exists; live use still requires API key, provider terms review, and provider-to-MLBAM ID mapping. |
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

## Implemented MVP

### MLB Stats API Official Snapshot

The free/keyless path is now the primary low-cost `pre_lineup` source:

```text
mlb-winprob collect-mlb-schedule \
  --start-date 2026-05-26 \
  --end-date 2026-05-26 \
  --output outputs/mlb_lineup_snapshot_smoke/schedule_2026-05-26.csv

mlb-winprob collect-mlb-lineup-snapshots \
  --games outputs/mlb_lineup_snapshot_smoke/schedule_2026-05-26.csv \
  --output-dir outputs/mlb_lineup_snapshot_smoke/boxscores \
  --manifest outputs/mlb_lineup_snapshot_smoke/manifest.csv

mlb-winprob standardize-mlb-boxscores \
  --schedule outputs/mlb_lineup_snapshot_smoke/schedule_2026-05-26.csv \
  --boxscore-dir outputs/mlb_lineup_snapshot_smoke/boxscores \
  --output-dir outputs/mlb_lineup_snapshot_smoke/standardized \
  --prediction-mode pre_lineup \
  --lineup-source mlb_stats_api_boxscore_snapshot \
  --captured-at 2026-05-26T04:06:02Z \
  --lineup-confidence 1.0

mlb-winprob build-features \
  --games outputs/mlb_lineup_snapshot_smoke/standardized/games.csv \
  --batting-logs outputs/mlb_lineup_snapshot_smoke/standardized/batting_logs.csv \
  --pitcher-logs outputs/mlb_lineup_snapshot_smoke/standardized/pitcher_logs.csv \
  --lineups outputs/mlb_lineup_snapshot_smoke/standardized/lineups.csv \
  --weather outputs/mlb_lineup_snapshot_smoke/standardized/weather.csv \
  --prediction-mode pre_lineup \
  --output outputs/mlb_lineup_snapshot_smoke/features_pre_lineup.csv
```

Early snapshot behavior is verified. When MLB has not posted official batting orders yet, standardized `lineups.csv` is empty but keeps schema headers, and `build-features --prediction-mode pre_lineup` produces game rows with null lineup features instead of falling back to confirmed lineups.

Latest live smoke:

```text
schedule rows: 15
snapshot JSON files: 15
standardized games: 15
standardized lineups: 0
pre_lineup feature rows: 15
non-null lineup player counts: 0
```

Completed-game official lineup smoke:

```text
source date: 2026-05-25
output: outputs/mlb_completed_lineup_smoke/
schedule rows: 13
official lineup rows: 234
games with lineups: 13
pre_lineup feature rows: 13
home/away lineup_player_count non-null: 13 / 13
prediction summary: outputs/mlb_completed_lineup_smoke/predictions.csv
winner direction smoke: 9 / 13
```

This confirms the MLB official lineup extraction path once batting orders are available. Because the games were already completed, this should be treated as a pipeline smoke test, not as true pre-game validation.

### BALLDONTLIE Projected Lineup

BALLDONTLIE MLB projected-lineup ingestion is available as a first automated-source path:

```text
mlb-winprob collect-balldontlie-lineups --dates 2026-05-26 --output data/raw/balldontlie/lineups_2026-05-26.json

mlb-winprob standardize-balldontlie-lineups \
  --input data/raw/balldontlie/lineups_2026-05-26.json \
  --output data/standardized/pre_lineup_2026-05-26/lineups.csv \
  --prediction-mode projected \
  --captured-at 2026-05-26T10:00:00Z \
  --game-id-map data/metadata/balldontlie_game_id_map.csv \
  --player-id-map data/metadata/balldontlie_player_id_map.csv
```

The standardizer preserves provider IDs as `external_game_id` and `external_player_id`, then optionally maps them into the MLBAM IDs used by the existing feature pipeline. Without those mapping files, the CSV is still useful as a raw normalized snapshot, but feature generation will only join cleanly after `game_id` and `player_id` match the project standard tables.

Provider-to-MLBAM map helpers are available:

```text
mlb-winprob build-external-lineup-id-maps \
  --provider-lineups data/standardized/pre_lineup_2026-05-26/lineups.csv \
  --mlb-games data/standardized/mlb_stats_api_2026/games.csv \
  --id-map data/processed/id_map.csv \
  --season 2026 \
  --game-map-output data/metadata/balldontlie_game_id_map.csv \
  --player-map-output data/metadata/balldontlie_player_id_map.csv
```

Player mapping uses unique normalized-name matches from `id_map.csv`, with an optional active-season filter. Game mapping uses `game_date`, `home_team`, and `away_team`. Ambiguous player/game matches are intentionally omitted and should be reviewed manually before feature generation.

Next operational requirement: validate the helpers against a real BALLDONTLIE response, review omitted ambiguous IDs, then run a real source-backed `build-features --prediction-mode pre_lineup` smoke test.

## Fixture-Backed Smoke Test

Before live API credentials are available, the local smoke script can exercise the full ingestion path with a provider-shaped fixture derived from an existing MLBAM standardized game:

```text
python scripts/run_pre_lineup_fixture_smoke.py
```

Default fixture:

- source game: `778563` (`2025-03-18`, CHC vs LAD)
- output: `outputs/pre_lineup_fixture_smoke/`
- path tested: provider JSON -> normalized provider lineups -> external ID maps -> mapped projected lineups -> `FeatureBuilder(prediction_mode="pre_lineup")`

Latest result:

```text
unmapped_lineup_rows: 18
mapped_game_rows: 1
mapped_player_rows: 14
mapped_lineup_rows: 18
feature_rows: 1
```

The partial player mapping is intentional signal: unmatched or ambiguous provider player IDs need review before treating a live source as production-ready.

## Manual Lineup Input

Manual projected lineups are supported for quick what-if checks before official lineups are posted.

Create a user-editable template:

```text
mlb-winprob write-manual-lineup-template \
  --games outputs/mlb_lineup_snapshot_smoke/standardized/games.csv \
  --game-ids 824434 \
  --output outputs/manual_lineup_smoke/manual_lineup_template.csv
```

Fill `player_id` directly when known. If `player_id` is blank, fill `player_name` and pass `--id-map data/processed/id_map.csv` during standardization.

Convert the edited CSV into standard `lineups.csv`:

```text
mlb-winprob standardize-manual-lineups \
  --input outputs/manual_lineup_smoke/manual_lineup_filled.csv \
  --output outputs/manual_lineup_smoke/lineups_manual.csv \
  --prediction-mode projected \
  --lineup-source manual \
  --captured-at 2026-05-26T04:30:00Z
```

Then build `pre_lineup` features with the manual lineup file:

```text
mlb-winprob build-features \
  --games outputs/mlb_lineup_snapshot_smoke/standardized/games.csv \
  --batting-logs data/standardized/mlb_stats_api_2025/batting_logs.csv \
  --pitcher-logs data/standardized/mlb_stats_api_2025/pitcher_logs.csv \
  --lineups outputs/manual_lineup_smoke/lineups_manual.csv \
  --weather outputs/mlb_lineup_snapshot_smoke/standardized/weather.csv \
  --prediction-mode pre_lineup \
  --output outputs/manual_lineup_smoke/features_manual_pre_lineup.csv
```

Latest smoke result:

```text
manual lineup rows: 18
manual feature rows: 15
game 824434 home_lineup_player_count: 9
game 824434 away_lineup_player_count: 9
```

Fit a final baseline model and predict the manually edited game:

```text
mlb-winprob fit-final-model \
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest \
  --output-dir outputs/final_models/full_random_forest_confirmed_2021_2025_statcast

mlb-winprob predict \
  --features outputs/manual_lineup_smoke/features_manual_pre_lineup.csv \
  --model outputs/final_models/full_random_forest_confirmed_2021_2025_statcast/best_model.joblib \
  --prediction-mode pre_lineup \
  --game-ids 824434
```

Latest prediction smoke:

```json
{"home_win_probability": 0.4772758014293535, "away_win_probability": 0.5227241985706466, "model_name": "random_forest", "prediction_mode": "pre_lineup"}
```

Over/under baseline:

```text
mlb-winprob fit-final-runs-model \
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest_regressor \
  --output-dir outputs/final_models/runs_random_forest_confirmed_2021_2025_statcast

mlb-winprob predict-runs \
  --features outputs/mlb_completed_lineup_smoke/features_pre_lineup.csv \
  --model outputs/final_models/runs_random_forest_confirmed_2021_2025_statcast/runs_model.joblib \
  --prediction-mode pre_lineup \
  --total-line 8.5 \
  --output outputs/mlb_completed_lineup_smoke/over_under_predictions_8_5.csv
```

Latest over/under smoke:

```text
fixed total line 8.5: 7 / 13 correct
line sensitivity:
6.5  9 / 13
7.5  8 / 13
8.5  7 / 13
9.5  9 / 13
10.5 10 / 13
```

Use `ou_margin` and `ou_confidence` rather than raw over/under picks. Small margins should be treated as pass.

## Market-Aware Over/Under Path

The expected-runs baseline can compare `pred_total` to a supplied line, but a true over/under model needs the market number as part of training. The pipeline now supports this with an optional `market_lines.csv`.

Create a market-line template:

```text
mlb-winprob write-market-lines-template \
  --games outputs/mlb_completed_lineup_smoke/standardized/games.csv \
  --output outputs/mlb_completed_lineup_smoke/market_lines_template.csv
```

Fill game-level market fields:

```text
game_id
opening_total_line
current_total_line
closing_total_line
over_odds
under_odds
opening_home_moneyline
opening_away_moneyline
current_home_moneyline
current_away_moneyline
home_sp_id_at_open
away_sp_id_at_open
home_sp_changed
away_sp_changed
starter_change_count
captured_at
market_source
```

Build features with the market rows:

```text
mlb-winprob build-features \
  --games .../games.csv \
  --batting-logs .../batting_logs.csv \
  --pitcher-logs .../pitcher_logs.csv \
  --lineups .../lineups.csv \
  --weather .../weather.csv \
  --market-lines .../market_lines.csv \
  --prediction-mode pre_lineup \
  --output .../features_pre_lineup_with_market.csv
```

Train the direct over/under classifier once historical market rows exist for 2021-2025:

```text
mlb-winprob fit-final-ou-model \
  --features data/processed/features_confirmed_2021_2025_with_market.csv \
  --prediction-mode confirmed_lineup \
  --model-name random_forest \
  --output-dir outputs/final_models/ou_random_forest_confirmed_2021_2025_market
```

Predict with:

```text
mlb-winprob predict-ou \
  --features outputs/today/features_pre_lineup_with_market.csv \
  --model outputs/final_models/ou_random_forest_confirmed_2021_2025_market/ou_model.joblib \
  --prediction-mode pre_lineup \
  --output outputs/today/ou_predictions.csv
```

Notes:

- `market_total_line` is the model-facing current line. If `current_total_line` is blank, it falls back to `opening_total_line`.
- `market_closing_total_line` is preserved for evaluation but excluded from normal feature selection to avoid future-line leakage.
- If only today's line is available, `predict-runs` can still do line comparison, but `fit-final-ou-model` needs historical line data to learn market-specific behavior.

## References

- MLB starting lineups: https://www.mlb.com/starting-lineups
- RotoWire daily MLB lineups: https://www.rotowire.com/baseball/daily-lineups.php
- Lineups.com MLB lineups: https://www.lineups.com/mlb/lineups/
- BALLDONTLIE MLB API: https://mlb.balldontlie.io/
