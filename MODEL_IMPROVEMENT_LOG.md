# Model Improvement Log

모델 후보, 개선 실험, 평가 점수, 채택/보류 이유를 한곳에 누적 기록한다.

## Current Decision

- Main baseline: `full + random_forest`
- Confidence-band challenger: `full + random_forest_shallow`
- Calibration challenger: `calibrated_logistic`
- Next validation: confidence-band selection rule comparison
- 보류 후보: `without_lineup_optional + random_forest`

현재 production 후보는 평균 log loss 기준으로 `full + random_forest`가 가장 안정적이다. `random_forest_shallow`는 평균 log loss는 밀리지만 `accuracy_conf_60`이 높아 고확신 구간 선택 모델로 남긴다. `without_lineup_optional + random_forest`는 단일 실험에서는 좋아 보였지만 multi-seed 안정성 검증에서 기준선을 넘지 못했다.

## Metric Read Guide

- `log_loss`: 낮을수록 좋음. 확률 예측의 주 평가 지표.
- `brier_score`: 낮을수록 좋음. 확률 보정과 예측 오차를 함께 확인.
- `accuracy`: 높을수록 좋음. 승패 방향 적중률.
- `accuracy_conf_60`: 예측 확률이 60% 이상인 고확신 경기에서의 accuracy.
- `coverage_conf_60`: 60% 이상 고확신 경기가 전체에서 차지하는 비율. 너무 낮으면 선택적으로만 쓸 수 있음.
- `win_rate_vs_baseline`: seed/holdout 조합에서 baseline을 이긴 비율.

## Model Candidate List

| candidate | role | status | reason |
| --- | --- | --- | --- |
| `full + random_forest` | main baseline | active | multi-seed 기준 평균 log loss가 가장 좋고 안정적임 |
| `full + random_forest_shallow` | confidence challenger | active challenger | 평균 log loss는 나쁘지만 `accuracy_conf_60`이 가장 강함 |
| `without_lineup_optional + random_forest` | feature-pruned challenger | hold | 단일 실험은 좋았지만 multi-seed에서 log loss가 기준선보다 나쁨 |
| `without_lineup_optional + random_forest_shallow` | pruned confidence challenger | hold | 고확신 성능은 괜찮지만 기준선 대비 log loss 개선 없음 |
| `without_bullpen_role + random_forest` | feature-pruned challenger | watch | multi-seed에서 평균 log loss/accuracy는 소폭 개선됐지만 win rate가 55%로 아직 약함 |
| `calibrated_logistic` | calibration challenger | watch | plain logistic보다 log loss는 개선되지만 RF 계열보다 약함 |
| `calibrated_random_forest` | RF calibration test | rejected for now | 평균 log loss와 accuracy가 plain RF보다 약함 |
| `extra_trees` | tree ensemble challenger | rejected for now | 전체 log loss 경쟁력이 낮고 coverage가 낮음 |
| `hist_gradient_boosting` | sklearn boosting challenger | rejected | 현재 sklearn-only 설정에서는 유용하지 않음 |
| `catboost` | booster challenger | rejected for now | booster 중 가장 낫지만 RF보다 log loss/accuracy가 낮음 |
| `xgboost` | booster challenger | rejected | 현재 기본 설정에서는 RF보다 크게 낮음 |
| `lightgbm` | booster challenger | rejected | 현재 기본 설정에서는 log loss가 크게 악화됨 |
| `logistic`, `logistic_l1`, `logistic_l2_*` | linear baselines | baseline/reference | 해석성과 기준 비교용. 성능은 RF보다 낮음 |
| `elo` | simple baseline | reference | feature 없는 순수 기준선으로 유지 |

## Experiment History

### 2026-05-21 - Feature Set Refresh Comparison

- Output: `outputs/experiments/feature_set_update_compare_20260521_095456/summary.md`
- Baseline: previous `season_holdout_confirmed_2021_2025_with_park_factors_statcast`
- Latest: refreshed `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv`
- Change: feature columns `121 -> 173` (`+52`)
- Reason: Statcast, lineup continuity, travel/rest proxy, high-leverage bullpen role proxy 등 신규 feature 확장이 실제 성능에 도움이 되는지 확인.

| model | log_loss_delta | brier_score_delta | accuracy_delta | read |
| --- | ---: | ---: | ---: | --- |
| `random_forest` | -0.000246 | -0.000130 | +0.002572 | small positive |
| `logistic` | +0.000310 | +0.000101 | +0.004321 | accuracy는 증가, 확률 품질은 소폭 악화 |
| `elo` | 0.000000 | 0.000000 | 0.000000 | feature 비사용 기준선 |

Decision: `random_forest` 기준으로는 작은 개선이지만 시즌별로 균일하지 않다. decisive breakthrough가 아니라 incremental gain으로 기록.

### 2026-05-21 - Broad Model Test

- Output: `outputs/experiments/model_test_confirmed_2021_2025_with_park_factors_statcast/summary.md`
- Models: `logistic`, logistic variants, RF variants, `extra_trees`, `hist_gradient_boosting`, `calibrated_logistic`
- Reason: 기존 RF 기준선을 다른 모델군이 대체할 수 있는지 확인.

| model | mean_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `random_forest` | 0.679559 | 0.243292 | 0.567343 | 0.650573 | 0.186231 | best overall log loss |
| `random_forest_shallow` | 0.680300 | 0.243648 | 0.565285 | 0.672257 | 0.130978 | high-confidence challenger |
| `random_forest_deep` | 0.680681 | 0.243834 | 0.565902 | 0.647200 | 0.189627 | no replacement case |
| `extra_trees` | 0.681978 | 0.244467 | 0.559008 | 0.678075 | 0.070890 | high confidence only, very low coverage |
| `calibrated_logistic` | 0.683131 | 0.244886 | 0.561066 | 0.615442 | 0.175737 | better than logistic, still trails RF |
| `hist_gradient_boosting` | 0.692632 | 0.249101 | 0.551806 | 0.599648 | 0.412999 | not useful in current setup |

Decision: main baseline remains `random_forest`. Keep `random_forest_shallow` for confidence-band experiments and `calibrated_logistic` as calibration challenger.

### 2026-05-21 - Feature Group Ablation

- Output: `outputs/experiments/feature_group_ablation_confirmed_2021_2025_with_park_factors_statcast/summary.md`
- Model: `random_forest`
- Reason: newly added research feature groups 중 어떤 그룹이 실제로 도움이 되는지 확인.

Positive `mean_log_loss_delta_vs_full` means removing the group made log loss worse, so the group helped the full model.

| variant | mean_log_loss | delta_vs_full | mean_accuracy | accuracy_delta_vs_full | read |
| --- | ---: | ---: | ---: | ---: | --- |
| `without_lineup_optional` | 0.679386 | -0.000174 | 0.569092 | +0.001749 | 단일 실험상 full보다 좋아 보임 |
| `without_bullpen_role` | 0.679424 | -0.000135 | 0.565079 | -0.002264 | log loss는 소폭 개선, accuracy는 악화 |
| `full` | 0.679559 | 0.000000 | 0.567343 | 0.000000 | 기준 |
| `without_all_research_groups` | 0.679770 | +0.000210 | 0.564873 | -0.002470 | research group 전체는 도움 |
| `baseline_like_columns` | 0.679803 | +0.000244 | 0.564976 | -0.002367 | feature expansion은 전체적으로 도움 |
| `without_travel` | 0.679937 | +0.000377 | 0.563433 | -0.003910 | travel/rest proxy는 도움 |
| `without_pitch_stuff` | 0.679942 | +0.000382 | 0.563844 | -0.003499 | pitch stuff는 도움 |

Decision: 단일 ablation만 보면 `without_lineup_optional` pruning 후보가 생겼다. 다만 이 결과는 seed 안정성 검증 전까지 baseline 교체 근거로 보지 않는다.

### 2026-05-21 - RF Family And Feature Variant Comparison

- Output: `outputs/experiments/model_test_rf_family_comparison_confirmed_2021_2025/summary.md`
- Feature variants: `full`, `without_lineup_optional`, `without_lineup_optional_bullpen_role`
- Models: `random_forest`, `random_forest_shallow`, `calibrated_random_forest`
- Reason: RF 계열 안에서 feature pruning, shallow model, calibration 조합을 비교.

| feature_variant | model | mean_log_loss | mean_accuracy | accuracy_conf_60 | coverage_conf_60 | read |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| `without_lineup_optional` | `random_forest` | 0.679386 | 0.569092 | 0.647983 | 0.191376 | single-run top by log loss |
| `full` | `random_forest` | 0.679559 | 0.567343 | 0.650573 | 0.186231 | stable baseline candidate |
| `without_lineup_optional_bullpen_role` | `random_forest` | 0.679819 | 0.561890 | 0.655906 | 0.187980 | accuracy drop |
| `full` | `calibrated_random_forest` | 0.679895 | 0.563947 | 0.638381 | 0.186131 | calibration did not help enough |
| `full` | `random_forest_shallow` | 0.680300 | 0.565285 | 0.672257 | 0.130978 | confidence-only challenger |

Decision: `without_lineup_optional + random_forest` looked like a possible replacement, but required multi-seed stability validation.

### 2026-05-21 - Multi-Seed RF Pruning Stability

- Output: `outputs/experiments/model_multiseed_rf_pruning_confirmed_2021_2025/summary.md`
- Baseline: `full + random_forest`
- Seeds: 10 random seeds
- Reason: single-seed pruning result가 우연인지, 실제로 안정적인 개선인지 검증.

| variant | model | mean_log_loss | std_log_loss | mean_accuracy | mean_accuracy_conf_60 | log_loss_win_rate_vs_baseline | read |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `full` | `random_forest` | 0.679496 | 0.001806 | 0.565069 | 0.657115 | 0.000 | stable baseline |
| `without_lineup_optional` | `random_forest` | 0.679896 | 0.001839 | 0.565100 | 0.652715 | 0.350 | not stable enough |
| `full` | `random_forest_shallow` | 0.680243 | 0.001537 | 0.567127 | 0.678148 | 0.125 | confidence challenger |
| `without_lineup_optional` | `random_forest_shallow` | 0.680310 | 0.001571 | 0.566623 | 0.673279 | 0.150 | no replacement case |

Decision: `full + random_forest` remains the main baseline. `without_lineup_optional + random_forest` is held, not promoted. `full + random_forest_shallow` remains useful only as a confidence-band challenger.

### 2026-05-22 - Multi-Seed Bullpen Role Stability

- Output: `outputs/experiments/model_multiseed_rf_bullpen_role_confirmed_2021_2025/summary.md`
- Baseline: `full + random_forest`
- Candidate: `without_bullpen_role + random_forest`
- Seeds: 10 random seeds
- Reason: 단일 ablation에서 `bullpen_role` 제거가 log loss를 소폭 개선했지만 accuracy는 흔들렸기 때문에 반복 seed 기준으로 노이즈 여부를 확인.
- Change from previous: `home_estimated_high_leverage_role_fatigue_score`, `away_estimated_high_leverage_role_fatigue_score`만 제거한 feature table 추가.

| variant | model | mean_log_loss | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | log_loss_win_rate_vs_baseline | read |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `without_bullpen_role` | `random_forest` | 0.679389 | 0.565974 | 0.653579 | 0.185984 | 0.550 | small positive, not decisive |
| `full` | `random_forest` | 0.679496 | 0.565069 | 0.657115 | 0.185079 | 0.000 | current baseline |
| `full` | `random_forest_shallow` | 0.680243 | 0.567127 | 0.678148 | 0.127459 | 0.125 | confidence challenger |
| `without_bullpen_role` | `random_forest_shallow` | 0.680302 | 0.566736 | 0.674287 | 0.127367 | 0.200 | no replacement case |

Decision: keep `full + random_forest` as the main baseline for now. Promote `without_bullpen_role + random_forest` to watchlist/challenger because it improves mean log loss by `0.000107` and mean accuracy by `0.000906`, but the 55% log-loss win rate is too thin for a baseline swap.

### 2026-05-22 - Confidence-Band Selection Rule Check

- Output: `outputs/experiments/confidence_band_selection_rules_confirmed_2021_2025/summary.md`
- Source: `outputs/experiments/model_multiseed_rf_pruning_confirmed_2021_2025/metrics_by_seed_holdout.csv`
- Baseline: `full + random_forest`
- Candidate: `full + random_forest_shallow`
- Reason: `random_forest_shallow` repeatedly shows stronger high-confidence accuracy, so compare the gain against coverage loss and overall log-loss cost.

| rule | log_loss_delta_vs_rf | accuracy_delta_vs_rf | accuracy_conf_60_delta_vs_rf | coverage_conf_60_delta_vs_rf | read |
| --- | ---: | ---: | ---: | ---: | --- |
| `always_random_forest` | 0.000000 | 0.000000 | 0.000000 | 0.000000 | main baseline |
| `always_random_forest_shallow` | 0.000746 | 0.002058 | 0.021033 | -0.057620 | confidence challenger |

Decision: keep `full + random_forest` as the default probability model. `full + random_forest_shallow` can be used for selective confidence-band analysis because it improves mean `accuracy_conf_60`, but it loses coverage and worsens overall log loss. Do not switch the default model until prediction-level blending or a deployable model-switch rule is evaluated.

### 2026-05-22 - Pre-Lineup Readiness Check

- Output: `outputs/experiments/pre_lineup_readiness_confirmed_2021_2025/summary.md`
- Feature table: `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv`
- Reason: 실제 경기 전 예측 품질을 확인하려면 `pre_lineup` feature와 holdout metric이 필요함.

Readout:

- Current feature rows are all `confirmed_lineup`.
- Season-level standardized `lineups.csv` files for 2021-2025 are also all `confirmed_lineup`.
- No `pre_lineup`, `projected`, or `expected` lineup rows are currently available.

Decision: pre-lineup performance evaluation is blocked on upstream projected-lineup data. Do not treat current confirmed-lineup metrics as deployable pre-game performance.

### 2026-05-22 - Expected Runs Full Holdout Check

- Output: `outputs/experiments/expected_runs_confirmed_2021_2025_full_check/summary.md`
- Feature table: `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv`
- Models: `ridge`, `random_forest_regressor`
- Reason: 기존 expected-runs check가 2024-2025 중심이라 2022-2025 전체 holdout으로 보조 target 품질을 다시 확인.

| holdout | best_model | total_mae | total_rmse | run_diff_mae | read |
| --- | --- | ---: | ---: | ---: | --- |
| 2022 | `random_forest_regressor` | 3.507164 | 4.411268 | 3.373167 | RF regressor best |
| 2023 | `ridge` | 3.570532 | 4.546192 | 3.472396 | ridge best by total MAE |
| 2024 | `random_forest_regressor` | 3.328263 | 4.198817 | 3.412222 | RF regressor best |
| 2025 | `ridge` | 3.533861 | 4.490473 | 3.529009 | ridge best by total MAE |

Decision: expected-runs is viable as an adjacent report, but the best regressor changes by season. Do not add it to the win-probability baseline until an out-of-fold/holdout-safe prediction feature is generated and tested against `full + random_forest`.

### 2026-05-22 - Booster Model Comparison

- Output: `outputs/experiments/model_test_boosters_confirmed_2021_2025_with_park_factors_statcast/summary.md`
- Models: `random_forest`, `lightgbm`, `xgboost`, `catboost`
- Reason: optional booster dependencies were installed so the current RF baseline could be tested against LightGBM/XGBoost/CatBoost under the same season-holdout setup.

| model | mean_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `random_forest` | 0.679559 | 0.243292 | 0.567343 | 0.650573 | 0.186231 | best overall |
| `catboost` | 0.683661 | 0.245132 | 0.563123 | 0.609966 | 0.372049 | closest booster, still behind RF |
| `xgboost` | 0.693865 | 0.249331 | 0.562507 | 0.596301 | 0.482863 | not competitive |
| `lightgbm` | 0.720479 | 0.258854 | 0.552834 | 0.577527 | 0.576493 | not competitive with current defaults |

Decision: no booster replaces `full + random_forest`. CatBoost is the only booster worth revisiting later, but only after targeted hyperparameter tuning or calibration.

### 2026-05-22 - Pre-Lineup Schema Guard And Smoke Build

- Output: `data/smoke_pre_lineup/features_pre_lineup_2024-04-01.csv`
- Source plan: `PRE_LINEUP_SOURCE_PLAN.md`
- Reason: `pre_lineup` evaluation must not silently fall back to confirmed lineups when projected rows are missing.
- Change from previous: `FeatureBuilder(prediction_mode="pre_lineup")` now filters strictly to `pre_lineup`, `projected`, or `expected` rows and returns null lineup features when none exist.

Smoke result:

| file | rows | read |
| --- | ---: | --- |
| `data/smoke_pre_lineup/lineups_projected_2024-04-01.csv` | 252 | projected-lineup schema smoke input |
| `data/smoke_pre_lineup/features_pre_lineup_2024-04-01.csv` | 14 | pre-lineup feature build succeeded |

Decision: schema path is ready for a real projected-lineup source. True historical `pre_lineup` evaluation remains blocked until source snapshots are collected.

### 2026-05-22 - Expected-Runs OOF Feature Experiment

- Outputs:
  - `outputs/experiments/expected_runs_oof_feature_confirmed_2021_2025/summary.md`
  - `outputs/experiments/expected_runs_oof_feature_rf_regressor_confirmed_2021_2025/summary.md`
- Baseline: `full + random_forest`
- Candidates: OOF `expected_home_runs`, `expected_away_runs`, `expected_total_runs`, `expected_run_diff`
- Reason: test whether leakage-safe expected-runs predictions improve win-probability features.

| expected_runs_model | mean_log_loss_delta | mean_brier_delta | mean_accuracy_delta | mean_accuracy_conf_60_delta | read |
| --- | ---: | ---: | ---: | ---: | --- |
| `ridge` | +0.000174 | +0.000088 | -0.003807 | +0.003608 | hurts overall probability quality |
| `random_forest_regressor` | +0.000074 | +0.000040 | -0.003807 | -0.003980 | closer, still not useful |

Decision: do not add expected-runs predictions to the current win-probability baseline. Keep expected-runs as an adjacent report.

### 2026-05-22 - Bullpen Role Proxy Cap

- Output: `outputs/experiments/model_multiseed_rf_bullpen_role_capped_confirmed_2021_2025/summary.md`
- Change: cap `estimated_high_leverage_role_score` contribution to `0..1` when converting to fatigue IP.
- Reason: prevent high-leverage role proxy from exceeding actual innings contribution.

Result: multi-seed metrics were unchanged at decision precision versus the previous bullpen-role stability check.

Decision: keep the cap as a safety guard, but it does not change baseline selection. `without_bullpen_role + random_forest` remains watchlist only.

### 2026-05-22 - CatBoost Targeted Tuning

- Output: `outputs/experiments/model_test_catboost_tuning_confirmed_2021_2025_with_park_factors_statcast/summary.md`
- Models: `random_forest`, `catboost`, `catboost_shallow`, `catboost_l2`, `catboost_lr02`
- Reason: default CatBoost lagged RF, so test smaller/deeper regularized candidates.

| model | mean_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `random_forest` | 0.679559 | 0.243292 | 0.567343 | 0.650573 | 0.186231 | best mean log loss |
| `catboost_shallow` | 0.680094 | 0.243537 | 0.563020 | 0.631409 | 0.284594 | closest CatBoost |
| `catboost_lr02` | 0.680760 | 0.243817 | 0.564770 | 0.625545 | 0.317005 | season-dependent wins |
| `catboost_l2` | 0.681566 | 0.244183 | 0.563329 | 0.618764 | 0.330484 | behind |
| `catboost` | 0.683661 | 0.245132 | 0.563123 | 0.609966 | 0.372049 | default behind |

Decision: CatBoost does not replace RF. Keep `catboost_shallow` / `catboost_lr02` as season-dependent challengers only.

### 2026-05-22 - Feature Stability Summary

- Output: `outputs/experiments/feature_stability_confirmed_2021_2025/summary.md`
- Reason: compare season-to-season stability across feature importance and SHAP top features.

Stable features appearing in both views include:

- `team_woba_diff`
- team runs scored/allowed to date
- bullpen FIP/WHIP to date
- away starter K-BB / hard-hit allowed features
- `away_lineup_bottom4_ops`

Decision: use stability results to guide grouped ablations. Do not delete one-off low-stability features solely from importance ranking.

### 2026-05-22 - Experiment Runbook

- Added: `EXPERIMENT_RUNBOOK.md`
- Reason: make data refresh, holdout, multi-seed, pre-lineup smoke, expected-runs, booster, feature-stability, and decision-log steps reproducible.

### 2026-05-27 - Recent-Season Training Challenger

- Output: `outputs/experiments/recent_season_challenger_2026/`
- Baseline: `random_forest` trained on all of 2021-2025 (current production default).
- Candidate: `random_forest` trained on 2024-2025 only, and a recency-weighted `random_forest` (exponential season weight, half-life 2 seasons) trained on 2021-2025.
- Reason: check whether league/roster drift makes recent-only or recency-weighted training track the 2026 season better than equal-weighted all-season training. Enabled now that a leakage-safe 2026 season-to-date feature table exists.
- Change from previous: first recency-weighting / recent-only training comparison; added `model__sample_weight` support path in `scripts/run_recent_season_challenger.py`.

| model_or_variant | eval_set | log_loss | brier_score | accuracy | acc_conf_60 | coverage_conf_60 | read |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline_rf_all_seasons | target_2026_scored | 0.6944 | 0.2506 | 0.5167 | 0.5586 | 0.1375 | reference |
| challenger_rf_2024_2025 | target_2026_scored | 0.6939 | 0.2503 | 0.5390 | 0.5155 | 0.1202 | best 2026 accuracy |
| recency_weighted_rf_hl2 | target_2026_scored | 0.6933 | 0.2501 | 0.5180 | 0.5895 | 0.1177 | best 2026 log_loss/conf |
| baseline_rf_all_seasons | holdout_2025 | 0.6797 | 0.2434 | 0.5584 | 0.6524 | 0.1823 | best on robust holdout |
| challenger_rf_2024 | holdout_2025 | 0.6829 | 0.2449 | 0.5527 | 0.6491 | 0.1407 | worse than baseline |
| recency_weighted_rf_hl2 | holdout_2025 | 0.6813 | 0.2442 | 0.5539 | 0.6547 | 0.1609 | worse than baseline |

Decision: Keep `baseline + random_forest` (all 2021-2025, equal weight) as the production default. Recent-only and recency-weighted variants show a small edge on the partial 2026 sample but lose to baseline on the robust 2025 holdout, and all 2026 log_loss values sit near 0.693 (weak edge on the current sample). Not a robust improvement.

Follow-up: Re-run once 2026 has a larger scored sample (e.g. post All-Star break) before reconsidering; recency weighting at a longer half-life is a future watchlist item, not a promotion candidate.

### 2026-05-27 - CatBoost Season-Dependent Selection Rule

- Output: `outputs/experiments/catboost_season_rule_multiseed_2021_2025/` (`per_season_winrate_vs_rf.csv`, `summary_by_variant_model.csv`)
- Baseline: `full + random_forest`.
- Candidate: `catboost`, `catboost_lr02` as a season-dependent switch (earlier single-seed runs showed CatBoost best in 2022/2024/2025).
- Reason: verify with 5 seeds × 4 holdouts whether per-season CatBoost wins are stable signal or seed luck, before allowing a season-switch rule.
- Change from previous: first multi-seed per-season CatBoost-vs-RF stability check.

| model_or_variant | mean_log_loss | std_log_loss | mean_accuracy | mean_acc_conf_60 | mean_cov_conf_60 | read |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| random_forest | 0.6795 | 0.0017 | 0.5651 | 0.6599 | 0.1851 | best overall log_loss |
| catboost_lr02 | 0.6807 | 0.0023 | 0.5668 | 0.6246 | 0.3191 | marginal accuracy, worse log_loss |
| catboost | 0.6839 | 0.0041 | 0.5612 | 0.6147 | 0.3742 | worst log_loss |

Per-season CatBoost log_loss win-rate vs RF (across 5 seeds): 2022 = 0%, 2023 ≤ 20%, 2024 = 100% (catboost_lr02) / 40% (catboost), 2025 ≤ 20%. The only stable CatBoost win is 2024, and its margin is negligible (catboost_lr02 0.6785 vs RF 0.6792, delta -0.00072).

Decision: Do NOT adopt a season-dependent CatBoost switch. The earlier "CatBoost best in 2022/2024/2025" pattern does not generalize across seeds; only 2024 holds, with a trivial margin. Keep `random_forest` as the single default. `catboost_lr02` stays a watchlist-only challenger, not a selection rule.

Follow-up: None. Revisit only if a future feature set materially changes 2024-style seasons.

## New Experiment Entry Template

### YYYY-MM-DD - Experiment Name

- Output:
- Baseline:
- Candidate:
- Reason:
- Change from previous:

| model_or_variant | log_loss | brier_score | accuracy | confidence_metric | coverage | delta_vs_baseline | read |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
|  |  |  |  |  |  |  |  |

Decision:

Follow-up:
