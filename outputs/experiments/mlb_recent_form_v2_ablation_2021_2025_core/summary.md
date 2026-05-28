# MLB Recent Form v2 Ablation

Baseline: `baseline + random_forest`

## Variant Feature Counts

| variant | rows | columns | recent_columns_kept |
| --- | --- | --- | --- |
| baseline | 12148 | 242 | 0 |
| v2_core | 12148 | 262 | 20 |
| run_diff_only | 12148 | 247 | 5 |

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.6799421496057289 | 0.0011438517857420578 | 0.2434854668475541 | 0.5616834421295943 | 0.6485709266346289 | 0.2058134842983813 | 208.5 |
| run_diff_only | random_forest_shallow | 0.6800200016955592 | 0.001308843392112509 | 0.24352153859573766 | 0.5647016136182536 | 0.6592641122363779 | 0.15690532946376687 | 213.5 |
| run_diff_only | random_forest | 0.6800641227606402 | 0.0011330676711359708 | 0.24353871496207288 | 0.5643588616291145 | 0.6431407765438576 | 0.2080775505847552 | 213.5 |
| baseline | random_forest_shallow | 0.6804863116924746 | 0.0010256136579707077 | 0.24374728178167046 | 0.5644958523013811 | 0.6575665900048603 | 0.15405841396341982 | 208.5 |
| v2_core | random_forest_shallow | 0.6805013029708831 | 0.001568010494840758 | 0.24375386316823397 | 0.5609285604162325 | 0.6539930724420305 | 0.1592716128445662 | 228.5 |
| v2_core | random_forest | 0.6805474769062188 | 0.001530549353944788 | 0.2437782146580166 | 0.5614091360622474 | 0.6381071928942716 | 0.20715189290811023 | 228.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| run_diff_only | random_forest_shallow | 7.785208983037324e-05 | 0.0002673987985858939 | 0.3333333333333333 | 0.0030181714886592568 | 0.6666666666666666 |
| run_diff_only | random_forest | 0.00012197315491141447 | 0.00018437506433327533 | 0.4166666666666667 | 0.002675419499520243 | 0.75 |
| baseline | random_forest_shallow | 0.0005441620867457364 | 0.0006595623882611479 | 0.25 | 0.0028124101717868313 | 0.75 |
| v2_core | random_forest_shallow | 0.0005591533651542376 | 0.0007674213326952506 | 0.25 | -0.0007548817133617991 | 0.5 |
| v2_core | random_forest | 0.0006053273004898533 | 0.0006802610359927241 | 0.16666666666666666 | -0.0002743060673469448 | 0.5 |
