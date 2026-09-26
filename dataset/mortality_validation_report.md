# Validation report - synthetic heat-related mortality dataset

**DATA HONESTY: every record is SYNTHETIC (`data_type = SYNTHETIC`). This is NOT NCRB, IMD, official or real 2025/2026 mortality data. Correlations below describe a simulation, not causal epidemiology, and nothing here is a mortality forecast.**

Reference paper (calibration only): Guin, Bhan & Sethi (2025), *Temperature* 12(2):179-199. Seed 20260924; window 2025-09-24 to 2026-09-23.

## 1. Dataset dimensions
1095 rows x 61 columns; 365 days x 3 states. Integrity checks passed: total = heatstroke + other; male+female = total; age groups sum to total; all rows SYNTHETIC.

## 2. State-wise summary
| state | population | days | heatstroke | other | total | expected | max_daily | mean_tmax | max_tmax | mean_wbgt | max_wbgt | heatwave_days | rate_per_100k_year |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Karnataka | 68000000 | 365 | 14 | 38 | 52 | 48.00 | 4 | 30.90 | 39.12 | 25.98 | 30.72 | 6 | 0.08 |
| Kerala | 35800000 | 365 | 7 | 7 | 14 | 20.00 | 2 | 31.35 | 35.74 | 28.32 | 32.34 | 2 | 0.04 |
| Tamil Nadu | 77000000 | 365 | 24 | 76 | 100 | 96.00 | 5 | 33.15 | 40.37 | 28.82 | 33.92 | 10 | 0.13 |

## 3. Monthly distribution of simulated deaths
| month | Tamil Nadu | Kerala | Karnataka |
|---|---|---|---|
| 2025-09 | 0 | 0 | 1 |
| 2025-10 | 3 | 0 | 0 |
| 2025-11 | 1 | 0 | 1 |
| 2025-12 | 1 | 1 | 6 |
| 2026-01 | 3 | 2 | 3 |
| 2026-02 | 4 | 2 | 3 |
| 2026-03 | 11 | 2 | 7 |
| 2026-04 | 19 | 2 | 13 |
| 2026-05 | 26 | 3 | 6 |
| 2026-06 | 14 | 2 | 6 |
| 2026-07 | 11 | 0 | 3 |
| 2026-08 | 5 | 0 | 1 |
| 2026-09 | 2 | 0 | 2 |

![monthly](charts/monthly_deaths.png)

## 4-5. Temperature, WBGT and humidity distributions
| level_0 | level_1 | Karnataka | Kerala | Tamil Nadu |
|---|---|---|---|---|
| maximum_temperature_c | count | 365.00 | 365.00 | 365.00 |
| maximum_temperature_c | mean | 30.90 | 31.35 | 33.15 |
| maximum_temperature_c | std | 2.85 | 1.78 | 2.94 |
| maximum_temperature_c | min | 25.55 | 26.97 | 27.14 |
| maximum_temperature_c | 25% | 28.60 | 30.31 | 30.76 |
| maximum_temperature_c | 50% | 30.54 | 31.24 | 32.95 |
| maximum_temperature_c | 75% | 33.03 | 32.78 | 35.70 |
| maximum_temperature_c | max | 39.12 | 35.74 | 40.37 |
| wbgt_c | count | 365.00 | 365.00 | 365.00 |
| wbgt_c | mean | 25.98 | 28.32 | 28.82 |
| wbgt_c | std | 1.72 | 1.24 | 2.06 |
| wbgt_c | min | 21.78 | 24.99 | 24.19 |
| wbgt_c | 25% | 24.70 | 27.55 | 27.27 |
| wbgt_c | 50% | 25.93 | 28.35 | 28.55 |
| wbgt_c | 75% | 27.15 | 29.13 | 30.54 |
| wbgt_c | max | 30.72 | 32.34 | 33.92 |
| relative_humidity_percent | count | 365.00 | 365.00 | 365.00 |
| relative_humidity_percent | mean | 65.95 | 77.01 | 69.43 |
| relative_humidity_percent | std | 11.84 | 8.59 | 8.62 |
| relative_humidity_percent | min | 36.70 | 59.30 | 51.40 |
| relative_humidity_percent | 25% | 55.00 | 69.90 | 62.50 |
| relative_humidity_percent | 50% | 67.70 | 76.70 | 69.40 |
| relative_humidity_percent | 75% | 76.10 | 83.10 | 75.20 |
| relative_humidity_percent | max | 90.70 | 98.00 | 92.20 |

WBGT category breakdown (all states):

| wbgt_category | days | mean_deaths_per_day | total_deaths | mean_expected | share_of_deaths_pct |
|---|---|---|---|---|---|
| LOW | 593 | 0.08 | 47 | 0.08 | 28.31 |
| CAUTION | 350 | 0.10 | 36 | 0.10 | 21.69 |
| DANGER | 129 | 0.43 | 56 | 0.39 | 33.73 |
| EXTREME | 23 | 1.17 | 27 | 1.29 | 16.27 |

## 6-7. Heatwave vs non-heatwave days
| heatwave_day | days | mean_deaths_per_day | total |
|---|---|---|---|
| False | 1077 | 0.14 | 152 |
| True | 18 | 0.78 | 14 |

By state:

| state | heatwave_day | days | mean_deaths_per_day | total |
|---|---|---|---|---|
| Karnataka | False | 359 | 0.13 | 47 |
| Karnataka | True | 6 | 0.83 | 5 |
| Kerala | False | 363 | 0.04 | 14 |
| Kerala | True | 2 | 0.00 | 0 |
| Tamil Nadu | False | 355 | 0.26 | 91 |
| Tamil Nadu | True | 10 | 0.90 | 9 |

## 8. Male / female
Total heat-related: male:female = 1.77. Heatstroke only: 3.50 (paper: 31/8 = 3.9 state-year means; 3-5x nationally, Fig. 1c).

## 9. Age distribution
Total heat-related: <30 = 6.6%, 30-59 = 36.1%, 60+ = 57.2%.
Heatstroke component only (compare with paper Table 1 means): <30 = 4.4% (paper 12.8%), 30-59 = 53.3% (paper 59.0%), 60+ = 42.2% (paper 28.2%). Shares are tilted by each state's synthetic elderly share, and only ~45 heatstroke deaths were simulated, so shares are noisy and exact agreement is not expected.

## 10. Correlation matrix (Pearson, pooled)
| index | maximum_temperature_c | heat_index_c | wbgt_c | cumulative_heat_load_7day | consecutive_hot_days | relative_humidity_percent | heat_related_deaths_total | expected_heat_related_deaths |
|---|---|---|---|---|---|---|---|---|
| maximum_temperature_c | 1.000 | 0.860 | 0.848 | 0.755 | 0.406 | -0.666 | 0.321 | 0.673 |
| heat_index_c | 0.860 | 1.000 | 0.986 | 0.779 | 0.418 | -0.223 | 0.296 | 0.619 |
| wbgt_c | 0.848 | 0.986 | 1.000 | 0.743 | 0.380 | -0.191 | 0.264 | 0.556 |
| cumulative_heat_load_7day | 0.755 | 0.779 | 0.743 | 1.000 | 0.640 | -0.346 | 0.370 | 0.810 |
| consecutive_hot_days | 0.406 | 0.418 | 0.380 | 0.640 | 1.000 | -0.192 | 0.335 | 0.699 |
| relative_humidity_percent | -0.666 | -0.223 | -0.191 | -0.346 | -0.192 | 1.000 | -0.205 | -0.424 |
| heat_related_deaths_total | 0.321 | 0.296 | 0.264 | 0.370 | 0.335 | -0.205 | 1.000 | 0.429 |
| expected_heat_related_deaths | 0.673 | 0.619 | 0.556 | 0.810 | 0.699 | -0.424 | 0.429 | 1.000 |

Deaths vs drivers, Pearson and Spearman (pooled):

| index | Pearson | Spearman |
|---|---|---|
| maximum_temperature_c | 0.321 | 0.274 |
| heat_index_c | 0.296 | 0.230 |
| wbgt_c | 0.264 | 0.225 |
| cumulative_heat_load_7day | 0.370 | 0.232 |
| consecutive_hot_days | 0.335 | 0.212 |
| relative_humidity_percent | -0.205 | -0.205 |

Pearson by state (deaths vs Tmax / heat index / WBGT):

| index | Tamil Nadu | Kerala | Karnataka |
|---|---|---|---|
| maximum_temperature_c | 0.397 | 0.168 | 0.183 |
| heat_index_c | 0.427 | 0.168 | 0.185 |
| wbgt_c | 0.417 | 0.158 | 0.162 |

Correlation is not causation; the simulation only encodes the relationships written into the generator. Daily counts are small, so daily correlations are modest by design.

## 11-12. Temperature and WBGT relationships
| tbin | days | mean_deaths_per_day | mean_expected |
|---|---|---|---|
| (0, 30] | 292 | 0.05 | 0.05 |
| (30, 32] | 331 | 0.05 | 0.06 |
| (32, 34] | 244 | 0.11 | 0.12 |
| (34, 36] | 141 | 0.29 | 0.27 |
| (36, 38] | 72 | 0.62 | 0.58 |
| (38, 40] | 13 | 1.23 | 1.20 |
| (40, 50] | 2 | 1.50 | 1.93 |

| wbin | days | mean_deaths_per_day |
|---|---|---|
| (0, 26] | 226 | 0.08 |
| (26, 28] | 370 | 0.08 |
| (28, 30] | 347 | 0.10 |
| (30, 32] | 129 | 0.43 |
| (32, 35] | 23 | 1.17 |

![bins](charts/deaths_by_temperature_wbgt.png)
![tn](charts/tamil_nadu_timeseries.png)

The relationship is convex but noisy: some hot days have zero deaths and some moderate days have several.

## 13. Lag relationship
| lag_days | corr_deaths_vs_Tmax_lag | corr_deaths_vs_WBGT_lag |
|---|---|---|
| 0.000 | 0.321 | 0.264 |
| 1.000 | 0.306 | 0.240 |
| 2.000 | 0.311 | 0.237 |
| 3.000 | 0.318 | 0.246 |
| 4.000 | 0.304 | 0.230 |
| 5.000 | 0.293 | 0.212 |
| 6.000 | 0.279 | 0.193 |
| 7.000 | 0.295 | 0.208 |
| 8.000 | 0.290 | 0.209 |
| 9.000 | 0.282 | 0.202 |
| 10.000 | 0.264 | 0.182 |

| index | corr_with_deaths |
|---|---|
| heat_exposure_index | 0.408 |
| lag_1 | 0.329 |
| lag_2 | 0.325 |
| lag_3 | 0.359 |
| lag_7 | 0.311 |
| cum_3day | 0.379 |
| cum_7day | 0.370 |

![lag](charts/lag_correlation.png)

## 14. Comparison with the paper
| index | paper (NCRB heatstroke, 2001-14) | synthetic heatstroke (365 d) | synthetic total heat-related |
|---|---|---|---|
| Tamil Nadu | 16.3/yr | 24 | 100 |
| Kerala | 0.7/yr | 7 | 14 |
| Karnataka | 6.9/yr | 14 | 52 |

- Ordering TN > KA > KL matches the paper (228 > 97 > 10 cumulative). Synthetic annual heatstroke targets (TN 24, KA 12, KL 5) are ASSUMPTIONS anchored on, not equal to, the paper: they are above the paper's per-year averages (TN 16.3, KA 6.9, KL 0.7) because NCRB counts are police-recorded and likely undercounted, and Kerala was deliberately not set to near-zero because of humidity-driven stress.
- Paper sensitivity: +8.028 deaths per +1C average summer max, mean 39 deaths/state-year, i.e. +20.6%. Simulated: +1C on all Apr-Jun Tmax raises annual expected heatstroke deaths by 20.6% on average (TN 42.2%, KL 14.3%, KA 5.3%). The mean is calibrated to the target; the state split is an outcome of the model.
- Sex ratio and age shares: see sections 8-9 (heatstroke component approximates the paper's Table 1 cell means).
- Threshold shape: the paper's spline (Table 7) finds the largest per-degree effect in the 33-38C bin and an insignificant/negative effect above 38C (total deaths -8.96, SE 8.29), which the authors attribute to adaptation. The requested design instead makes extreme heat the steepest part. The quadratic model (Table 6, positive squared term 0.798, significant) supports convexity, but this is a **known divergence** from the piecewise result. The paper's data are annual state means, so a daily curve cannot be identified from it.
- Not comparable: the paper's mean of 39 is per state-year over 24 states; the max 418 and SD 53.9 are not reproduced (3 small states only).

## 15. Limitations
State-level only (no districts); weather is simulated, not IMD data; WBGT is an approximation; heatwave rule is IMD-inspired, not official; the 3:1 ratio of other heat-related deaths to heatstroke is an assumption; demographic values are assumptions; daily counts are very small; annual totals are calibrated to assumed targets; NCRB heatstroke counts are conservative and ecological; a 365-day window gives one hot season, so multi-year variability is absent. Do not use for real risk estimation or policy.

## Example: analogue search (hypothetical day: WBGT 32.5, Tmax 38.1, RH 64%, 3 consecutive heat days)
Fields used: max_temperature_c, humidity_percent, wbgt_c, consecutive_heat_days.

**CURRENT THERMAL RISK:** WBGT band: EXTREME

**HISTORICAL ANALOGUES (top 5):**

| date | state | similarity_score | maximum_temperature_c | relative_humidity_percent | wbgt_c | heat_related_deaths_total |
|---|---|---|---|---|---|---|
| 2026-04-01 | Tamil Nadu | 79.42 | 38.30 | 59.60 | 32.34 | 0 |
| 2026-06-24 | Tamil Nadu | 72.88 | 37.02 | 62.40 | 32.11 | 2 |
| 2026-03-31 | Tamil Nadu | 65.69 | 36.51 | 63.50 | 31.43 | 2 |
| 2026-05-13 | Tamil Nadu | 63.97 | 37.61 | 58.20 | 31.54 | 0 |
| 2026-06-26 | Tamil Nadu | 63.21 | 37.41 | 66.30 | 32.46 | 0 |

**EXPECTED HEALTH IMPACT:** Historical SYNTHETIC scenarios with similar thermal conditions were associated with an average of 0.80 simulated heat-related deaths/day (5 closest days) and 0.88 (25 closest). This is a model-estimated heat-related mortality burden for decision support, not a forecast for any individual or day.

**VULNERABLE POPULATIONS:** Among the 25 closest analogues: deaths under 30 / 30-59 / 60+ = 0 / 10 / 12; male / female = 10 / 12 (simulated; small counts, noisy).

**RECOMMENDED PRECAUTIONS:** Suspend non-essential outdoor labour in peak hours, open cooling shelters, alert hospitals, frequent welfare checks on elderly and isolated people.

*Decision-support indicator, not an individual medical prediction.*
