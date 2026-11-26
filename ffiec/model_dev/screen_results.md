# Prod-Lvl Deposit Beta: Model Screen and Estimation Results (v2-rc-6)

> **STATUS: DRAFT, development run, 2026-11-26. NOT VALIDATED.** Ten one-step ECMs (five banks x two segments),
> screened and estimated end to end on data vintage v2-rc-6 (data commit `cddc1d1`), branch
> `model-dev/screen-v2-rc-6` from `model-dev/prod-lvl` at `f0feb82`. Method: origin doc ("WIP Regional Banking
> Deposit Beta Analyses.md" at `73e015e^`, sections 3.3, 5, 6) as amended by `data_description.md` rev 0.13.
> Every departure from the origin method is in section 11; open items needing an owner decision are in section 12.
> Outputs: `ffiec/model_dev/outputs/v2-rc-6/`. Nothing was written outside `ffiec/`; no origin script was edited.

## 0. Run Record

| Item | Value |
| :-- | :-- |
| Dependent file | `ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv` (413 rows); hash checked before every run (`screen_common.check_pinned`) |
| Regressor | `ffiec/model_dev/inputs/v2-rc-3/FFT_2011-2026.csv` (used); `FFT_2008-2026.csv` hash-checked, not used |
| Pinned LF hashes | dependent `1cc31d8694afd042b89aac290f3ab80521abd8306477dff88ac4d4bfc503b1bf`; FFT 2011 `d1c83be581d0c04b04cbeed58084b7ec853a336fa4ed0be8e6364a5870dde1bc`; FFT 2008 `38298c661ff571457fb4c2f7e058ed9c9f4946c06683c81e60b674e375fb18c6`. All matched |
| Banks (run filter) | First Horizon 4977, Huntington 6560, KeyBank 17534, M&T 588, Old National 3832. Filter applied at run time into `outputs/v2-rc-6/inputs/run_input_2012Q1.csv` (rows only; the pinned file is read, never edited) |
| Sample | 2012Q1 to 2026Q3, 59 quarters per bank (about 55 to 58 usable after lags) |
| Dependent variables | `rate_nmd_eoq_pf` (segment `nmd`), `rate_time_eoq_pf` (segment `time`) |
| Environment | Python 3.13; numpy 2.1.3, pandas 2.2.3, scipy 1.14.1, statsmodels 0.14.4, matplotlib 3.9.2 (see 11, item D9) |
| Tests | `python -m pytest ffiec/tests`: 29 passed. Origin tests (`data_build projection ecm_tests MAE_Backtesting`): 66 passed on the same stack |

Commands (from the repo root; each stage script is in `ffiec/model_dev/`):

```bash
python ffiec/model_dev/stage1_eda_unitroot.py
python ffiec/model_dev/stage1b_gregory_hansen.py
python ffiec/model_dev/stage2_pipeline.py --tag base
python ffiec/model_dev/stage2_pipeline.py --tag covid --covid
python ffiec/model_dev/stage2_pipeline.py --tag start2012Q2 --start 2012Q2
python ffiec/model_dev/stage3_champions.py
python -I ffiec/cumulative_beta.py --segment-betas ffiec/model_dev/outputs/v2-rc-6/segment_betas.csv --out ffiec/model_dev/outputs/v2-rc-6/cumulative_beta.csv
```

`stage2_pipeline.py` runs the origin scripts unchanged as subprocesses with explicit arguments and with
`DEPOSIT_OUTPUT_VINTAGE` set to the segment's output folder, so every default write of the origin code lands
under `outputs/v2-rc-6/<tag>/<segment>/`. Backtest caches (`cache/`) are regenerable and not committed.

| Output folder | Content |
| :-- | :-- |
| `stage1/` | EDA charts, ACF/PACF (`acf_pacf.csv`, `figures/`), `unit_root_grid.csv`, `unit_root_summary.csv`, `i2_check.csv`, `zivot_andrews.csv`, `gregory_hansen*.csv` |
| `base/<seg>/` | `Co-integration_results.csv`, `co-integration_respecification_results.csv`, model/param selection, `ECM estimation results (det pruned).csv`, asymmetric results and tests, `deterministic_pruning_log.csv`, `MAE_Backtesting/output/out_of_sample/`, `Beta_Backtesting/output/out_of_sample/`, `pipeline.log` |
| `covid/<seg>/`, `start2012Q2/<seg>/` | The same pipeline with the COVID dummy offered (D6), and from 2012Q2 |
| `stage3/` | `champions.csv`, `champion_estimates.csv`, `residual_diagnostics.csv`, `treatment_tests.csv`, `covid_decision.csv`, `start2012Q2_comparison.csv`, `segment_betas*.csv`, `cumulative_beta_theta_*.csv` |
| root | `segment_betas.csv`, `cumulative_beta.csv` |

---

## 1. Summary

| Segment | Bank | Out-of-sample champion | λ | θ (long-run beta) | Mean h-step MAE (SE) | Skill | MAE rating, peer limits (provisional) | θ stability | Flags |
| :-- | :-- | :-- | :-: | :-: | :-: | :-: | :-: | :-: | :-- |
| nmd | First Horizon | EG long run, `n`, BIC (ADF lag 1, ECM lag 0), **asymmetric** (λ split) | λ⁺ −0.137, λ⁻ −0.581 | 0.606 | 0.211 (0.023) | Green | Green | Green | Residual autocorrelation (LB p 0.0002) |
| nmd | Huntington | ARDL(2,1), case 1, BIC | −0.165 | 0.533 | 0.211 (0.033) | Green | Green | **Red** | Champion changes when the sample starts 2012Q2 (θ unchanged) |
| nmd | KeyBank | Johansen VECM, det_order 1, AIC, k=1; trend and constant pruned | −0.282 | 0.463 | 0.258 (0.055) | Green | Green | **Red** | Pruned form (det_order −1) differs from the qualifying case |
| nmd | M&T | ARDL(1,1), case 2, BIC; constant pruned | −0.308 | 0.483 | 0.256 (0.053) | Green | Green | Amber | Pruned form (case 1) differs from the qualifying case |
| nmd | Old National | EG long run, `n`, BIC (ADF lag 1, ECM lag 1) | −0.125 | 0.472 | 0.351 (0.159) | Amber | **Red** | **Red** | No Johansen pass; residual autocorrelation (LB p8 0.012) |
| time | First Horizon | EG long run, `c`, AIC (ADF lag 1, ECM lag 4) | −0.335 | 0.733 | 0.336 (0.029) | Green | Green | **Red** | |
| time | Huntington | EG short run, `ct`, BIC (ADF lag 0, ECM lag 0) | −0.543 | 0.829 | 0.293 (0.064) | Green | Green | **Red** | P15 dummy significant; merger impulse significant; long-run trend −0.012 pp/quarter |
| time | KeyBank | Johansen VECM, det_order 0, fixed k=1 | −0.220 | 0.658 | 0.376 (0.082) | Green | Green | Green | Residual autocorrelation (LB p4 0.006) |
| time | M&T | ARDL(3,1), case 4, BIC, **asymmetric** (λ and θ split) | λ⁺ −0.153, λ⁻ −0.972 | **θ⁺ 0.811, θ⁻ 0.371** (no single θ) | 0.501 (0.064) | Amber | **Red** | **Red** | θ split; P13 dummy significant; long-run trend −0.050 pp/quarter; only 2 qualifying specifications |
| time | Old National | ARDL(3,4), case 1, AIC | −0.091 | 0.943 | 0.403 (0.073) | Green | **Red** | Green | θ near 1 with slow adjustment; champion changes from 2012Q2 (θ 0.84) |

All ten series and FFT are I(1); none is I(2). Every bank and segment has specifications that pass the cointegration
screen. The COVID dummy is excluded for all ten models. Cumulative total-deposit betas are 0.356 to 0.450 against
High-Level betas of 0.402 to 0.477 (section 10).

---

## 2. Exploratory Review

Charts: `stage1/figures/nmd_rates_vs_FFT.png`, `time_rates_vs_FFT.png`; ACF/PACF per series and FFT, levels and first
differences: `stage1/figures/acf_pacf_*.png`, values in `stage1/acf_pacf.csv` (lags 1 to 12, 95% band ±1.96/√n).
Both segment rates follow FFT through the zero lower bound (2012 to 2015, 2020 to 2021), the 2016 to 2019 cycle
and the 2022 to 2023 hikes. Level ACFs decay slowly for every series (persistent, consistent with a unit root);
first-difference ACFs are small beyond the first few lags. Visible single-quarter anomalies: M&T time 2022Q2 to Q3
(0.087%, 0.085%; P13) and Huntington time 2026Q2 (3.10%; P15).

---

## 3. Unit Roots (steps 2a, 2b)

Origin grid (`diagnostics/stationarity_and_breaks.py`, imported): ADF `c`/`n` x AIC/BIC/t-stat (max lag 4); KPSS
`c`/`ct` x auto/short/long. Default ADF `c`/AIC with KPSS `c`/auto; classified only when both agree. KPSS p-values
are bounded to [0.01, 0.10] (0.010 means ≤ 0.01; 0.100 means ≥ 0.10). Robustness = share of the six
re-specifications agreeing with the default verdict (levels: non-stationary; differences: stationary).

| Segment | Bank | Levels ADF p | Levels KPSS p | Δ ADF p | Δ KPSS p | Robustness: levels ADF / KPSS | Robustness: Δ ADF / KPSS | Class |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| nmd | First Horizon | 0.227 | 0.010 | 0.0091 | 0.100 | 6/6 / 1/6 | 6/6 / 6/6 | I(1) |
| nmd | Huntington | 0.524 | 0.010 | 0.0103 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| nmd | KeyBank | 0.410 | 0.010 | 0.0060 | 0.100 | 6/6 / 2/6 | 5/6 / 6/6 | I(1) |
| nmd | M&T | 0.596 | 0.010 | 0.0149 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| nmd | Old National | 0.369 | 0.010 | 0.0029 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| time | First Horizon | 0.623 | 0.016 | 0.0010 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| time | Huntington | 0.264 | 0.012 | 0.0009 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| time | KeyBank | 0.169 | 0.021 | 0.0179 | 0.100 | 6/6 / 1/6 | 6/6 / 6/6 | I(1) |
| time | M&T | 0.381 | 0.018 | 0.0006 | 0.100 | 6/6 / 2/6 | 6/6 / 6/6 | I(1) |
| time | Old National | 0.324 | 0.013 | 0.0225 | 0.100 | 6/6 / 2/6 | 5/6 / 6/6 | I(1) |
| FFT | | 0.330 | 0.010 | 0.0323 | 0.100 | 6/6 / 1/6 | 6/6 / 6/6 | I(1) |

The low levels-KPSS robustness (1 or 2 of 6) comes from the `ct` KPSS specifications, which do not reject trend
stationarity; the ADF grid is unanimous on levels. This is the same pattern as the origin (e.g. First Horizon 2/6).

**I(2) check** (`stage1/i2_check.csv`; same grid on second differences): every series is stationary in second
differences under the default (ADF p ≤ 0.012, KPSS p ≥ 0.10; ADF 6/6 and KPSS 5/6 or 6/6). **No series is I(2).**

---

## 4. Structural Breaks

### 4.1 Zivot-Andrews on levels (step 3; `c`/`t`/`ct`, AIC lags, max 4)

| Segment | Bank | `c` | `t` | `ct` |
| :-- | :-- | :-- | :-- | :-- |
| nmd | First Horizon | −6.47 (p 0.000, 2022Q3) | −5.06 (p 0.009, 2021Q4) | −5.50 (p 0.014, 2022Q3) |
| nmd | Huntington | −6.28 (p 0.001, 2022Q2) | −4.65 (p 0.025, 2021Q4) | −5.01 (p 0.061, 2022Q3) |
| nmd | KeyBank | −6.19 (p 0.001, 2022Q3) | −4.10 (p 0.110, 2021Q3) | −5.15 (p 0.041, 2022Q3) |
| nmd | M&T | −5.27 (p 0.010, 2022Q3) | −3.47 (p 0.371, 2021Q2) | −4.40 (p 0.261, 2022Q3) |
| nmd | Old National | −7.25 (p 0.000, 2022Q3) | −5.38 (p 0.005, 2021Q4) | −5.73 (p 0.006, 2022Q3) |
| time | First Horizon | −5.39 (p 0.006, 2022Q4) | −3.11 (p 0.586, 2021Q4) | −4.49 (p 0.216, 2022Q4) |
| time | Huntington | −5.97 (p 0.001, 2022Q3) | −3.90 (p 0.167, 2021Q4) | −4.66 (p 0.150, 2022Q4) |
| time | KeyBank | −7.35 (p 0.000, 2022Q2) | −5.66 (p 0.004, 2021Q4) | −5.70 (p 0.007, 2020Q1) |
| time | M&T | −9.09 (p 0.000, 2022Q3) | −4.16 (p 0.094, 2021Q4) | −7.11 (p 0.001, 2022Q3) |
| time | Old National | −6.79 (p 0.000, 2022Q3) | −4.32 (p 0.065, 2021Q3) | −5.68 (p 0.007, 2022Q3) |
| FFT | | −5.30 (p 0.009, 2022Q1) | −3.56 (p 0.320, 2020Q3) | −4.91 (p 0.080, 2022Q2) |

As in the origin, every series rejects a unit root once a 2022 level break is allowed (`c`), and FFT shows the same
break (2022Q1). M&T time's very large `c` statistic (−9.09) reflects the P13 dip as well as the 2022 level shift.

### 4.2 Gregory-Hansen (step 4; `model_form/gregory_hansen.py` unchanged)

Finite-sample critical values simulated at **T = 59** (2,000 replications, origin seed), which govern. ADF\* 5%:
C −5.09, C/T −5.53, C/S −5.29, C/S/T −5.87 (origin at T = 62: C −5.14, C/T −5.50, C/S −5.46, C/S/T −5.82).

| Segment | Bank | ADF\* C | C/T | C/S | C/S/T | Breaks (C) | 5% rejections (simulated CV) |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: | :-- |
| nmd | First Horizon | −4.45 | −4.76 | −4.67 | −4.90 | 2024Q2 | none |
| nmd | Huntington | −4.52 | −4.68 | −4.52 | −4.62 | 2023Q3 | none |
| nmd | KeyBank | −4.94 | −5.31 | −5.15 | −5.40 | 2024Q1 | none |
| nmd | M&T | −4.57 | **−5.68** | −5.16 | −5.59 | 2024Q2 | C/T ADF\* (−5.68 vs −5.53, 2024Q3) |
| nmd | Old National | −5.07 | −5.39 | **−5.89** | **−5.97** | 2023Q3 | C/S ADF\*, C/S/T ADF\*; Zt\* and Za\* in C, C/T, C/S, C/S/T; all break 2023Q3 |
| time | First Horizon | −4.97 | **−5.59** | −5.07 | −5.57 | 2024Q1 | C/T ADF\* (−5.59 vs −5.53, 2024Q1) |
| time | Huntington | −4.04 | −4.23 | −4.07 | −4.24 | 2024Q3 | none |
| time | KeyBank | −4.10 | −4.22 | −4.37 | −4.23 | 2023Q4 | none |
| time | M&T | −4.17 | −4.59 | −4.88 | −4.84 | 2023Q4 | none |
| time | Old National | −3.91 | −4.22 | −3.91 | −4.19 | 2024Q3 | none |

Allowing one break overturns no result of the screen. Where GH rejects (M&T nmd, Old National nmd, First Horizon
time), the standard tests in section 5 also pass; the breaks are not interpreted (origin 5.3). Old National nmd is
the one series where the break form is clearly stronger than the no-break tests (Johansen 0/15, below); recorded as
open item O-4.

---

## 5. Cointegration (step 5)

Baseline (`Co-integration Tests.py`: trend `c`, max lag 4, EG/ARDL by AIC, Johansen det_order 0, k = 1, ARDL case 3)
and re-specification grid (`FlaggedRates_co-integration_respecification.py`, five banks). Grid pass counts are
specifications with p < 0.05 (Johansen: trace r ≤ 0 "<0.05" or "<0.01") over the grid (EG 3 trends x 4 lag rules;
Johansen 3 det_orders x 5 lag rules; ARDL 5 cases x 3 ICs).

| Segment | Bank | Baseline EG LR p | EG SR p | Johansen r≤0 | ARDL case 3 p | Grid: EG LR | EG SR | Johansen | ARDL | Specifications estimated (ARDL/EG/Johansen) |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-- |
| nmd | First Horizon | 0.075 | 0.480 | <0.01 | ARDL(4,1) 1.0e-05 | 4/12 | 3/12 | 15/15 | 15/15 | 37 (15/7/15) |
| nmd | Huntington | 0.259 | 0.961 | <0.10 | ARDL(3,4) 0.136 | 0/12 | 0/12 | 5/15 | 8/15 | 13 (8/0/5) |
| nmd | KeyBank | 0.051 | 0.149 | <0.10 | ARDL(2,1) 0.003 | 3/12 | 3/12 | 10/15 | 15/15 | 31 (15/6/10) |
| nmd | M&T | 0.139 | 0.831 | <0.05 | ARDL(2,1) 0.0008 | 3/12 | 1/12 | 15/15 | 15/15 | 34 (15/4/15) |
| nmd | Old National | 0.059 | 0.902 | <0.10 | ARDL(4,2) 0.009 | 3/12 | 0/12 | **0/15** | 8/15 | 11 (8/3/0) |
| time | First Horizon | 0.017 | 0.706 | <0.01 | ARDL(3,4) 0.209 | 6/12 | 0/12 | 7/15 | **0/15** | 10 (0/6/4) |
| time | Huntington | 0.215 | 0.448 | <0.01 | ARDL(2,3) 0.024 | 0/12 | 1/12 | 14/15 | 10/15 | 25 (10/1/14) |
| time | KeyBank | 0.027 | 0.333 | <0.01 | ARDL(3,2) 0.069 | 2/12 | 0/12 | 10/15 | 8/15 | 20 (8/2/10) |
| time | M&T | 0.055 | 0.461 | <0.10 | ARDL(4,2) 0.218 | **0/12** | **0/12** | **0/15** | 2/15 | **2 (2/0/0)** |
| time | Old National | 0.164 | 0.608 | <0.10 | ARDL(3,4) 0.040 | 0/12 | 0/12 | **0/15** | 8/15 | 6 (6/0/0) |

Every model has at least one qualifying specification, so no bank and segment fails cointegration. Thin support:
M&T time passes only ARDL(3,1) cases 4 and 5 by BIC (identical fits; open item O-1); Old National time and nmd have
no Johansen pass; Huntington nmd has no EG pass. Coefficient t- and p-values on levels regressors are descriptive only.

---

## 6. Specifications, Selection and Pruning (step 6)

`ECM workflow.py` unchanged: model screen (p < 0.05), parameter screen (short-run p < 0.05), one-step OLS ECM with
deterministic terms from the qualifying case, short-run pruning, then deterministic pruning (`deterministic_pruning.py`:
trend then constant at p ≥ 0.05, refit, model always kept, no cointegration re-check), then one fully split
asymmetric variant per screened specification (NLS with regime iteration, pair pruning, Wald collapse).

| Segment | Bank | Symmetric models | In-sample MAE range | θ range | Asymmetric variants: λ split kept / θ split kept | Models with a deterministic term pruned (sym / asym) |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: |
| nmd | First Horizon | 37 | 0.069 to 0.115 | 0.547 to 0.623 | 37: 15 / 6 | 19 / 2 |
| nmd | Huntington | 13 | 0.040 to 0.058 | 0.524 to 0.533 | 13: 2 / 2 | 6 / 4 |
| nmd | KeyBank | 31 | 0.045 to 0.057 | 0.451 to 0.463 | 31: 26 / 26 | 17 / 6 |
| nmd | M&T | 34 | 0.054 to 0.061 | 0.463 to 0.483 | 34: 22 / 11 | 22 / 5 |
| nmd | Old National | 11 | 0.045 to 0.049 | 0.447 to 0.472 | 11: 4 / 5 | 5 / 0 |
| time | First Horizon | 10 | 0.092 to 0.111 | 0.702 to 0.937 | 13: 7 / 5 | 0 / 0 |
| time | Huntington | 25 | 0.096 to 0.187 | 0.745 to 0.975 | 25: 8 / 12 | 0 / 0 |
| time | KeyBank | 20 | 0.067 to 0.082 | 0.658 to 0.853 | 20: 17 / 14 | 5 / 1 |
| time | M&T | 2 | 0.118 | 0.808 | 2: 2 / 2 | 0 / 0 |
| time | Old National | 6 | 0.079 to 0.081 | 0.761 to 0.943 | 8: 6 / 6 | 0 / 4 |

Pruning flags (`form_differs_from_qualifying_test`, logged in `base/<seg>/deterministic_pruning_log.csv`): 86 nmd
and 10 time models. For the champions: KeyBank nmd (qualifying det_order 1; trend p 0.439 and constant p 0.592
dropped; remaining det_order −1) and M&T nmd (qualifying case 2; constant p 0.552 dropped; remaining case 1). Neither
was re-checked against the screen and nothing was dropped because of such a re-check (rule 9.4).

---

## 7. Champions (out-of-sample default) and Coefficients

Champion rule as the origin (`MAE_Backtesting/backtest.py`, `DEFAULT_SELECT = out-of-sample`): admissible λ (λ±) in
(−1, 0) and θ (θ±) in [0, 1]; ranked by mean many-start-date h-step MAE (h = 1 to 8, start dates 2016Q1 to 2026Q2,
expanding window); fewest parameters within one Newey-West SE of the best; tie-break asymmetric > EG > ARDL >
Johansen. Full scores: `base/<seg>/MAE_Backtesting/output/out_of_sample/selection_oos_scores_8Q.csv`.

| Segment | Bank | Candidates (admissible) | Terms: coefficient (t) | θ (t) |
| :-- | :-- | :-: | :-- | :-: |
| nmd | First Horizon | 74 (67) | ect⁺ −0.137 (−1.26); ect⁻ −0.581 (−6.49); ΔFFT⁺ 0.074 (1.19); ΔFFT⁻ 0.480 (7.10) | 0.606 (38.8) |
| nmd | Huntington | 26 (24) | y.L1 −0.165 (−3.09); FFT.L1 0.088 (3.31); Δy.L1 0.240 (2.87); ΔFFT.L0 0.237 (8.56) | 0.533 (19.7) |
| nmd | KeyBank | 62 (36) | y.L1 −0.282 (−4.13); FFT.L1 0.130 (4.40); ΔFFT.L1 0.152 (3.19) | 0.463 (26.5) |
| nmd | M&T | 68 (57) | y.L1 −0.308 (−6.16); FFT.L1 0.149 (6.76); ΔFFT.L0 0.186 (5.52) | 0.483 (29.6) |
| nmd | Old National | 22 (20) | y.L1 −0.125 (−2.85); FFT.L1 0.059 (3.04); Δy.L1 0.393 (4.45); ΔFFT.L0 0.161 (5.57) | 0.472 (12.8) |
| time | First Horizon | 23 (20) | const 0.181 (4.48); y.L1 −0.335 (−7.16); FFT.L1 0.246 (7.24); Δy.L2 −0.369 (−3.46); ΔFFT.L3 0.597 (5.78); LR const 0.541 | 0.733 (20.9) |
| time | Huntington | 50 (48) | const 0.471 (8.43); trend −0.0065 (−3.41); y.L1 −0.543 (−13.2); FFT.L1 0.450 (13.4); LR const 0.867, LR trend −0.0121 | 0.829 (25.1) |
| time | KeyBank | 40 (40) | const 0.164 (3.56); y.L1 −0.220 (−4.43); FFT.L1 0.145 (4.31); Δy.L1 0.345 (4.47); ΔFFT.L1 0.307 (4.32); LR const 0.748 | 0.658 (16.4) |
| time | M&T | 4 (4) | ect⁺ −0.153 (−1.85); ect⁻ −0.972 (−10.8); Δy⁺.L1 0.194 (2.76); Δy⁻.L1 0.522 (2.90); ΔFFT⁺.L0 −0.378 (−3.29); ΔFFT⁻.L0 0.106 (1.37); LR const 1.292, LR trend −0.0502 | θ⁺ 0.811 (23.3), θ⁻ 0.371 (8.0) |
| time | Old National | 14 (14) | y.L1 −0.091 (−2.68); FFT.L1 0.086 (2.86); ΔFFT.L1 0.395 (7.46); ΔFFT.L3 0.182 (3.54) | 0.943 (12.1) |

Coefficients and p-values: `stage3/champion_estimates.csv`.

**Plausibility.** Non-maturity θ 0.46 to 0.61, against static OLS slopes of 0.42 to 0.52 (data description 6) and
origin total-deposit betas of 0.40 to 0.48: higher, as expected for an interest-bearing, end-of-quarter base. Time θ
0.66 to 0.94 (static slopes 0.60 to 0.67). Old National time (0.943, λ −0.091, about 7.6 quarters half-life) and
Huntington time (0.829 with a negative long-run trend) are at the high end (open items O-3, O-2). M&T time is not a
single-beta model (O-1).

---

## 8. Backtests (step 7)

Many-start-date backtest (governing): h-step MAE over 34 (8Q) to 41 (1Q) start dates from 2016Q1, dynamic forecast,
realized FFT. **Ratings.** The origin's approved fixed reference (`MAE_Backtesting/reference/reference_v1`) was not
used. Absolute ratings below use limits derived from this run's five banks per segment (`--limits peer`); they are
provisional, because the Prod-Lvl model has no approved reference (open item O-7). The skill test (ratio to the
no-change forecast) needs no reference and is the governing rating here. Peer limits (green/red): nmd 1–2Q 0.15/0.20,
3–4Q 0.25/0.30, 5–8Q 0.40/0.45; time 1–2Q 0.25/0.30, 3–4Q 0.40/0.45, 5–8Q 0.60/0.70.

| Segment | Bank | h-step MAE 1Q … 8Q | No-change MAE 1Q … 8Q | Worst skill ratio | Skill | Absolute (peer, provisional) | Single-window 8Q mean / no-change, beats | Single-window rating |
| :-- | :-- | :-- | :-- | :-: | :-: | :-: | :-: | :-: |
| nmd | First Horizon | 0.098 0.160 0.185 0.209 0.229 0.254 0.269 0.284 | 0.189 … 1.183 | 0.52 (1Q) | Green | Green | 0.158 / 0.374, 8/8 | Amber |
| nmd | Huntington | 0.060 0.125 0.158 0.191 0.243 0.282 0.316 0.310 | 0.140 … 0.918 | 0.47 (2Q) | Green | Green | 0.204 / 0.212, 4/8 | Red |
| nmd | KeyBank | 0.079 0.126 0.174 0.230 0.294 0.346 0.384 0.427 | 0.126 … 0.873 | 0.62 (1Q) | Green | Green | 0.110 / 0.252, 6/8 | Green |
| nmd | M&T | 0.082 0.142 0.191 0.244 0.288 0.335 0.363 0.402 | 0.133 … 0.887 | 0.61 (1Q) | Green | Green | 0.125 / 0.269, 7/8 | Green |
| nmd | Old National | 0.080 0.159 0.232 0.285 0.374 0.484 0.555 0.639 | 0.118 … 0.795 | 0.80 (8Q) | Amber | Red (3–4Q avg 0.259; 5–8Q max 0.639) | 0.170 / 0.239, 5/8 | Amber |
| time | First Horizon | 0.180 0.270 0.274 0.310 0.378 0.410 0.419 0.450 | 0.248 … 1.637 | 0.72 (1Q) | Green | Green | 0.262 / 0.379, 5/8 | Red |
| time | Huntington | 0.143 0.192 0.250 0.299 0.334 0.359 0.370 0.397 | 0.271 … 1.584 | 0.53 (1Q) | Green | Green | 0.265 / 0.548, 8/8 | Red |
| time | KeyBank | 0.114 0.242 0.352 0.418 0.454 0.465 0.478 0.490 | 0.240 … 1.653 | 0.51 (2Q) | Green | Green | 0.133 / 0.459, 6/8 | Green |
| time | M&T | 0.158 0.370 0.519 0.593 0.575 0.538 0.587 0.667 | 0.221 … 1.491 | 0.84 (2Q) | Amber | Red (1–2Q max 0.370; 3–4Q max 0.593) | 0.247 / 0.371, 6/8 | Amber |
| time | Old National | 0.122 0.186 0.258 0.336 0.440 0.537 0.631 0.712 | 0.223 … 1.502 | 0.54 (1Q) | Green | Red (5–8Q max 0.712) | 0.203 / 0.376, 6/8 | Amber |

The single-window Green/Amber/Red thresholds (0.15/0.25/0.50 pp) are the origin's fixed absolute values, calibrated
on total-deposit rates; for the time segment, whose rates move more, they are strict (Huntington time beats
no-change on 8/8 horizons yet rates Red on its mean 0.265).

**Long-run beta stability** (`Beta_Backtesting`, rated from 2020Q1; fail = > 2 SE and > 20% from the full-sample θ):

| Segment | Bank | θ range 2020Q1–2026Q1 | Failing start dates | Max deviation | Rating |
| :-- | :-- | :-: | :-: | :-- | :-: |
| nmd | First Horizon | 0.534–0.651 | 0 | 12% (2022Q4) | Green |
| nmd | Huntington | 0.199–0.547 | 4 (2022Q2–Q4, 2024Q4) | 63% (2020Q2) | Red |
| nmd | KeyBank | 0.271–0.551 | 12 (2020Q2–2023Q1) | 42%, 3.9 SE | Red |
| nmd | M&T | 0.384–0.729 | 1 (2022Q3) | 51% (2023Q4) | Amber |
| nmd | Old National | 0.089–6.070 | 15 | 1,186% (2023Q4; λ near 0 at that start) | Red |
| time | First Horizon | 0.500–0.762 | 4 (2020Q2–2021Q1) | 32%, 3.0 SE | Red |
| time | Huntington | 0.660–0.856 | 1 (2021Q2) | 20%, 3.2 SE | Red |
| time | KeyBank | 0.503–0.678 | 0 | 24% (2023Q3) | Green |
| time | M&T | θ⁺/θ⁻ 0.353–1.135 | 19 (θ⁺), 15 (θ⁻) | 56%, 9.8 SE | Red |
| time | Old National | 0.786–1.235 | 0 | 31% (2023Q2) | Green |

Most failures fall in 2020 to 2022 start dates, where the expanding window ends at or just after the zero lower bound
and the hiking cycle is not yet in the sample (O-6).

**Realized beta (descriptive)**, mean actual / model-implied, 1Q … 8Q (`realized_beta_summary_8Q.csv`):
nmd First Horizon 0.74…0.51 / 0.45…0.37; Huntington 0.47…0.36 / 0.39…0.27; KeyBank 0.48…0.34 / 0.24…0.19; M&T
0.47…0.35 / 0.26…0.25; Old National 0.45…0.28 / 0.26…−0.11. Time First Horizon 0.79…0.67 / 0.49…0.61; Huntington
0.54…0.64 / 0.48…0.52; KeyBank 0.54…0.67 / 0.59…0.62; M&T 0.63…0.59 / 0.44…0.43; Old National 0.64…0.56 / 0.52…0.25.
As in the origin, dynamic forecasts under-state realized short-horizon pass-through for most models.

### 8.1 Residual diagnostics (champions, in-sample one-step residuals; `stage3/residual_diagnostics.csv`)

| Segment | Bank | n | ACF 1 | ACF 4 | Ljung-Box p (4) | Ljung-Box p (8) | Largest residual |
| :-- | :-- | :-: | :-: | :-: | :-: | :-: | :-- |
| nmd | First Horizon | 58 | −0.00 | 0.30 | **0.0002** | **0.0003** | 0.46 (2023Q3) |
| nmd | Huntington | 57 | 0.06 | 0.19 | 0.245 | 0.286 | 0.28 (2026Q2) |
| nmd | KeyBank | 57 | 0.20 | 0.20 | 0.283 | 0.279 | 0.29 (2023Q3) |
| nmd | M&T | 58 | 0.29 | 0.07 | 0.133 | 0.265 | 0.27 (2023Q4) |
| nmd | Old National | 57 | 0.10 | 0.23 | **0.033** | **0.012** | 0.25 (2023Q3) |
| time | First Horizon | 55 | 0.14 | 0.05 | 0.761 | 0.562 | 0.40 (2026Q3) |
| time | Huntington | 58 | −0.07 | −0.05 | 0.489 | 0.710 | 0.50 (2026Q2, P15) |
| time | KeyBank | 57 | 0.23 | −0.18 | **0.006** | 0.056 | 0.33 (2020Q3) |
| time | M&T | 57 | 0.01 | 0.12 | 0.444 | 0.764 | 0.30 (2025Q1) |
| time | Old National | 55 | −0.06 | 0.06 | 0.371 | 0.376 | 0.35 (2023Q1) |

95% ACF band ±0.26. Ljung-Box without a degrees-of-freedom correction for the fitted terms. Serial correlation at
5%: First Horizon nmd (lag-4 seasonality-like ACF 0.30 with no short-run Δy lag in the champion), Old National nmd,
KeyBank time (O-5). The linear-form champions refit by OLS reproduce the stored coefficients exactly (max difference 0).

---

## 9. Treatment Tests (step 8; flags only, data never edited, no champion changed)

Dummies are added to each champion's own regressors and refit by OLS. For the λ-split champions (First Horizon nmd,
M&T time) the error-correction terms are held at the champion's long-run coefficients, so those tests are conditional
on them. Additive-outlier form for P13/P15: ΔD_t and D_{t−1} with D = 1 over the flagged quarters (joint F).

| Test | Segment / Bank | Result | Effect on λ / θ | Outcome |
| :-- | :-- | :-- | :-- | :-- |
| P13 M&T 2022Q2–Q3 | time / M&T | F 4.57, p 0.015; D_{t−1} −0.628 (p 0.006), ΔD −0.173 (p 0.187) | conditional (θ± held) | **Significant.** Flag; owner decision (O-1) |
| P15 Huntington 2026Q2 | time / Huntington | F 10.63, p 0.0001; ΔD −0.556 (p 0.000), D_{t−1} −0.259 (p 0.215) | λ −0.543 → −0.503; θ 0.829 → 0.837 | **Significant.** θ barely moves. Flag (O-2) |
| Merger quarters (impulse on `merger_quarter = 1`) | all ten | Significant only for Huntington time: +0.194 (p 0.007), 6 quarters incl. 2026Q1 (Cadence, 24%). Others p 0.17 to 0.88 | Huntington time θ 0.829 → 0.833 | Origin treatment kept (pro forma, no dummy); Huntington time flagged (O-2) |
| Start at 2012Q2, champion refit | all ten | θ changes ≤ 0.010 (Huntington time 0.829 → 0.825); λ ≤ 0.005 | | No effect of the 2012Q1 fallback rows on the champions |
| Start at 2012Q2, full rerun (`start2012Q2/`) | all ten | Same champion for 8 of 10. Huntington nmd → ARDL(4,1) case 1 AIC (θ 0.533 → 0.532). **Old National time → ARDL(2,1) case 2 BIC asymmetric (θ 0.943 → 0.844)** | | Flag Old National time (O-3) |
| COVID dummy D6 (`covid/`, origin rule 5.5.8) | all ten | Pruned from every champion (rule 1 fails); champions, out-of-sample MAE and θ identical with and without it | none | **Excluded for all ten** (`stage3/covid_decision.csv`) |

Note on the fallback rows: the four 2012Q1 fallback rows carry a synthetic 2011Q4 balance used in the two-point
averages; the end-of-quarter model rates divide by the 2012Q1 quarter-end balance. The sensitivity confirms no
material effect.

---

## 10. Cumulative Beta vs High-Level (data description 7.4; D10/O8 open)

`segment_betas.csv` = each champion's long-run θ, except M&T time (θ split): default is the θ of its symmetric
parent, ARDL(3,1) case 4 BIC (0.808), with θ⁺ (0.811) and θ⁻ (0.371) as sensitivities
(`stage3/segment_betas_theta_pos.csv`, `_theta_neg.csv`, `stage3/cumulative_beta_theta_*.csv`). Weights: two-point
balances averaged 2012Q1–2026Q3 (tool default). Both bases reported; neither chosen.

| Bank | β nmd | β time | Share nmd / time of total deposits | Cumulative, interest-bearing basis | Cumulative, total-deposit basis | High-Level β | Gap HL − total basis |
| :-- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| First Horizon | 0.606 | 0.733 | 0.604 / 0.114 | 0.626 | 0.450 | 0.477 | +0.027 |
| Huntington | 0.533 | 0.829 | 0.636 / 0.130 | 0.583 | 0.446 | 0.463 | +0.017 |
| KeyBank | 0.463 | 0.658 | 0.643 / 0.089 | 0.487 | 0.356 | 0.402 | +0.046 |
| M&T | 0.483 | 0.808 | 0.573 / 0.110 | 0.536 | 0.366 | 0.402 | +0.036 |
| Old National | 0.472 | 0.943 | 0.603 / 0.150 | 0.566 | 0.426 | 0.419 | −0.007 |

M&T with θ⁺: identical to two decimals (0.536 / 0.366); with θ⁻: 0.465 / 0.318, gap +0.084. The total-deposit basis
is 0.017 to 0.046 below High-Level for four banks and 0.007 above it for Old National. Caveats as in 7.4: the
weights are two-point balances while the segment rates use end-of-quarter balances, and the total basis sets
noninterest-bearing and foreign-office deposits at beta 0.

---

## 11. Departures from the Origin Method

To be logged in the main doc, section 0.2 (rule 9.5). This session did not edit the main doc (task instruction);
see O-8.

| # | Departure | Reason |
| :-: | :-- | :-- |
| D1 | Dependent variables `rate_nmd_eoq_pf`, `rate_time_eoq_pf` (FFIEC, interest-bearing, end-of-quarter) instead of `rate_pf_clean`; two models per bank | Owner decisions D7, D8, D9 |
| D2 | Sample 2012Q1–2026Q3 (59 quarters) instead of 2011Q1–2026Q2 (62); no 2008-start sample (the FFIEC data start in 2012) | Data description 1, 5; D5 |
| D3 | Five banks; filter applied at run time into a filtered run-input copy in the vintage folder | D3; rule 9.1/9.2 |
| D4 | Origin scripts run unchanged with explicit arguments and `DEPOSIT_OUTPUT_VINTAGE` pointing into `ffiec/model_dev/outputs/v2-rc-6/`; Prod-Lvl wrappers in `ffiec/model_dev/stage*.py` | Isolation rules |
| D5 | Gregory-Hansen critical values simulated at T = 59 (origin T = 62); same replications and seed | Sample length |
| D6 | MAE absolute ratings use limits derived from this run's five banks per segment, not the origin's approved reference v1; reported as provisional, skill test governing | Task instruction; no approved Prod-Lvl reference (O-7) |
| D7 | Added: I(2) check (grid on second differences), ACF/PACF, residual ACF and Ljung-Box | Task instruction |
| D8 | Added treatment tests as flags: P13/P15 additive-outlier dummies, merger-quarter impulse, 2012Q2 start (champion refit and full rerun). Origin had no merger dummy (pro forma only), which is kept as the treatment | Task instruction; data description 6 |
| D9 | Package versions pinned for the run (numpy 2.1.3, pandas 2.2.3, scipy 1.14.1, statsmodels 0.14.4, matplotlib 3.9.2). statsmodels 0.15 breaks the origin ARDL bounds code (`BoundsTestResult.stat` removed); scipy 1.18 breaks statsmodels 0.14 | Origin versions unpinned (origin 10.1) |
| D10 | COVID retest run as the four workflow steps with `--covid` (`ECM workflow.py` has no switch for it) | Same scripts and rule as origin 5.5.8 |
| D11 | θ-split champion (new case; no origin champion had one): cumulative beta uses the symmetric parent θ by default, θ± as sensitivities | Needs owner decision (O-1) |
| D12 | Not run: in-sample selection option (8c), `model_form` challengers and 2022Q3 level-dummy test (8d), actual-vs-predicted and doc figures, projection and scenarios | Outside the requested scope |

---

## 12. Open Items (owner decision or review; defaults used)

| # | Item | Evidence | Default used |
| :-: | :-- | :-- | :-- |
| O-1 | **M&T time**: champion is asymmetric with θ split (θ⁺ 0.811, θ⁻ 0.371), λ⁻ −0.972 (near the admissibility bound), long-run trend −0.050 pp/quarter (about −2.9 pp over the sample, not a plausible equilibrium), only 2 qualifying specifications (ARDL(3,1) cases 4/5, BIC; EG and Johansen 0 passes), P13 dummy significant (p 0.015), MAE Red (peer, provisional), skill Amber, θ stability Red (19 failing start dates). The P13 dip (0.087%, 0.085%) may drive both the thin screen and the trend | Champion as selected; cumulative beta with parent θ 0.808. Decision needed: P13 treatment (dummy in screen and estimation, or exclusion) and a rescreen, and how to define one beta for a θ-split model |
| O-2 | **Huntington time**: P15 additive outlier significant (F 10.6, p 0.0001); merger impulse significant (p 0.007; 2026Q1 Cadence quarter adjacent to P15); long-run trend −0.012 pp/quarter; θ 0.829; single-window Red; θ stability Red (1 start date, 3.2 SE) | Champion and data unchanged; θ moves only to 0.837 with the P15 dummy |
| O-3 | **Old National time**: θ 0.943 with λ −0.091 (slow adjustment, wide θ SE 0.078); absolute MAE Red (peer); champion changes when the sample starts 2012Q2 (θ 0.844); no EG or Johansen pass | Champion as selected |
| O-4 | **Old National nmd**: no Johansen pass (0/15), baseline EG fails; GH rejects with a 2023Q3 regime shift (C/S, C/S/T ADF\*); skill Amber, absolute Red; θ stability Red (θ up to 6.07 at start dates where λ ≈ 0); residual autocorrelation (LB p8 0.012) | Champion as selected |
| O-5 | Residual serial correlation: First Horizon nmd (LB p 0.0002; ECM lag 0 champion), Old National nmd (p 0.033/0.012), KeyBank time (p 0.006 at lag 4) | No change; the selection rule is the origin's |
| O-6 | θ stability Red for 6 of 10 (nmd Huntington, KeyBank, Old National; time First Horizon, Huntington, M&T), mostly 2020–2022 start dates | Reported; rule unchanged |
| O-7 | No approved fixed MAE reference for Prod-Lvl; absolute MAE ratings are peer-derived and provisional; the single-window thresholds are origin total-deposit values | Skill test governs; a Prod-Lvl reference would need freezing and owner approval |
| O-8 | Departures in section 11 to be logged in the main doc 0.2 (rule 9.5) by the doc owner | Not written by this session |
| O-9 | Cumulative beta basis and weights (D10/O8) | Both bases reported; sample-average two-point weights |
| O-10 | Deterministic pruning changed two champions' forms (KeyBank nmd det_order 1 → none; M&T nmd case 2 → case 1); not re-screened per rule 9.4 | Flag only |
