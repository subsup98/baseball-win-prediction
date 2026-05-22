# Research Extensions

## Model Ensemble Selection Rule

`season-holdout-report` now writes `model_selection_rules.csv`.

Rules are intentionally simple and auditable:

- `overall_log_loss`: choose the model with the best holdout log loss.
- `confidence_55`, `confidence_60`, `confidence_65`: choose the model with the best accuracy inside that confidence band, only when coverage is at least 10%.

This keeps the production rule separate from the raw model leaderboard. The next comparison should evaluate:

- fixed overall winner
- confidence-band winner
- stacking/blending
- per-season instability of selected models

## Expected Runs Model

`expected-runs-report` trains separate home-score and away-score regressors on the same leakage-safe feature matrix.

Current baseline regressors:

- `ridge`
- `random_forest_regressor`

Outputs:

- `expected_runs_metrics_by_holdout.csv`
- `expected_runs_best_by_holdout.csv`
- `summary.md`

Primary metrics:

- `home_mae`
- `away_mae`
- `total_mae`
- `total_rmse`
- `run_diff_mae`

The win-probability target remains the primary model target. Expected runs should be treated as an adjacent task until it proves incremental value.

## Player Embedding Experiment Design

Goal: test whether player identity and lineup sequence add signal beyond tabular rolling stats.

Recommended first experiment:

- Inputs:
  - home lineup player IDs in batting order
  - away lineup player IDs in batting order
  - home and away starting pitcher IDs
  - existing tabular feature vector
- Embeddings:
  - batter ID embedding shared across lineup slots
  - pitcher ID embedding
  - optional team ID embedding
- Architecture:
  - encode each lineup as ordered player embeddings plus batting-order position embeddings
  - average or attention-pool each lineup
  - concatenate home lineup, away lineup, starter embeddings, and tabular features
  - train binary classifier for `home_team_win`
- Leakage control:
  - fit embedding vocabulary on training seasons only
  - unknown players in holdout season map to an `UNK` token
  - no target-season future stats are used to initialize embeddings
- Evaluation:
  - season holdout, same folds as tabular models
  - compare log loss and calibration to random forest and logistic baselines
  - report cold-start player share by holdout season

Start with a small PyTorch or scikit-compatible adapter only after the tabular expected-runs and selection-rule reports are stable.
