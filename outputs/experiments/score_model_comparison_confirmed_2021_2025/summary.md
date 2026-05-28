# Score Model Comparison (Expected Runs)

Models: ridge, random_forest_regressor, gradient_boosting_regressor, hist_gradient_boosting_regressor, lightgbm_regressor, catboost_regressor
Holdouts: 2022, 2023, 2024, 2025

## Mean Metrics By Model (lower MAE/RMSE is better)

| model_name | mean_total_mae | mean_total_rmse | mean_home_mae | mean_away_mae | mean_run_diff_mae | mean_total_within_1 | mean_total_within_2 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| catboost_regressor | 3.4661 | 4.3844 | 2.4114 | 2.493 | 3.4351 | 0.1769 | 0.3508 |
| gradient_boosting_regressor | 3.491 | 4.4159 | 2.4272 | 2.5097 | 3.4512 | 0.1808 | 0.3468 |
| random_forest_regressor | 3.5005 | 4.4111 | 2.4169 | 2.5066 | 3.4346 | 0.1752 | 0.3451 |
| ridge | 3.5037 | 4.4347 | 2.4392 | 2.5292 | 3.4699 | 0.1766 | 0.3478 |
| lightgbm_regressor | 3.5218 | 4.449 | 2.4505 | 2.5245 | 3.4715 | 0.1785 | 0.3442 |
| hist_gradient_boosting_regressor | 3.5447 | 4.4801 | 2.4659 | 2.5409 | 3.5018 | 0.1765 | 0.3439 |

## Mean Synthetic O/U Accuracy At 8.5 Line

| model_name | mean_ou_accuracy_8_5 |
| --- | --- |
| catboost_regressor | 0.5529 |
| gradient_boosting_regressor | 0.552 |
| ridge | 0.549 |
| lightgbm_regressor | 0.5482 |
| hist_gradient_boosting_regressor | 0.5389 |
| random_forest_regressor | 0.5372 |

## Best Model Per Holdout (by total_mae)

| holdout_season | model_name | total_mae | total_rmse |
| --- | --- | --- | --- |
| 2022 | catboost_regressor | 3.4958 | 4.4009 |
| 2023 | catboost_regressor | 3.5564 | 4.511 |
| 2024 | catboost_regressor | 3.2846 | 4.1621 |
| 2025 | catboost_regressor | 3.5276 | 4.4634 |
