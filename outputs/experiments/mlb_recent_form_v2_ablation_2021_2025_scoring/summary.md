# MLB Recent Form v2 Ablation

Baseline: `baseline + random_forest`

## Variant Feature Counts

| variant | rows | columns | recent_columns_kept |
| --- | --- | --- | --- |
| scoring_only | 12148 | 254 | 12 |
| pythag_only | 12148 | 247 | 5 |
| weighted_win_only | 12148 | 247 | 5 |

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | mean_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pythag_only | random_forest | 0.6795808466608322 | 0.0014491713827669485 | 0.2432977473523267 | 0.5660385821528954 | 0.6443766640933053 | 0.20554020887300853 | 213.5 |
| scoring_only | random_forest | 0.6797505993903453 | 0.0014215412430596125 | 0.2433874004191208 | 0.5649758349753012 | 0.6474185537576234 | 0.20780362571375485 | 220.5 |
| pythag_only | random_forest_shallow | 0.6801684558628117 | 0.0012718290914942375 | 0.24359091460103555 | 0.5642210379722388 | 0.6561302124735974 | 0.1576599146910813 | 213.5 |
| scoring_only | random_forest_shallow | 0.6804100497093923 | 0.0011802440341897493 | 0.24371042957547862 | 0.5615121720228989 | 0.6555310664637654 | 0.15436736654315905 | 220.5 |
| weighted_win_only | random_forest | 0.6804518602884354 | 0.0013782196089182628 | 0.2437245427423984 | 0.562677926924378 | 0.6439341493037857 | 0.20526526747841722 | 213.5 |
| weighted_win_only | random_forest_shallow | 0.6804571428611798 | 0.0009941810740165167 | 0.24373042683426235 | 0.5638785401139975 | 0.6603660832816854 | 0.15018341191625426 | 213.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| pythag_only | random_forest |  |  | 0.0 |  | 0.0 |
| pythag_only | random_forest_shallow |  |  | 0.0 |  | 0.0 |
| scoring_only | random_forest |  |  | 0.0 |  | 0.0 |
| scoring_only | random_forest_shallow |  |  | 0.0 |  | 0.0 |
| weighted_win_only | random_forest |  |  | 0.0 |  | 0.0 |
| weighted_win_only | random_forest_shallow |  |  | 0.0 |  | 0.0 |
