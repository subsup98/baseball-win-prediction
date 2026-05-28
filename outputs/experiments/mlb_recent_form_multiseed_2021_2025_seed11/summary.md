# Multi-Seed Model Experiment

Baseline: `baseline + random_forest`

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.6792607027706233 | 0.0012229780282539515 | 0.24314157412033424 | 0.0006428484717830028 | 0.5662116029391085 | 0.013138955820213988 | 0.6625666822849288 | 0.1874661794130254 | 161.5 |
| baseline | random_forest_shallow | 0.6801626623972055 | 0.0014765564243876363 | 0.24358170248800365 | 0.0007465365796626708 | 0.5683720967662691 | 0.0093278082271266 | 0.6817004558341786 | 0.12645057916431596 | 161.5 |
| recent_form | random_forest | 0.6808843157702394 | 0.001108094320128272 | 0.2439264791264789 | 0.0005691167967885475 | 0.5605513878088325 | 0.01006024246804793 | 0.6424535272061217 | 0.20351662100781537 | 244.5 |
| recent_form | random_forest_shallow | 0.6813382702505254 | 0.0015215653670442727 | 0.2441566211340656 | 0.0007659463041444082 | 0.5596253771726074 | 0.006549597081079745 | 0.6480677793776856 | 0.15680278764652764 | 244.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline | random_forest_shallow | 0.0009019596265820995 | 0.0009482334950942084 | 0.0 | 0.0021604938271604923 | 0.25 |
| recent_form | random_forest | 0.0016236129996160809 | 0.0015126552997924425 | 0.0 | -0.005660215130276008 | 0.25 |
| recent_form | random_forest_shallow | 0.002077567479902065 | 0.001753706079461348 | 0.0 | -0.006586225766501197 | 0.25 |
