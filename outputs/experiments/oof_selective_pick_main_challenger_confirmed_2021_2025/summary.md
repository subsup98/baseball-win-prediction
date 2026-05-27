# OOF Selective Pick Report

Models: `random_forest, random_forest_shallow, soft_voting`
Primary model: `random_forest`
Agreement challengers: `random_forest_shallow, soft_voting`
Thresholds: lean `0.55`, strong `0.6`

## Actionable Summary

| rule_name | model_name | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| model:random_forest | random_forest | actionable | 4865 | 4865 | 2937.0 | 0.6036998972250771 | 0.5005659018417533 | 0.5951737726664841 |
| model:random_forest_shallow | random_forest_shallow | actionable | 4276 | 4276 | 2607.0 | 0.6096819457436857 | 0.43996295915217615 | 0.587710191284764 |
| model:soft_voting | soft_voting | actionable | 4874 | 4874 | 2977.0 | 0.6107919573245794 | 0.5014919230373496 | 0.5923782043882174 |
| agreement | random_forest | actionable | 4789 | 4789 | 2893.0 | 0.6040927124660681 | 0.49274616730116266 | 0.5956940184252437 |

## Agreement By Holdout

| holdout_season | rule | games | picks | hits | accuracy | coverage | avg_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | actionable | 1237 | 1237 | 756.0 | 0.6111560226354082 | 0.5090534979423869 | 0.5974374922910277 |
| 2023 | actionable | 1218 | 1218 | 710.0 | 0.5829228243021346 | 0.5012345679012346 | 0.5957480423686112 |
| 2024 | actionable | 1132 | 1132 | 701.0 | 0.6192579505300353 | 0.46603540551667355 | 0.5941950650653544 |
| 2025 | actionable | 1202 | 1202 | 726.0 | 0.6039933444259568 | 0.49465020576131685 | 0.5952566946884703 |
