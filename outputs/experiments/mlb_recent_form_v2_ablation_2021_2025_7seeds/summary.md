# MLB Recent Form v2 Ablation

Baseline: `baseline + random_forest`

## Variant Feature Counts

| variant | rows | columns | recent_columns_kept |
| --- | --- | --- | --- |
| baseline | 12148 | 242 | 0 |
| pythag_only | 12148 | 247 | 5 |
| volatility_only | 12148 | 244 | 2 |
| scoring_only | 12148 | 254 | 12 |

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| volatility_only | random_forest | 0.6796817540332505 | 0.0014831052620382524 | 0.243357462418115 | 0.5646526550991122 | 0.6449788113922267 | 0.20782265124358348 | 210.5 |
| pythag_only | random_forest | 0.6797596438229944 | 0.0013207737545164798 | 0.24338935049269694 | 0.5649607162037975 | 0.6428294533923109 | 0.20786752954997773 | 213.5 |
| baseline | random_forest | 0.6798157301071038 | 0.001217484553917308 | 0.24342028796493903 | 0.5632561150549806 | 0.6482703179671324 | 0.20505917740490726 | 208.5 |
| scoring_only | random_forest | 0.6799717651099222 | 0.0011145402494063795 | 0.2434951099254472 | 0.5630944454488666 | 0.6451404713552511 | 0.2070293392911297 | 220.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| volatility_only | random_forest | -0.000133976073853233 | -6.45785843224056e-05 | 0.5714285714285714 | 0.0013965400441316564 | 0.5357142857142857 |
| pythag_only | random_forest | -5.608628410945306e-05 | 9.858517252325782e-06 | 0.4642857142857143 | 0.0017046011488168953 | 0.5357142857142857 |
| baseline | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| scoring_only | random_forest | 0.00015603500281843478 | -6.512394804109034e-05 | 0.5357142857142857 | -0.00016166960611404705 | 0.5 |
