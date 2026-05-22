# Multi-Seed Model Experiment

Baseline: `full + random_forest`

## Summary By Variant And Model

| variant | model_name | mean_log_loss | std_log_loss | mean_brier_score | std_brier_score | mean_accuracy | std_accuracy | mean_accuracy_conf_60 | mean_coverage_conf_60 | mean_feature_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| without_bullpen_role | random_forest | 0.6793894098120326 | 0.0019010495471922049 | 0.24320800823692856 | 0.0009483264144457939 | 0.5659743759815805 | 0.009151717072683375 | 0.6535794548960314 | 0.18598439720998158 | 159.5 |
| full | random_forest | 0.6794961913651129 | 0.0018059870576879996 | 0.24326017022878005 | 0.0009037741240194445 | 0.5650687254657796 | 0.00889652512916662 | 0.6571152499326083 | 0.18507903894471298 | 161.5 |
| full | random_forest_shallow | 0.6802425315386784 | 0.0015365498671654513 | 0.24362051216725594 | 0.000772055785823226 | 0.5671269485486585 | 0.00961520490542375 | 0.6781479004617201 | 0.12745899597964921 | 161.5 |
| without_bullpen_role | random_forest_shallow | 0.6803019538012607 | 0.0015645209962878433 | 0.24364841452775843 | 0.0007845559859940197 | 0.5667358580390921 | 0.008511731299883576 | 0.6742869248047978 | 0.12736666598898427 | 159.5 |

## Stability Vs Baseline

| variant | model_name | mean_log_loss_delta_vs_baseline | median_log_loss_delta_vs_baseline | log_loss_win_rate_vs_baseline | mean_accuracy_delta_vs_baseline | accuracy_win_rate_vs_baseline |
| --- | --- | --- | --- | --- | --- | --- |
| without_bullpen_role | random_forest | -0.00010678155308039006 | -0.00021628632230097367 | 0.55 | 0.000905650515801018 | 0.55 |
| full | random_forest | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| full | random_forest_shallow | 0.0007463401735655739 | 0.0006575688289336967 | 0.125 | 0.002058223082878874 | 0.625 |
| without_bullpen_role | random_forest_shallow | 0.0008057624361477833 | 0.0007696176262985133 | 0.2 | 0.0016671325733125352 | 0.55 |
