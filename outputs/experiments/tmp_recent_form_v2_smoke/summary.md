# MLB Recent Form v2 Ablation

Baseline: `baseline + random_forest`

## Variant Feature Counts

| variant | rows | columns | recent_columns_kept |
| --- | --- | --- | --- |
| baseline | 12148 | 242 | 0 |
| v2_core | 12148 | 262 | 20 |

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v2_core | random_forest_shallow | 0.6786100933313953 |  | 0.24278569255517377 | 0.5674897119341564 | 0.6230936819172114 | 0.18888888888888888 | 227.0 |
| baseline | random_forest_shallow | 0.6794091302423944 |  | 0.24320149006962946 | 0.5654320987654321 | 0.6577777777777778 | 0.18518518518518517 | 207.0 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest_shallow |  |  | 0.0 |  | 0.0 |
| v2_core | random_forest_shallow |  |  | 0.0 |  | 0.0 |
