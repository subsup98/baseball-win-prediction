# Multi-Seed Model Experiment

Baseline: `baseline + random_forest`

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.6796366201324 | 0.0015302553564643178 | 0.2433277415016255 | 0.0007583243114931913 | 0.5635359857822233 | 0.009347399576912156 | 0.6645041981009627 | 0.1885981207867215 | 161.5 |
| baseline | random_forest_shallow | 0.6804254920731397 | 0.0017126542922114769 | 0.2437122640910074 | 0.0008633659071641078 | 0.567240155392573 | 0.012931323709593268 | 0.6755089802076302 | 0.130257375302204 | 161.5 |
| recent_form | random_forest_shallow | 0.6805175352129146 | 0.0014100815111686823 | 0.24376207348338247 | 0.0007037634834254073 | 0.5615807026549903 | 0.0035921040686507865 | 0.6623750367244183 | 0.16112398707659675 | 244.5 |
| recent_form | random_forest | 0.6810035069007848 | 0.0016930956821140227 | 0.24399332947672858 | 0.0008603098566335845 | 0.561169095310946 | 0.010782201667316327 | 0.6365387057222388 | 0.20855840859843422 | 244.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline | random_forest_shallow | 0.0007888719407397882 | 0.0005417563270302406 | 0.0 | 0.0037041696103496113 | 0.75 |
| recent_form | random_forest_shallow | 0.0008809150805145771 | 0.0008351051076183613 | 0.25 | -0.001955283127233115 | 0.5 |
| recent_form | random_forest | 0.0013668867683848396 | 0.0016022427083897117 | 0.25 | -0.0023668904712772776 | 0.25 |
