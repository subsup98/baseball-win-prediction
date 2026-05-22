# Feature Set Update Comparison

Baseline:

- `baseline_features_confirmed_2021_2025_with_park_factors_statcast.csv`
- previous `season_holdout_confirmed_2021_2025_with_park_factors_statcast`

Latest:

- `data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv`
- refreshed `outputs/experiments/season_holdout_confirmed_2021_2025_with_park_factors_statcast`

## Feature Shape

| version | columns |
| --- | ---: |
| baseline | 121 |
| latest | 173 |
| added | 52 |

## Mean Metric Delta

Delta is `latest - baseline`. Lower is better for `log_loss` and `brier_score`; higher is better for `accuracy`.

| model | log_loss_delta | brier_score_delta | accuracy_delta |
| --- | ---: | ---: | ---: |
| elo | 0.000000 | 0.000000 | 0.000000 |
| logistic | 0.000310 | 0.000101 | 0.004321 |
| random_forest | -0.000246 | -0.000130 | 0.002572 |

## Random Forest By Season

| holdout | log_loss_delta | accuracy_delta |
| --- | ---: | ---: |
| 2022 | 0.000720 | 0.003292 |
| 2023 | -0.000755 | -0.002881 |
| 2024 | -0.001108 | 0.001647 |
| 2025 | 0.000160 | 0.008230 |

## Read

The refreshed feature set is mildly positive for the current strongest model, `random_forest`: average log loss improved by `0.000246`, average brier score improved by `0.000130`, and average accuracy improved by `0.257 percentage points`.

The improvement is not uniform. 2023 and 2024 log loss improved, while 2022 and 2025 were slightly worse. This should be treated as a small incremental gain, not a decisive feature breakthrough.

The features with actual coverage are mostly:

- starter pitch-mix / Stuff: whiff rate, fastball velocity, spin, pitch usage
- lineup continuity counts
- home/away streak and rest-day travel proxies
- high-leverage bullpen role proxy

The currently unavailable source-dependent columns are still all-null:

- lineup confidence / availability / expected starter ratios
- venue distance and timezone shift

Those columns need upstream source enrichment before they can influence model training.
