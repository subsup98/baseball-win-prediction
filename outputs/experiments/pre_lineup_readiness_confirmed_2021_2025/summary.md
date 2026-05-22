# Pre-Lineup Readiness Check

Feature table: data\processed\features_confirmed_2021_2025_with_park_factors_statcast.csv
Feature prediction_mode counts: {'confirmed_lineup': 12148}

Standardized lineup files checked: 5
All season-level lineup files currently contain only confirmed_lineup rows. There are no projected, expected, or pre_lineup rows available for a real pre_lineup holdout report.

Decision: pre_lineup model evaluation is blocked until an upstream projected lineup source is added or historical expected-lineup snapshots are created. Do not treat confirmed_lineup results as pre-game deployable performance.

Next data requirement: collect or construct lineups with prediction_mode in pre_lineup/projected/expected before game start, then rebuild features with --prediction-mode pre_lineup.
