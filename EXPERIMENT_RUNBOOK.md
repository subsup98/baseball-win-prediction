# Experiment Runbook

This runbook keeps the model-improvement loop reproducible.

## 1. Refresh Feature Table

Reuse existing raw Statcast files unless source data must be recollected.

```powershell
.\.venv\Scripts\python.exe scripts\build_statcast_feature_pipeline.py `
  --seasons 2021,2022,2023,2024,2025 `
  --prediction-mode confirmed_lineup `
  --models elo,logistic,random_forest `
  --holdout-seasons 2022,2023,2024,2025
```

Outputs:

- `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv`
- `outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast/`
- `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast/`

## 2. Baseline Model Test

```powershell
.\.venv\Scripts\python.exe scripts\run_model_test_experiment.py `
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --output-dir outputs/experiments/model_baseline_confirmed_2021_2025_with_park_factors_statcast `
  --holdout-seasons 2022,2023,2024,2025 `
  --models elo,logistic,random_forest `
  --prediction-mode confirmed_lineup
```

Decision metric priority:

1. Mean log loss
2. Mean brier score
3. Mean accuracy
4. `accuracy_conf_60` with coverage

## 3. Multi-Seed Stability

Use this before promoting any candidate to baseline.

```powershell
.\.venv\Scripts\python.exe scripts\run_multiseed_model_experiment.py `
  --variants full=data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --models random_forest,random_forest_shallow `
  --baseline-variant full `
  --baseline-model random_forest `
  --output-dir outputs/experiments/model_multiseed_candidate_name
```

Promotion rule:

- Candidate should improve mean log loss.
- Candidate should have a clear win rate, not just a tiny average gain.
- Confidence-only candidates must not replace the default probability model unless a model-switch rule is validated.

## 4. Pre-Lineup Path

Current status:

- Confirmed-lineup features are available.
- True `pre_lineup` historical rows are not yet available.
- Confirmed-lineup metrics are not deployable pre-game metrics.

Smoke build after creating projected lineups:

```powershell
.\.venv\Scripts\python.exe -m mlb_winprob.cli build-features `
  --games data/standardized/mlb_stats_api_2024-04-01/games.csv `
  --batting-logs data/standardized/mlb_stats_api_2024-04-01/batting_logs.csv `
  --pitcher-logs data/standardized/mlb_stats_api_2024-04-01/pitcher_logs.csv `
  --lineups data/smoke_pre_lineup/lineups_projected_2024-04-01.csv `
  --weather data/standardized/mlb_stats_api_2024-04-01/weather.csv `
  --park-factors data/processed/park_factors_empirical_previous_season_2022_2026.csv `
  --venues data/raw/mlb_stats_api/venues_2021_2025.csv `
  --prediction-mode pre_lineup `
  --output data/smoke_pre_lineup/features_pre_lineup_2024-04-01.csv
```

## 5. Expected-Runs OOF Feature Check

```powershell
.\.venv\Scripts\python.exe scripts\run_expected_runs_feature_experiment.py `
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --output-dir outputs/experiments/expected_runs_oof_feature_confirmed_2021_2025 `
  --holdout-seasons 2022,2023,2024,2025 `
  --models random_forest `
  --expected-runs-model ridge `
  --prediction-mode confirmed_lineup
```

Current decision:

- Ridge and RF-regressor OOF expected-runs features did not improve the RF win-probability baseline on average.
- Keep expected-runs as an adjacent report for now.

## 6. Booster Tests

Install optional dependencies when needed:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[boosters]"
```

Current targeted CatBoost comparison:

```powershell
.\.venv\Scripts\python.exe scripts\run_model_test_experiment.py `
  --features data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv `
  --output-dir outputs/experiments/model_test_catboost_tuning_confirmed_2021_2025_with_park_factors_statcast `
  --holdout-seasons 2022,2023,2024,2025 `
  --models random_forest,catboost,catboost_shallow,catboost_l2,catboost_lr02 `
  --prediction-mode confirmed_lineup
```

Current decision:

- `catboost_shallow` improved over default CatBoost but still trails RF on mean log loss.
- CatBoost can remain a season-dependent challenger, not the default baseline.

## 7. Feature Stability

```powershell
.\.venv\Scripts\python.exe scripts\summarize_feature_stability.py `
  --experiment-dir outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast `
  --output-dir outputs/experiments/feature_stability_confirmed_2021_2025 `
  --top-n 20
```

Use feature stability to guide grouped ablations, not one-off feature deletion.

## 8. Decision Log

After every experiment, update:

- `MODEL_IMPROVEMENT_LOG.md`
- `WORKLOG.md`
- `PROJECT_CHECKLIST.md`

Each entry should include:

- Baseline
- Candidate/change
- Reason
- Key metrics
- Decision
- Follow-up

## 9. Tests

Use workspace-local basetemp on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest --basetemp .pytest_tmp
```

