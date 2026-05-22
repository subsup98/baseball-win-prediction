# Multi-Seed Model Experiment

Baseline: `full + random_forest`

## Readout

The earlier single-seed result favoring `without_lineup_optional + random_forest` did not hold under 10 random seeds.

Final baseline decision:

- Main baseline: `full + random_forest`
- Confidence-band challenger: `full + random_forest_shallow`

Reasoning:

- `full + random_forest` has the best mean log loss: `0.679496`.
- `without_lineup_optional + random_forest` has nearly identical mean accuracy, but worse mean log loss and only wins `35%` of seed/holdout comparisons against the baseline.
- `full + random_forest_shallow` has worse mean log loss, but better mean accuracy and better `accuracy_conf_60`, so it remains useful only as a selective high-confidence candidate.
- Feature pruning is not stable enough to replace the full feature set.

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | random_forest | 0.6794961913651129 | 0.0018059870576879963 | 0.24326017022878005 | 0.0009037741240194464 | 0.5650687254657796 | 0.00889652512916662 | 0.6571152499326083 | 0.18507903894471298 | 161.5 |
| without_lineup_optional | random_forest | 0.6798960845095515 | 0.0018388951238187804 | 0.24345637751298682 | 0.0009203698416711334 | 0.5650996913156695 | 0.00937493117802543 | 0.6527149716264605 | 0.18820674649765268 | 142.5 |
| full | random_forest_shallow | 0.6802425315386784 | 0.001536549867165454 | 0.24362051216725594 | 0.000772055785823226 | 0.5671269485486585 | 0.00961520490542375 | 0.6781479004617201 | 0.12745899597964921 | 161.5 |
| without_lineup_optional | random_forest_shallow | 0.6803103543781226 | 0.0015713351163350981 | 0.24365387446776282 | 0.0007874965270592195 | 0.5666227782606266 | 0.009055575930307926 | 0.6732788144193582 | 0.12824109652399757 | 142.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| full | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| without_lineup_optional | random_forest | 0.00039989314443871773 | 0.0003186282032038301 | 0.35 | 3.096584988997175e-05 | 0.375 |
| full | random_forest_shallow | 0.0007463401735655628 | 0.0006575688289336967 | 0.125 | 0.002058223082878874 | 0.625 |
| without_lineup_optional | random_forest_shallow | 0.0008141630130096805 | 0.0006712846611875989 | 0.15 | 0.001554052794846908 | 0.55 |
