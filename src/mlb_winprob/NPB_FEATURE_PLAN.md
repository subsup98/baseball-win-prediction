# NPB Feature Plan

NPB should follow the same multi-league design as KBO. Near-term collection is limited to three public sources:

1. Official NPB pages for schedule/result/team/player/stat source-of-truth checks.
2. ProEyeKyuu downloadable tables as the primary practical public-data source.
3. BaseballData.jp analysis pages as a secondary sabermetric/split source.

Paid sports-data APIs are intentionally out of scope for the first NPB pipeline.

## Data Storage

Keep NPB files separate from MLB and KBO files.

- Raw official NPB pages/API responses: `data/raw/npb_official/`
- Raw secondary NPB sources: `data/raw/npb_secondary/`
- Standardized tables: `data/standardized/npb/<season>/`
- Processed features: `data/processed/npb/`
- Quality reports: `outputs/quality/npb/`
- Experiments: `outputs/experiments/npb/`

## Initial Feature Direction

Reuse the KBO first-model approach unless a better NPB source is found.

- Public-data sabermetrics from official or stable public records.
- League-common rolling features: starter, lineup, team, bullpen, weather, and park factor.
- MLB-to-NPB proxy fields for missing Statcast-quality measurements.
- League-specific adjustments for NPB roster rules, ball/park context, and interleague structure.
- Feature gaps and proxy definitions are tracked in `NPB_FEATURE_GAP.md`.

## Expected Gaps

- Public Statcast-equivalent pitch tracking is not assumed.
- Player ID crosswalks need source-specific design.
- Confirmed pregame lineups may need a separate source.
- Batter vs pitcher-hand splits may not be consistently available from official pages.

## First Milestone

1. Collect and parse raw pages from official NPB, ProEyeKyuu, and BaseballData.jp only.
2. Standardize ProEyeKyuu season tables into named NPB secondary-source tables.
3. Add schedule/game-page standardization once the most stable public game-result source is confirmed.
4. Collect one NPB season into canonical tables.
5. Build league-common and proxy features.
6. Compare null rates and model lift against KBO and MLB baselines.

## Collection Status

- 2026-05-27: Added source-limited NPB page collection CLI:
  - `collect-npb-source-pages --source npb_official`
  - `collect-npb-source-pages --source proeyekyuu`
  - `collect-npb-source-pages --source baseballdatajp`
- 2026-05-27: Added ProEyeKyuu parsed-table standardization CLI:
  - `standardize-proeyekyuu-tables`
- 2026-05-27: Verified ProEyeKyuu pages are wpDataTables-style dynamic tables. The parser now saves dynamic table metadata and can fall back to parsing embedded static rows when present.
- 2026-05-27: Added ProEyeKyuu game-result standardization to canonical `games.csv`:
  - `standardize-proeyekyuu-game-results`
- 2026-05-27: Added ProEyeKyuu game-page collection and canonical-ish game-table standardization:
  - `collect-proeyekyuu-game-pages`
  - `standardize-proeyekyuu-game-tables`
- 2026-05-27: Added confirmed starter backfill from ProEyeKyuu `pitcher_logs.csv` into the NPB game backbone:
  - `enrich-proeyekyuu-games-starters`
- 2026-05-27: Added ProEyeKyuu canonical coverage reporting:
  - `report-proeyekyuu-coverage`
- 2026-05-27: Smoke verified one ProEyeKyuu 2026 game into `games.csv`, `lineups.csv`, `batting_logs.csv`, `pitcher_logs.csv`, enriched `games_with_starters_sample.csv`, then through the shared `build-features` command.
- 2026-05-27: Wrote smoke coverage report at `outputs/npb_smoke/npb_proeyekyuu_coverage_report.md`. Current smoke coverage is one collected game page out of 50 standardized game results.
- 2026-05-27: Added shared public-data proxy features for non-Statcast leagues:
  - `lineup_xwoba_proxy`
  - `lineup_hard_contact_proxy`
  - `sp_whiff_proxy`
  - `sp_run_prevention_proxy`
  - `sp_command_proxy`
- 2026-05-27: Expanded ProEyeKyuu smoke collection to 10 game pages. Current 50-game result sample has 10 canonical game pages covered:
  - `batting_logs.csv`: 267 rows
  - `lineups.csv`: 180 rows
  - `pitcher_logs.csv`: 81 rows
  - coverage report: `outputs/npb_smoke/npb_proeyekyuu_coverage_report.md`
- 2026-05-27: Added NPB venue metadata/backfill flow:
  - seed file: `data/standardized/npb/venues_seed.csv`
  - `write-npb-venue-template`
  - `enrich-npb-games-venues`
- 2026-05-27: Added ProEyeKyuu batting detail audit:
  - `audit-proeyekyuu-batting-detail`
  - current parsed game batting tables expose AB/R/H/RBI/SB/order/position, but not 2B/3B/HR/BB/HBP/SF.
- 2026-05-27: Added NPB public/proxy feature-set export:
  - `write-npb-feature-set`
  - 10-game smoke output includes 102 NPB-usable numeric features and excludes MLB-only tracking columns.
- 2026-05-27: Added reproducible full-run script:
  - `scripts/run_npb_proeyekyuu_pipeline.py`
  - local smoke verification wrote `outputs/npb_smoke/processed/features_confirmed_npb_10.csv` and feature quality output under `outputs/npb_smoke/quality/features_confirmed_10/`.
- 2026-05-27: Expanded the ProEyeKyuu smoke run to all 50 standardized game results:
  - `canonical_sample_50/batting_logs.csv`: 1337 rows
  - `canonical_sample_50/lineups.csv`: 900 rows
  - `canonical_sample_50/pitcher_logs.csv`: 396 rows
  - `npb_proeyekyuu_coverage_report_50.md`: 100% game/log/lineup/starter coverage for the 50-game sample
  - `processed/features_confirmed_npb_sample_50.csv`: 50 rows, 210 columns
  - `processed/npb_feature_set_sample_50.csv`: 128 included public/proxy numeric features
  - `quality/features_confirmed_npb_sample_50/summary.md`: shared feature quality report
- 2026-05-27: Added KBO-style NPB model-ready feature export:
  - `write-npb-model-ready-features`
  - `processed/features_confirmed_npb_model_ready_sample_50.csv`: 50 rows, 140 columns
  - The model-ready file keeps identifiers/target plus public/proxy included features, and drops unavailable MLB-only tracking columns.
- 2026-05-27: Added and ran NPB smoke model prediction workflow:
  - `scripts/run_npb_smoke_model_predictions.py`
  - 40 chronological train rows, 10 test rows, 128 features
  - `model_smoke_random_forest_shallow/summary.md`: accuracy 0.50, Brier 0.253, log loss 0.698
  - `model_smoke_logistic/summary.md`: accuracy 0.40, Brier 0.469, log loss 2.410
  - `model_smoke_random_forest_deep/summary.md`: accuracy 0.30, Brier 0.302, log loss 0.798
  - `model_final_random_forest_shallow/best_model.joblib`: final smoke model fit on all 50 rows
