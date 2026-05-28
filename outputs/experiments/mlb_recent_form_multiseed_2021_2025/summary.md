# Multi-Seed Model Experiment

Baseline: aseline + random_forest

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.6794781619476113 | 0.0014747846033633923 | 0.24325010907934885 | 0.0007418277154805695 | 0.5657309990563273 | 0.009553613051632872 | 0.6607133781331364 | 0.185751515890805 | 161.5 |
| baseline | random_forest_shallow | 0.6803579645243097 | 0.0015416285987522964 | 0.2436774444326444 | 0.0007760239580196873 | 0.567583246222909 | 0.010303272383702301 | 0.6785739691296601 | 0.12717068729983658 | 161.5 |
| recent_form | random_forest_shallow | 0.6809217579210533 | 0.0015967354792285227 | 0.24395557263731912 | 0.0007976188620337773 | 0.5596597271989523 | 0.006560441882870679 | 0.6544847351725799 | 0.15786595837561787 | 244.5 |
| recent_form | random_forest | 0.6810040179549909 | 0.0014072678357879935 | 0.2439924911945999 | 0.0007103264201918293 | 0.561065748745864 | 0.00927820433076952 | 0.6375110944111687 | 0.20598599682279903 | 244.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline | random_forest_shallow | 0.0008798025766985443 | 0.0007935182422095788 | 0.0 | 0.0018522471665816942 | 0.5833333333333334 |
| recent_form | random_forest_shallow | 0.0014435959734419301 | 0.0012056890178165913 | 0.16666666666666666 | -0.006071271857374966 | 0.25 |
| recent_form | random_forest | 0.0015258560073795706 | 0.0015126552997924425 | 0.08333333333333333 | -0.004665250310463258 | 0.16666666666666666 |
