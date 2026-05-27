# Recent-Season Training Challenger

## target_2026_scored

| model | train_rows | n_games | log_loss | brier | accuracy | acc_conf_60 | cov_conf_60 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_rf_all_seasons | 12148 | 807 | 0.6944 | 0.2506 | 0.5167 | 0.5586 | 0.1375 |
| challenger_rf_2024_2025 | 4859 | 807 | 0.6939 | 0.2503 | 0.5390 | 0.5155 | 0.1202 |
| recency_weighted_rf_hl2 | 12148 | 807 | 0.6933 | 0.2501 | 0.5180 | 0.5895 | 0.1177 |

## holdout_2025

| model | train_rows | n_games | log_loss | brier | accuracy | acc_conf_60 | cov_conf_60 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline_rf_all_seasons | 9718 | 2430 | 0.6797 | 0.2434 | 0.5584 | 0.6524 | 0.1823 |
| challenger_rf_2024 | 2429 | 2430 | 0.6829 | 0.2449 | 0.5527 | 0.6491 | 0.1407 |
| recency_weighted_rf_hl2 | 9718 | 2430 | 0.6813 | 0.2442 | 0.5539 | 0.6547 | 0.1609 |
