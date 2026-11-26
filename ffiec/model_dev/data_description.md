# Prod-Lvl Deposit Beta: Model Development Data Description

> **STATUS: DRAFT, rev 0.13 (2026-11-26). For model development only. NOT VALIDATED.**
> This note describes the data the Prod-Lvl model development uses: one pinned dataset, the regressor and the
> rules that every development session (this one, and any forked or fresh sub-session) must follow. The data
> build, source change control and build checks are recorded in `Prod-Lvl Deposit Beta Analyses.md` (doc rev 0.13,
> sections 4 to 7). Where the two disagree, the main doc is the record and this note is corrected.

| Rev | Date | Change |
| :-- | :-- | :-- |
| 0.13 | 2026-11-26 | Post-estimation step added (7.4): cumulative balance-weighted beta vs the High-Level betas, procedure only (owner, main doc 6.11, `acfcf46`); D10 (O8) open. Data unchanged |
| 0.12 | 2026-11-26 | Scope is two segments per bank, ten models (owner decision D9, relayed by the build session, main doc rev 0.12 `e4806e5`); no aggregate model; `rate_ib_pf` and `rate_total_pf` reconciliation only; D1 closed. Data unchanged (`cddc1d1`) |
| 0.11 | 2026-11-26 | Rebased on `cddc1d1`: end-of-quarter non-maturity rate `rate_nmd_eoq_pf` (balance `nmd_eoq_pf`) is the non-maturity model variable (D8, owner decision relayed by the build session); impact of D7 and D8 recorded; final variable list |
| 0.10 | 2026-11-26 | Rebased on `485ebb6` (supersedes `b052e00`): the end-of-quarter time rate is a new column `rate_time_eoq_pf` (balance `time_eoq_pf`) and is the time-deposit model variable; `rate_time_pf` is two-point again, reference only. Hashes now taken on the checked-out files (CRLF), matching the build session |
| 0.9 | 2026-11-26 | Rebased on `b052e00`: `rate_time_pf` on the end-of-quarter balance (new column `time_bal_pf`); new pinned hash; First Horizon and KeyBank 2023 flags dropped; Huntington 2026Q2 added (P15) |
| 0.8 | 2026-11-26 | D7 decided: end-of-quarter time-deposit denominator (owner, 2026-11-26); rebuild requested from the build session; time-deposit model waits for the new vintage |
| 0.7 | 2026-11-26 | Time-deposit denominator question added (D7, open); First Horizon 2023Q2 to Q3 and KeyBank 2023Q1 to Q2 added as time-model outlier candidates; main doc reference to rev 0.9 (O7 recorded, `a6e889c`) |
| 0.6 | 2026-11-26 | Sample end 2026Q3 (owner decision, D5 closed): FFT rebuilt to 2026Q3 in `ffiec/model_dev/inputs/v2-rc-3/`; pinned regressor replaced; prerequisite 7.1 done |
| 0.5 | 2026-11-26 | Scope set to five banks (owner decision 2026-11-26, D3 closed): Glacier and SouthState excluded from estimation; five-bank sample figures added. Data and hashes unchanged |
| 0.4 | 2026-11-25 | Rebased on `2e0fa49`: year-to-date breaks in quarterly interest expense repaired (main doc 6.8); 20 bank-quarters in 2012 to 2016 change; M&T 2022Q2 to Q3 time rate added as an outlier candidate (P13) |
| 0.3 | 2026-11-25 | Rebased on `9fa7dfc`: 2012Q1 fallback applied to the total-deposit series (P12 resolved, D4 closed); only `rate_total_pf` and `dep_avg_pf` change, in the 5 fallback rows |
| 0.2 | 2026-11-25 | Rebased on the Schedule RC base build (`49bfdb8`): new denominator, 413 rows with no dropped quarters, product lines, new pinned hashes; hybrid-base findings moved to "superseded" |
| 0.1 | 2026-11-14 | First draft on the hybrid (RC-K) build `ff50a25` |

---

## 1. Scope

| Item | Detail |
| :-- | :-- |
| Model | Prod-Lvl Deposit Beta: ten one-step ECMs, five banks x two segments (owner decision D9): interest-bearing non-maturity rate (`rate_nmd_eoq_pf`) and time-deposit rate (`rate_time_eoq_pf`), each on the federal funds rate (form, selection and backtests as the origin model). No aggregate or total-deposit model |
| Banks | **Five, estimated** (owner decision 2026-11-26, D3): First Horizon (cert 4977), Huntington (6560), KeyBank (17534), M&T (588), Old National (3832). The data file also holds Glacier (30788) and SouthState (33555); they are not estimated |
| Source | FFIEC Call Reports (CDR Public Web Service), pro forma for mergers |
| Regressor | `FFT`, quarterly average of monthly FRED `FEDFUNDS` |
| Frequency | Quarterly, quarter-end dates |
| Data commit | `callreport-source-switch` at `cddc1d1` (local; not pushed to `ffiec`). Model development branch `model-dev/prod-lvl` starts at the same commit |

---

## 2. Pinned Inputs

Every development run reads these files at these hashes (SHA-256 of the checked-out file; the repo checks out
with `core.autocrlf=true`, so the hash differs from the git blob's). A change in any of them is a new data
vintage: record it in section 9 and rerun from the screen.

| Role | Path (repo root) | Rows | SHA-256 (first 16) |
| :-- | :-- | --: | :-- |
| Dependent data | `ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv` (name kept from the hybrid build; content is the RC base) | 413 | `095e29e73791d016` |
| 2012Q1 fallback list | `ffiec/outputs/hybrid_td_fallback_v2.csv` | 14 | `2ef25a2e082fa73e` |
| Year-to-date repair log | `ffiec/outputs/ytd_repairs_v2.csv` | 28 | `d0ab88b032837ce6` |
| Dropped quarters | `ffiec/outputs/hybrid_dropped_quarters_v2.csv` | 0 | `b02bad382dd943b0` |
| Regressor, monthly | `FEDFUNDS.csv` (through 2026-09) | | `e81bdfd1b428f0ae` |
| Regressor, quarterly | `ffiec/model_dev/inputs/v2-rc-3/FFT_2011-2026.csv` (2011Q1 to 2026Q3; section 7.1) | 63 | `337ebe2f18a7cd1d` |
| Regressor, quarterly (2008 start) | `ffiec/model_dev/inputs/v2-rc-3/FFT_2008-2026.csv` (2008Q1 to 2026Q3) | 75 | `6e74cafb3f63f4d0` |
| Origin regressor (not used) | `FFT_2011-2026.csv` at the repo root (ends 2026Q2; origin file, left unchanged) | 62 | `b244b312ecde3002` |

Full hash of the dependent file: `095e29e73791d016879a40cfd300d9a68e22ec6663f240460acb6077370fb2c6`.

Code: builder `ffiec/data_build/build_ffiec.py` (`hybrid_denominator`, `build_hybrid`, `repair_ytd_breaks`); puller
`ffiec/data_build/ffiec_pull.py`; inputs `ffiec/data/ffiec_items.csv` (long, year to date) and
`ffiec_items_quarterly.csv`; denominator sensitivity `ffiec/sweep_sensitivity.py` (main doc 6.5); FFT builder
`data_build/build_fft.py` (origin code, synced). 28 Prod-Lvl tests pass (`ffiec/tests`; rerun here 2026-11-25 at `2e0fa49`).

---

## 3. Unit of Observation and Schema

One row per bank and quarter: 7 banks x 59 quarters. Key: `cert_number` + `quarter` (quarter-end date, e.g.
`2012-03-31`; read by `bank_plots.to_periods`). Group column for the pipeline: `bank_name`. RSSD is not a column;
it maps through `ffiec/data/cert_rssd.csv` and `rssd_extra.csv`. Amounts in $ thousands; rates in annualized
percent; `*_ie_ann_pf` = 4 x quarterly interest expense.

| Group | Columns | Use in development |
| :-- | :-- | :-- |
| Keys | `bank_name`, `cert_number`, `quarter` | Group and time index |
| Interest-bearing, pro forma (RC base) | `rate_ib_pf`, `A_pf`, `ie_ann_pf`, `n_predecessors_included` | Reconciliation only; not modelled (D9). The two-point legs tile `A_pf` |
| **Segment model 1: interest-bearing non-maturity** | `rate_nmd_eoq_pf` (model variable, D8), `nmd_eoq_pf` (end-of-quarter balance, its denominator), `nmd_ie_ann_pf`; `rate_nmd_pf` and `nmd_avg_pf` (two-point, reference and legs identity only) | **Model variable** (D8, D9) |
| **Segment model 2: time deposits** | `rate_time_eoq_pf` (model variable, D7), `time_eoq_pf` (end-of-quarter balance, its denominator), `time_ie_ann_pf`; `rate_time_pf` and `time_avg_pf` (two-point, reference and legs identity only) | **Model variable** (D7, D9) |
| Foreign offices leg | `rate_for_pf`, `for_avg_pf`, `for_ie_ann_pf` | Inside `rate_ib_pf` only; not a model line. `rate_for_pf` empty where the bank has no foreign offices |
| Total-deposit series (origin method) | `rate_total_pf`, `dep_avg_pf` | Reconciliation and origin comparison only; not modelled (D9) |
| Reconciling total | `rate_total_recon_pf`, `tot_avg_pf` | Audit: `tot_avg_pf = dep_avg_pf` in all rows |
| Merger fields | `adjustment_mode` (`none`, `a`, `b`), `merger_quarter` (0/1), `pct_deposits_acquired_in_quarter` | Merger diagnostics, candidate dummies |
| Fallback flag | `td_fallback_in_pf` (0/1) | 2012Q1 row uses the synthetic 2011Q4 balance (5 rows), in both the interest-bearing and the total-deposit series |
| Standalone | `ie`, `A`, `rate_ib` | Diagnostics only (no predecessors) |
| **Reference only, do not model** | `A_hyb_pf`, `rate_ib_hyb_pf`, `tran_*`, `sav_*`, `rate_nmd_rck` | RC-K hybrid series, affected by the sweep reclassification (main doc P10, P11) |

Identities that hold in the file: `nmd_avg_pf + time_avg_pf + for_avg_pf = A_pf` (to 1e-8) and the same for
interest expense; `rate_ib_pf = 100 x ie_ann_pf / A_pf`. No missing values in `rate_ib_pf`, `rate_nmd_pf`,
`rate_time_pf` or `rate_total_pf`.

---

## 4. Variable Construction

**Interest expense.** `IE_t` = RIAD4508 + RIAD0093 + (RIADA517 + RIADA518 to 2016Q4; RIADHK03 + RIADHK04 from
2017Q1) + RIAD4172 (foreign offices). Year to date converted to quarterly (`YTD_t - YTD_t-1`); merger-quarter interest pro rata as
in the origin.

**Year-to-date repair (main doc 6.8, applied before both builds).** The difference breaks in two cases. A restart
(push-down accounting at an acquisition, e.g. First Niagara 2016Q3) gives a negative quarter: the previous quarter's
rate is carried forward per product, or the quarter is set missing when there is no balance. A restatement (merger of
affiliates under common control reported from the start of the year, e.g. Old National's predecessor Bremer Bank
2014Q4) counts the affiliates' Q1 to Q3 interest twice: their prior year-to-date is removed, only when the
survivor's rate spikes above both neighbours. Every repair is logged in `ytd_repairs_v2.csv`; all affect 2012 to
2016 in the sample. Limit (P14): a restart that leaves a positive but understated quarter is not detected, so a
low single-quarter rate in a merger year is checked in the screen before it is read as pricing.

**Interest-bearing balance (Schedule RC base, owner decision 2026-11-25).**
- Quarter-end interest-bearing deposits `IB_t = RCON6636 + RCFN6636`. `RCFN6636` missing counts as zero only when
  `RCFN2200` is absent or zero.
- Legs: non-maturity `RCON6636 - TD_t`; time `TD_t` (RCON6648 + RCONJ473 + RCONJ474 to 2016Q4, RCONHK16 +
  RCONHK17 from 2017Q1, Schedule RC-E); foreign `RCFN6636`.
- Each quarter-end series is folded pro forma first, then two-point averaged:
  `A_pf,t = (IB_pf,t + IB_pf,t-1) / 2`. This is the origin's order for total deposits, so the reconciling total
  equals `dep_avg_pf`.
- Noninterest-bearing deposits (`RCON6631 + RCFN6631`) are outside the base. Swept (Regulation D reclassification)
  balances are reported there by Schedule RC, so the RC base excludes them without needing their volume.

**Dependent variables.**
- `rate_ib_pf = 400 x IE_pf / A_pf` (all interest-bearing deposits).
- Non-maturity model variable `rate_nmd_eoq_pf = 400 x (RIAD4508 + RIAD0093)_pf / nmd_eoq_pf`, where `nmd_eoq_pf`
  is the pro forma end-of-quarter `RCON6636 - TD` (owner decision D8, main doc 6.10). `rate_nmd_pf` (over the
  two-point `nmd_avg_pf`) stays as the leg of `rate_ib_pf` and as reference; it is not modelled.
- Time model variable `rate_time_eoq_pf = 100 x time_ie_ann_pf / time_eoq_pf`,
  the pro forma end-of-quarter time-deposit balance (owner decision D7, main doc 6.9). `rate_time_pf` (interest over
  the two-point `time_avg_pf`) stays as the leg of `rate_ib_pf` and as reference; it is not modelled.

**Merger adjustment.** Origin fold (`data_build/build_dataset.py`) with the Mode A/B decisions and the 1% test of
the total-deposit build, so the event set equals the origin's.

**2012Q1 fallback.** The 14 thrift predecessors whose first Call Report is 2012Q1 get their 2012Q1 quarter-end
balances as a synthetic 2011Q4 value (balances only), in the interest-bearing and the total-deposit builds alike
(owner decision, P12). It flags the 2012Q1 row of First Horizon, Huntington, M&T, Old National and SouthState.
The total-deposit outputs (`consolidated_*_v2.csv`) drop those banks' 2011Q4 rows, which are outside the sample.

**Regressor.** `FFT_q` = mean of the three monthly FEDFUNDS observations in calendar quarter `q`
(`data_build/build_fft.py`); same series as the origin. 2026Q3 = 3.67 (July 3.63, August 3.63, September 3.75).

**Missing data.** A quarter is dropped if a component is missing; nothing is zero-filled apart from the
`RCFN6636` rule above. No quarter is dropped in this build.

---

## 5. Sample

| Bank | Cert | Quarters | Merger quarters (Mode A / B) | Fallback row | `A_pf / dep_avg_pf` min / median / max | Median `rate_ib_pf` | Max | Median `rate_nmd_eoq_pf` | Median `rate_time_eoq_pf` | Non-maturity share of `A_pf` |
| :-- | --: | --: | :-: | :-: | :-: | --: | --: | --: | --: | --: |
| First Horizon | 4977 | 59 | 4 (4 / 0) | 2012Q1 | 0.60 / 0.74 / 0.79 | 0.57 | 3.51 | 0.40 | 1.15 | 84% |
| Glacier | 30788 | 59 | 16 (15 / 1) | none | 0.62 / 0.70 / 0.78 | 0.39 | 2.18 | 0.28 | 0.87 | 79% |
| Huntington | 6560 | 59 | 6 (6 / 0) | 2012Q1 | 0.67 / 0.78 / 0.86 | 0.50 | 3.13 | 0.31 | 1.19 | 82% |
| KeyBank | 17534 | 59 | 2 (1 / 1) | none | 0.66 / 0.72 / 0.82 | 0.41 | 2.89 | 0.24 | 1.40 | 86% |
| M&T | 588 | 59 | 2 (2 / 0) | 2012Q1 | 0.57 / 0.70 / 0.79 | 0.46 | 2.91 | 0.30 | 1.14 | 84% |
| Old National | 3832 | 59 | 11 (11 / 0) | 2012Q1 | 0.65 / 0.77 / 0.85 | 0.41 | 3.04 | 0.20 | 1.10 | 80% |
| SouthState | 33555 | 59 | 13 (12 / 1) | 2012Q1 | 0.64 / 0.73 / 0.81 | 0.52 | 3.09 | 0.34 | 0.96 | 79% |

Estimation sample (five banks; Glacier's and SouthState's rows are dropped by the run filter): 295
bank-quarters, 25 merger quarters, 4 fallback rows (First Horizon, Huntington, M&T, Old National), `A_pf / dep_avg_pf`
0.568 to 0.863 (median 0.737), median `rate_ib_pf` 0.47 vs `rate_total_pf` 0.36. Glacier and SouthState rows are kept
for reference only.

Ratios are over all 59 quarters; across the 413 rows they run from 0.568 to 0.863 (median 0.730). Window 2012Q1 to
2026Q3; about 56 usable observations per bank after lags and differencing. Excluded as before: quarters before
2012 (thrift filers); Wilmington Trust NA (33911) and Federal Trust Bank (32580), which file no Call Report.

---

## 6. Data Quality and Known Issues

**Build checks passed** (main doc 6.2 and 6.6):
- reconciling total equals `dep_avg_pf` in all 413 rows;
- legs add up to `A_pf` exactly;
- `A_pf < dep_avg_pf` in every row;
- BankFind reconciliation inside the window: 13 of 406 quarters differ by more than 0.005 (max 0.045);
- quarter-end identities `6631 + 6636 = 2200` hold across 4,601 filings;
- event set equals the origin's;
- no break at the 2017Q1 time-deposit definition change.

Checked again for this note (2026-11-26, at `cddc1d1`): against `485ebb6`, every existing column is identical (to
1e-12) and `nmd_eoq_pf`, `rate_nmd_eoq_pf` are added (413 x 40); `rate_nmd_eoq_pf = 100 x nmd_ie_ann_pf / nmd_eoq_pf`
exactly; 28 tests pass. Non-maturity impact reproduced for the five banks (end-of-quarter less two-point): median
-0.1 to -0.2 bp, 95th percentile of absolute 2 to 4 bp, max 11 bp (First Horizon 2023Q2, 2.22 to 2.11);
correlation of quarterly changes 0.984 to 0.997.

**Impact of the end-of-quarter denominators (D7, D8; main doc 6.10, build session figures).**

| | Non-maturity | Time |
| :-- | :-- | :-- |
| Median change per bank | -0.1 to -0.2 bp | +0.5 to +1.3 bp |
| 95th percentile of absolute change | 2 to 4 bp | 25 to 40 bp |
| Max | 11 bp | 87 to 94 bp |
| Spikes over 0.3 points | none new | 25 to 11 |
| Static OLS slope on FFT, two-point / end-of-quarter | FH 0.525/0.523, HBAN 0.464/0.461, KEY 0.418/0.415, M&T 0.424/0.421, ONB 0.415/0.414 | FH 0.679/0.641, HBAN 0.696/0.669, KEY 0.654/0.621, M&T 0.630/0.603, ONB 0.675/0.645 |

The slopes only illustrate the change; they are not ECM betas. End-of-quarter denominators are exact only when
balances are flat within the quarter (P15), and the product rates are on end-of-quarter balances while
`rate_ib_pf` is two-point, so the segment rates and the reconciling interest-bearing rate are not on the same base.

Checked at `485ebb6` (2026-11-26): against `2e0fa49`, every existing column is identical
(to 1e-12) and two columns are added; `rate_time_eoq_pf` and `time_eoq_pf` equal the end-of-quarter values of
`b052e00`; legs identity holds; 28 tests pass. `rate_time_eoq_pf` (two-point in brackets): First Horizon 2023Q2 to
Q3 3.55 / 4.39 (4.42 / 5.22); KeyBank 2023Q1 to Q2 3.32 / 3.95 (4.20 / 4.68); M&T 2022Q2 to Q3 0.091 / 0.089.
The FFT files in `inputs/v2-rc-3/` are unchanged and valid for this vintage.

Checked at `2e0fa49` (2026-11-25):
- Against `9fa7dfc`, 20 rows change (the repaired bank-quarters, all 2012 to 2016), in interest expense and the
  rates only; balances, columns, events and modes are unchanged. Largest: KeyBank 2016Q3 `rate_ib_pf` 0.06 to 0.31,
  time 0.14 to 1.09; Glacier 2012Q2 0.84 to 0.58; Old National 2014Q4 0.41 to 0.26, time 1.30 to 0.74.
- 413 rows, 59 quarters per bank, no missing model rates.
- The legs identity holds.
- The correlation of `rate_ib_pf` with `rate_total_pf` is 0.998 to 0.999 per bank.

**Resolved by the RC base.** The Huntington 2021Q2 to Q4 outlier and the M&T 2025Q1 move flagged in rev 0.1 came
from the RC-K reclassification effect. On the RC base, Huntington's interest-bearing share is 0.685, 0.671 and
0.668 for 2021Q1 to Q3, with no jump. Neither is an outlier candidate now.

**Still to review in the estimation phase:**

| Item | Detail | Treatment default |
| :-- | :-- | :-- |
| SouthState 2025Q1 | Independent Bank Group merger quarter; -33 bp under every base (main doc 6.5, P8) | Out of scope (five banks) |
| Merger quarters | 25 bank-quarters with `merger_quarter = 1` in the five banks (Old National 11, Huntington 6, First Horizon 4, KeyBank 2, M&T 2); 54 in the full file | As the origin |
| M&T 2022Q2 to Q3 time rate | 0.087% and 0.085%; matches the 10-Q (time-deposit interest $1,227K and $1,124K), so reported data, not a build error. Likely fair-value premium amortization on acquired People's United time deposits (10-Q note not checked; P13) | Flag; test a dummy in the time-deposit model |
| Huntington 2026Q2 time rate | 3.10% on the end-of-quarter basis (3.53% two-point), between 4.10% in 2026Q1 and 3.45% in 2026Q3. The end-of-quarter time balance rose 32% to 29.9 bn, then fell to 23.8 bn in 2026Q3; if the inflow came late in the quarter, the end balance overstates the earning balance (P15) | Flag; test a dummy in the time-deposit model |
| Fallback rows | 4 rows of 2012Q1 in the five banks (5 in the full file) with a one-point time and noninterest-bearing average (P9) | Keep; sensitivity: start at 2012Q2 |

Outliers are flagged and tested (dummy or exclusion, decided in the screen and recorded), never edited in the
data file.

**Level and scale.** The segment rates are not comparable with the origin's total-deposit rate: they exclude
noninterest-bearing deposits (the interest-bearing base is a median 73% of total deposits, 57% to 86%) and use
end-of-quarter balances. Segment betas are therefore expected to be higher than the origin betas. This is a change
of definition, not of pricing. Any comparison with the origin uses `rate_total_pf` (reconciliation only), on the
same window.

**Superseded.** The rev 0.1 findings on the hybrid base no longer apply to the model variable. The base understated
the beta by about 15% to 30% in the 2015 to 2019 cycle and moved in level around 2021 to 2022 (main doc 6.4 and
6.5). The hybrid series stay in the file as reference only.

---

## 7. Prerequisites Before Estimation

### 7.1 FFT ends on 2026Q3 (done 2026-11-26)
Owner decision D5: the sample ends 2026Q3. The origin `FFT_2011-2026.csv` ends 2026Q2 (`build_fft.py` cuts FFT to
the end of the FDIC bank file), and `bank_plots.check_series_end` stops the pipeline when FFT and the bank data end
differently. FFT was rebuilt from the committed `FEDFUNDS.csv` (no refresh) with
`python data_build/build_fft.py --out-dir ffiec/model_dev/inputs/v2-rc-3 --end 2026Q3`.
Checks: identical to the origin files on every overlapping quarter (max difference 0.0, both start years);
2026Q3 = 3.67 (mean of July 3.63, August 3.63, September 3.75), equal to the bank data end. The origin files
at the repo root are unchanged.

### 7.2 Pipeline wiring
The origin scripts default to the FDIC merger-adjusted file and `--y rate_pf_clean`. Development runs pass:
- `--dependents ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv`;
- `--y rate_nmd_eoq_pf` and `--y rate_time_eoq_pf` (one run per segment; no aggregate run);
- the rebuilt FFT (`ffiec/model_dev/inputs/v2-rc-3/`);
- an output directory under a Prod-Lvl vintage tag.

No origin output is overwritten (main doc 5.2). The scope is five banks: the bank filter (certs 4977, 6560, 17534, 588, 3832) is applied in
the run and the data file stays complete.

### 7.3 Window for origin comparison
Common window with the origin: 2012Q1 to 2026Q2 for the five banks.

### 7.4 After estimation: cumulative beta vs High-Level (procedure only; owner, main doc 6.11)
Run only after the ten segment ECMs have champions. No provisional figures are recorded.
1. Segment betas: each champion's long-run coefficient (theta), one per bank and segment (`nmd`, `time`), written
   to a CSV (`bank_name`, `segment`, `beta`) in the Prod-Lvl vintage output directory.
2. Weights: each bank's pro forma two-point balances averaged over 2012Q1 to 2026Q3: `B_nmd = mean(nmd_avg_pf)`,
   `B_time = mean(time_avg_pf)`, `B_total = mean(dep_avg_pf)`.
   - Interest-bearing basis: `(B_nmd b_nmd + B_time b_time) / (B_nmd + B_time)`; weights sum to 1.
   - Total-deposit basis: `(B_nmd b_nmd + B_time b_time) / B_total`; noninterest-bearing deposits and foreign offices
     at beta 0, so the weights sum to less than 1.
3. Comparison with the High-Level champion betas (High-Level doc rev 2.1, section 1.3;
   `ffiec/reference/high_level_champion_betas.csv`) on the total-deposit basis, the interest-bearing basis alongside.
4. Tool (run by this session after estimation; `a90a8ff`): `python -I ffiec/cumulative_beta.py --segment-betas
   <vintage dir>/segment_betas.csv --out <vintage dir>/cumulative_beta.csv`. Both arguments are required; nothing is
   written under `ffiec/outputs/`.

The weights are two-point balances while the segment rates use end-of-quarter balances. Which basis to report and
whether to use sample-average or latest-quarter weights are open (D10, O8).

---

## 8. Open Decisions (owner)

| # | Main doc | Decision | Default used until decided |
| :-: | :-- | :-- | :-- |
| D1 | O1 | Model variable `rate_ib_pf` (RC base) | **Closed 2026-11-26: not a model variable** (D9). `rate_ib_pf` was an assumption, never confirmed by the owner |
| D2 | O3 | Segments: interest-bearing non-maturity (`rate_nmd_eoq_pf`, D8) and time (`rate_time_eoq_pf`, D7); foreign and noninterest-bearing not modelled | **Closed 2026-11-26 by D9** |
| D3 | O7 | Scope: seven banks or five (Huntington, Old National, KeyBank, M&T, First Horizon) | **Closed 2026-11-26: five banks** |
| D4 | P12 | Apply the 2012Q1 fallback to the total-deposit series | **Closed 2026-11-25: applied** (`9fa7dfc`) |
| D5 | none | Sample end: 2026Q3 (rebuild FFT) or 2026Q2 | **Closed 2026-11-26: 2026Q3**, FFT rebuilt (7.1) |
| D6 | O2 | COVID liquidity dummy retest on the Prod-Lvl series | Retested in development |
| D7 | none | Time-deposit denominator: two-point average or end-of-quarter | **Closed 2026-11-26: end-of-quarter** (owner; build session had recommended the two-point average). Applied in `485ebb6` as `rate_time_eoq_pf`; First Horizon and KeyBank 2023 lag flags no longer needed |
| D8 | none | Non-maturity denominator: two-point average or end-of-quarter | **Closed 2026-11-26: end-of-quarter** (owner asked for it and to adopt it if the impact was moderate; build session found it moderate and adopted it, `cddc1d1`, main doc 6.10). Relayed by the build session |
| D9 | O3 | Model scope | **Closed 2026-11-26: two segments per bank (non-maturity and time deposits), ten models; no aggregate model.** Owner: "I want to scope to be two segments for each bank: NMD rates and time-deposit rates." Relayed by the build session |
| D10 | O8 | Cumulative beta: which basis to report (total-deposit or interest-bearing), and sample-average or latest-quarter weights | Open; procedure in 7.4 uses sample-average weights and reports both bases. Does not block estimation |

---

## 9. Rules for Development Sessions

1. Read the pinned inputs in section 2 only. Check the hash before a run and stop if it differs.
2. Never edit `ffiec/outputs/` or any origin output. Development outputs go to a Prod-Lvl vintage directory.
3. Do not model the reference-only columns (section 3).
4. Prune deterministic terms after the cointegration screen without re-checking them against it, and log a flag
   where the form differs (shared estimation rule). The out-of-sample champion choice is the default.
5. Log every departure from the origin method in the main doc, section 0.2.
6. A new pull or rebuild is a new data vintage. Update section 2 and the table below, then rerun from the screen.

| Data vintage | Date | Data commit | Change |
| :-- | :-- | :-- | :-- |
| v2-rc-6 | 2026-11-26 | `cddc1d1` | End-of-quarter non-maturity rate as new columns `rate_nmd_eoq_pf`, `nmd_eoq_pf`; all earlier columns unchanged. Model data for all lines |
| v2-rc-5 | 2026-11-26 | `485ebb6` | End-of-quarter time rate as new columns `rate_time_eoq_pf`, `time_eoq_pf`; all `2e0fa49` columns unchanged. Superseded by v2-rc-6 for the non-maturity line |
| v2-rc-4 | 2026-11-26 | `b052e00` | Superseded the same day: overwrote `rate_time_pf` with the end-of-quarter rate. Not for estimation |
| v2-rc-3 | 2026-11-25 | `2e0fa49` | Year-to-date breaks repaired; interest and rates change in 20 bank-quarters (2012 to 2016), balances unchanged |
| v2-rc-2 | 2026-11-25 | `9fa7dfc` | 2012Q1 fallback in the total-deposit series; `rate_total_pf` and `dep_avg_pf` change in 5 rows, nothing else |
| v2-rc-1 | 2026-11-25 | `49bfdb8` | Schedule RC interest-bearing base; 413 bank-quarters, 2012Q1 to 2026Q3, none dropped; product legs |
| v2-hybrid-1 | 2026-11-14 | `ff50a25` | Hybrid RC-K base, 408 bank-quarters. Superseded; not for estimation |
