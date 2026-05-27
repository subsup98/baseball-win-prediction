# Multi-Seed Model Experiment

Baseline: `full + random_forest`

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | random_forest | 0.6795482191816505 | 0.0017236862372078526 | 0.24328601185318832 | 0.000862244788514055 | 0.5650587127084086 | 0.009740421945976536 | 0.6599264787690073 | 0.18509979720354358 | 161.5 |
| full | catboost_lr02 | 0.6806693299527025 | 0.0022546655781587968 | 0.2437737640948038 | 0.001106472487376307 | 0.5668484803819418 | 0.010273072469306229 | 0.624636139477186 | 0.3191238583169419 | 161.5 |
| full | catboost | 0.6839074599186856 | 0.004063694382572134 | 0.24522013226071776 | 0.0018571720328426026 | 0.5611895528482144 | 0.010416564499905637 | 0.6147034751087693 | 0.37423144886801624 | 161.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| full | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| full | catboost_lr02 | 0.0011211107710518476 | 0.0011573978381580474 | 0.35 | 0.0017897676735332934 | 0.65 |
| full | catboost | 0.0043592407370349915 | 0.0029434930867565656 | 0.1 | -0.00386915986019411 | 0.35 |
