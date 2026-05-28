# Stable Feature Group Ablation

Stable group: 13 features. Low-stability group: 19 features.

Positive `mean_log_loss_delta_vs_full` means removing that group made log loss worse (the group was helping the full model).

| variant | model_name | mean_feature_count | mean_log_loss | mean_log_loss_delta_vs_full | mean_accuracy | mean_accuracy_delta_vs_full |
| --- | --- | --- | --- | --- | --- | --- |
| without_low_stability | random_forest | 142.5 | 0.679521 | -3.8e-05 | 0.566005 | -0.001338 |
| full | random_forest | 161.5 | 0.679559 | 0.0 | 0.567343 | 0.0 |
| without_stable | random_forest | 148.5 | 0.683308 | 0.003748 | 0.559317 | -0.008026 |
| stable_only | random_forest | 13.0 | 0.685491 | 0.005931 | 0.552732 | -0.014611 |
