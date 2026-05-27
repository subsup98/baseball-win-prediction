# OOF Selective Pick Report

Models: `random_forest, random_forest_shallow, soft_voting`
Primary model: `random_forest`
Agreement challengers: `random_forest_shallow, soft_voting`
Thresholds: lean `0.54`, strong `0.57`

## Actionable Summary

| rule_name | model_name | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| model:random_forest | random_forest | actionable | 5718 | 5718 | 3389.0 | 0.5926897516614201 | 0.5883321329354871 | 0.5876768584278076 |
| model:random_forest_shallow | random_forest_shallow | actionable | 5197 | 5197 | 3101.0 | 0.5966903983067154 | 0.5347257948348596 | 0.5801204185607017 |
| model:soft_voting | soft_voting | actionable | 5702 | 5702 | 3458.0 | 0.606453875833041 | 0.586685873032205 | 0.5855113411331029 |
| agreement | random_forest | actionable | 5558 | 5558 | 3294.0 | 0.5926592299388269 | 0.5718695339026649 | 0.5886674453042058 |

## Agreement By Holdout

| holdout_season | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | actionable | 1386 | 1386 | 835.0 | 0.6024531024531025 | 0.5703703703703704 | 0.591794295252404 |
| 2023 | actionable | 1415 | 1415 | 807.0 | 0.5703180212014134 | 0.5823045267489712 | 0.5886933390151518 |
| 2024 | actionable | 1343 | 1343 | 808.0 | 0.6016381236038719 | 0.5529024289831206 | 0.5864128807957736 |
| 2025 | actionable | 1414 | 1414 | 844.0 | 0.5968882602545968 | 0.5818930041152264 | 0.5877179590988542 |
