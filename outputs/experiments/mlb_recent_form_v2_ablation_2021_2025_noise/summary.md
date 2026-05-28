# MLB Recent Form v2 Ablation

Baseline: `baseline + random_forest`

## Variant Feature Counts

| variant | rows | columns | recent_columns_kept |
| --- | --- | --- | --- |
| volatility_only | 12148 | 244 | 2 |
| close_game_only | 12148 | 249 | 7 |
| v1_full | 12148 | 278 | 36 |

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| volatility_only | random_forest | 0.6796820173694583 | 0.0014006105979020458 | 0.24335821141351047 | 0.5650443514890094 | 0.6450344311268489 | 0.2091061030382196 | 210.5 |
| close_game_only | random_forest | 0.67981993503198 | 0.0012314398625069304 | 0.24342506283135054 | 0.5654904782799969 | 0.6473445145927542 | 0.2036874675630146 | 215.5 |
| close_game_only | random_forest_shallow | 0.6802498083162235 | 0.0009360192492485904 | 0.24363189466538618 | 0.5639815196011161 | 0.6652986758776342 | 0.15189814603039067 | 215.5 |
| volatility_only | random_forest_shallow | 0.6803763763837751 | 0.001061343641465189 | 0.2436948267747997 | 0.5642214756421182 | 0.6611837920564951 | 0.15155460341179203 | 210.5 |
| v1_full | random_forest_shallow | 0.6809217579210533 | 0.0015967354792285162 | 0.24395557263731912 | 0.5596597271989523 | 0.6544847351725799 | 0.1578659583756179 | 244.5 |
| v1_full | random_forest | 0.6810040179549909 | 0.0014072678357880059 | 0.24399249119459995 | 0.561065748745864 | 0.6375110944111687 | 0.20598599682279906 | 244.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| close_game_only | random_forest |  |  | 0.0 |  | 0.0 |
| close_game_only | random_forest_shallow |  |  | 0.0 |  | 0.0 |
| v1_full | random_forest |  |  | 0.0 |  | 0.0 |
| v1_full | random_forest_shallow |  |  | 0.0 |  | 0.0 |
| volatility_only | random_forest |  |  | 0.0 |  | 0.0 |
| volatility_only | random_forest_shallow |  |  | 0.0 |  | 0.0 |
