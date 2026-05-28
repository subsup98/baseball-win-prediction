# Multi-Seed Model Experiment

Baseline: `baseline + random_forest`

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.6795371629398106 | 0.002009087796364557 | 0.2432810116160869 | 0.0010022334738647944 | 0.5674454084476499 | 0.008000324521519626 | 0.6550692540135172 | 0.1811902474726682 | 161.5 |
| baseline | random_forest_shallow | 0.6804857391025843 | 0.0018767417128350817 | 0.2437383667189223 | 0.0009415997982499444 | 0.5671374865098848 | 0.011565688183154328 | 0.6785124713471714 | 0.12480410743298992 | 161.5 |
| recent_form | random_forest_shallow | 0.6809094682997197 | 0.0021437206582042086 | 0.2439480232945093 | 0.0010709195959089936 | 0.5577731017692593 | 0.009609532514372464 | 0.6530113894156356 | 0.15567110040372928 | 244.5 |
| recent_form | random_forest | 0.6811242311939483 | 0.0017688010964748428 | 0.24405766498059228 | 0.0008800937921767632 | 0.5614767631178134 | 0.00987869855981049 | 0.6335410503051456 | 0.20588296086214755 | 244.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| baseline | random_forest_shallow | 0.0009485761627737455 | 0.0008597718773553642 | 0.0 | -0.0003079219377650211 | 0.75 |
| recent_form | random_forest_shallow | 0.0013723053599091484 | 0.0011063821780046834 | 0.25 | -0.009672306678390585 | 0.0 |
| recent_form | random_forest | 0.0015870682541377912 | 0.0015887662208922682 | 0.0 | -0.005968645329836486 | 0.0 |
