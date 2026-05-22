# Confidence-Band Selection Rule Check

Source: outputs/experiments/model_multiseed_rf_pruning_confirmed_2021_2025/metrics_by_seed_holdout.csv

Files:
- model_confidence_summary.csv
- rule_comparison_vs_rf.csv

Model confidence summary:
```text
           model_name  mean_log_loss  mean_accuracy  mean_accuracy_conf_55  mean_coverage_conf_55  mean_accuracy_conf_60  mean_coverage_conf_60  mean_accuracy_conf_65  mean_coverage_conf_65
        random_forest       0.679496       0.565069               0.604359               0.500811               0.657115               0.185079               0.686142               0.043584
random_forest_shallow       0.680243       0.567127               0.607532               0.442531               0.678148               0.127459               0.695479               0.016071
```

Rule comparison vs random_forest:
```text
                        rule                 model  log_loss_delta_vs_rf  accuracy_delta_vs_rf  accuracy_conf_60_delta_vs_rf  coverage_conf_60_delta_vs_rf                  read
        always_random_forest         random_forest              0.000000              0.000000                      0.000000                       0.00000         main baseline
always_random_forest_shallow random_forest_shallow              0.000746              0.002058                      0.021033                      -0.05762 confidence challenger
```

Readout: full + random_forest_shallow improves mean accuracy_conf_60 versus full + random_forest, but it does so with lower coverage_conf_60 and worse overall log loss. Keep full + random_forest as the default probability model and use full + random_forest_shallow only as a selective confidence-band challenger until prediction-level blending is implemented.
