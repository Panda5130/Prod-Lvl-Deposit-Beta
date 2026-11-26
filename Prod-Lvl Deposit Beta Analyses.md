# Prod-Lvl Deposit Beta Analyses

> **STATUS: DRAFT. NOT VALIDATED. NOT APPROVED FOR PRODUCTION USE.**
> SR 11-7 / OCC 2011-12 style development document for the Prod-Lvl model. It replaces the inherited high-level working document in this repository.

---

## 0. Document Control

| Item | Detail |
| :--- | :--- |
| Document title | Prod-Lvl Deposit Beta Analyses |
| Model family | Regional bank deposit-rate error-correction models (deposit beta) |
| Model type | Single-equation, one-step error-correction models (ECM), as in the origin model (section 3) |
| Development status | Draft; data final for two segments x five banks (D7 to D9), estimation not yet run |
| Validation status | Not validated |
| Model tier / materiality | Not yet assigned |
| Developer / owner | Shivam Panda (GitHub: Panda5130) |
| Code repository | `Panda5130/Prod-Lvl-Deposit-Beta` |
| Origin model | High-Level Deposit Beta, repository `Panda5130/Deposit-Beta` (FDIC BankFind data), document "WIP Regional Banking Deposit Beta Analyses", version 2.0 (WIP), last synced origin commit `ea95980` |
| Document date | 2026-11-26 |
| Data period | 2012Q1 to 2026Q3 (59 quarters per bank, section 6.1; about 56 after lags and differencing) |

### 0.1 Naming
- **High-Level Deposit Beta** (origin repository): bank-level deposit interest expense and total deposits from FDIC BankFind. Kept as the benchmark.
- **Prod-Lvl Deposit Beta** (this repository): the same models fed by FFIEC Call Report data, the granular source that later phases need. Earlier working documents used "FDIC" and "FFIEC" for the two sources while the choice was open. The choice is made, so this document uses the two repository names.

### 0.2 Revision History
| Version | Date | Description | Validation |
| :--- | :--- | :--- | :--- |
| 0.13 (draft) | 2026-11-26 | Cumulative (balance-weighted) beta of the two segments and its comparison with the High-Level betas (6.11, `ffiec/cumulative_beta.py`); provisional until the segment ECMs are estimated | Static segment betas weighted over total deposits reproduce the static total-deposit beta within 0.034 |
| 0.12 (draft) | 2026-11-26 | Model scope set by the owner: two segments per bank, interest-bearing non-maturity and time deposits (D9; 1.1, 1.3, 2, 3.1). No aggregate (total-deposit or interest-bearing) model; O1 closed. Data unchanged | None needed (no data change) |
| 0.11 (draft) | 2026-11-26 | D8: non-maturity model also uses an end-of-quarter denominator (`rate_nmd_eoq_pf`, `nmd_eoq_pf`); both product models now default to end-of-quarter (6.10) | Impact moderate: median -0.2 bp, 95th percentile 4 bp, max 11 bp; no other column changed; 413 x 40; 28 tests |
| 0.10 (draft) | 2026-11-26 | D7: time-deposit model uses an end-of-quarter denominator (owner decision; 6.9, P15). New columns `rate_time_eoq_pf` and `time_eoq_pf`; `rate_time_pf` (two-point) kept as reference; no other series changed | Matches the tested variant exactly; legs still tile `A_pf`; 28 tests |
| 0.9 (draft) | 2026-11-26 | Scope decided: five banks estimated (O7, 1.2); sample end decided 2026Q3 and FFT rebuilt to 2026Q3 (1.3, 3.1, 4.4); dataset unchanged | FFT equals origin on every common quarter |
| 0.8 (draft) | 2026-11-25 | Year-to-date breaks in the quarterly interest expense repaired (6.8): push-down restarts (previous-quarter rate carried forward) and common-control restatements (affiliates' prior YTD removed); M&T 2022Q2-Q3 time-deposit dip confirmed as reported data (P13) | BankFind reconciliation in window 13 of 406 (was 21), max 0.045 (was 0.160); 28 tests |
| 0.7 (draft) | 2026-11-25 | 2012Q1 one-point fallback applied to the total-deposit build as well (owner decision; P12 resolved): `rate_total_pf` 2012Q1 corrected for five banks; their 2011Q4 rows leave the total-deposit outputs | Reconciling total equals `dep_avg_pf` in all 413 rows; BankFind reconciliation in window 21 of 406 (was 25); 26 tests |
| 0.6 (draft) | 2026-11-25 | Schedule RC interest-bearing base built (owner decision, 6.4): quarter-end `RCON6636 + RCFN6636` folded pro forma, then two-point averaged; product legs non-maturity / time / foreign tile it; sensitivity script committed (6.5, O6); product lines and sweep sourcing (6.7); finding on the 2012Q1 total-deposit rate (P12) | Reconciliation exact in 408 of 413 rows (6.6); 25 tests |
| 0.5 (draft) | 2026-11-16 | One-point 2011Q4 fallback for thrift predecessors (all 7 banks now 59 quarters); pro forma product rates (transaction, savings including MMDA, time); reconciling total-deposit series built after the `6631`/`6636` pull; finding: RC-K savings averages include noninterest-bearing reclassified balances (section 6.4), denominator decision reopened (O1) | Quarter-end identities `6631 + 6636 = 2200` hold; reconciliation fails by a median 13% to 2021, section 6.4 |
| 0.4 (draft) | 2026-11-14 | Hybrid denominator built and validated on the Call Report data (J473/J474 re-pull complete); results of the build in section 6; P7 and O1 updated | Four build checks in section 6.2; estimation not yet rerun |
| 0.3 (draft) | 2026-11-14 | Hybrid denominator finalized (section 5.4): items, formulas, pro forma, missing-data and validation rules; time-deposit item correction (J473 + J474 replace RCON2604); re-pull specified (5.5) | Item coverage checked on 4,601 entity-quarters; build not yet run |
| 0.2 (draft) | 2026-11-14 | Owner approved the RC-K average-balance denominator; feasibility check found no RC-K time-deposit average from 2017Q1 and no noninterest-bearing average (section 5.4); fallback options recorded, build pending owner choice | MDRM search; two live filings inspected |
| 0.1 (draft) | 2026-11-14 | First SR 11-7 draft for Prod-Lvl. Source switch from BankFind to Call Reports approved by the owner; sample starts at 2012Q1. Built from the pilot record (section 4) | Pilot reconciliation (section 4.3); no model rerun yet |

---

## 1. Executive Summary

### 1.1 Purpose
Estimate deposit betas (the long-run share of a federal funds rate change that passes through to a deposit rate) and the speed of adjustment toward them, using FFIEC Call Report data, for two segments in each of five U.S. regional banks: interest-bearing non-maturity deposits (NMD) and time deposits. Each bank and segment is modeled separately: ten models (D9, owner decision 2026-11-26: "I want to scope to be two segments for each bank: NMD rates and time-deposit rates."). No aggregate total-deposit or interest-bearing deposit model is estimated; the origin model's single bank-level rate is not carried over.

### 1.2 Banks in Scope
Estimated (owner decision 2026-11-26, O7): First Horizon Bank (cert 4977), Huntington National Bank (6560), KeyBank National Association (17534), Manufacturers and Traders Trust Company (588), Old National Bank (3832). Glacier Bank (30788) and SouthState Bank (33555) are not estimated; they stay in the dataset, which is built for all seven, and the bank filter is applied at run time. Merger predecessors are included pro forma (section 4.2).

### 1.3 What Changes From the Origin Model
| Item | Origin (High-Level) | Prod-Lvl |
| :-- | :-- | :-- |
| Source of deposits and interest expense | FDIC BankFind Financials API | FFIEC Call Reports, CDR Public Web Service |
| Sample | 2011Q1 to 2026Q2 (62 quarters) | 2012Q1 to 2026Q3 (59 quarters; end decided 2026-11-26, section 4.4) |
| Dependent variable | `rate_pf_clean`, one total-deposit rate per bank (two-point average denominator) | Two rates per bank (D9): `rate_nmd_eoq_pf` (NMD, D8) and `rate_time_eoq_pf` (time deposits, D7), both on pro forma end-of-quarter balances (sections 6.7, 6.9, 6.10). No aggregate rate is modelled |
| Regressor, model form, selection, backtests | As origin | Unchanged; rerun on the new data |
| Merger events | FDIC `/history` plus 7 NIC-found transfers | Same event list (read from the origin repository's shared file), cross-checked to NIC Transformations |

Estimation results are not yet available. This document will carry them once the ten models are estimated.

---

## 2. Model Purpose, Scope and Intended Use

### 2.1 Business Purpose
Deposit betas feed interest-rate risk measurement (NII and EVE sensitivity), deposit pricing analysis, funds-transfer pricing and peer benchmarking. The Call Report source carries deposit detail by account type (Schedules RC, RC-E and RI), which allows separate betas for non-maturity and time deposits; that split is the scope of this model (D9).

### 2.2 Intended Use (once validated)
- Peer benchmarking of long-run deposit pass-through.
- Scenario projection of deposit rates conditional on a federal funds rate path, up to 8 quarters.

### 2.3 Uses Outside Scope
- Production pricing or regulatory capital decisions before validation.
- A beta for total deposits or for all interest-bearing deposits (not estimated, D9). `rate_total_pf` and `rate_ib_pf` stay in the data file for reconciliation only.
- Separate transaction, savings/MMDA or time-by-size betas: no consistent Call Report basis (6.7).
- Horizons beyond 8 quarters or rate regimes outside the sample (for example negative rates).

### 2.4 Model Output
Per bank and segment (NMD, time deposits): estimated one-step ECM (speed of adjustment, long-run beta with delta-method standard errors), in-sample and rolling-origin forecast error, and long-run beta stability.

---

## 3. Model Overview

### 3.1 Variables
| Role | Variable | Definition | Source |
| :-- | :-- | :-- | :-- |
| Dependent (y), NMD model | `rate_nmd_eoq_pf` | 400 x quarterly (`RIAD4508 + RIAD0093`) / end-of-quarter (`RCON6636` less time deposits), pro forma for mergers (D8, 6.10) | FFIEC Call Reports |
| Dependent (y), time-deposit model | `rate_time_eoq_pf` | 400 x quarterly time-deposit interest (`RIADA517 + A518` to 2016, `RIADHK03 + HK04` from 2017) / end-of-quarter time deposits (`RCON6648 + J473 + J474` to 2016, `RCONHK16 + HK17` from 2017), pro forma (D7, 6.9) | FFIEC Call Reports |
| Regressor (x) | `FFT` | Quarterly average of the monthly effective federal funds rate | FRED `FEDFUNDS`; Prod-Lvl series rebuilt to 2026Q3 (section 4.4) |

Call Report items (fixed in `ffiec/data_build/items.py`, each checked against the current MDRM). The model items are in the table above. Total deposits are used only for the merger materiality test (Mode A/B) and the reconciliation: total deposits `RCFD2200` if present, else `RCON2200 + RCFN2200` (domestic plus foreign offices); deposit interest expense from the Schedule RI domestic codes plus `RIAD4172` (foreign offices). Call Report income items are year to date and are converted to quarterly values; dollars are divided by 1,000.

### 3.2 Model Form
Unchanged from the origin model: one-step ECM fitted by OLS, specification chosen among Engle-Granger, Johansen VECM and ARDL bounds forms, champion chosen out of sample, one asymmetric variant per passing specification, deterministic terms pruned after the screen. The origin document is the reference for the equations, the selection rule and the backtest design. Any departure on Prod-Lvl is recorded in section 0.2.

---

## 4. Data

### 4.1 Source
- FFIEC CDR Public Web Service (SIS611 v1.10), one filing per bank per quarter, by RSSD ID; 8,848 filings pulled for the pilot, none amended.
- FDIC certificate to RSSD mapping from the FDIC institutions API, with corrections in `ffiec/data/rssd_extra.csv` (section 4.2).
- Credentials are read only from the OS keyring or environment variables and are never logged or committed. Raw responses are hashed; an amendment is detected by hash change and logged.

### 4.2 Merger Adjustment
The origin merger logic (`data_build/build_dataset.py`) is reused unchanged, fed by Call Report data; Mode A/B, the 1% materiality test and the recursion are as origin. Events are FDIC `/history` plus the supplementary transfers of origin issue #20, cross-checked against NIC Transformations (380 of 387 events match; the 3 candidate mergers NIC adds are among the supplementary transfers). Certificate to RSSD is not one to one: 9 certs share 4 RSSDs, the API gives 3 certs another cert's RSSD, and 4 trust certs have no API RSSD. Filings are assigned to a cert only if the cert existed that quarter and the filing's total deposits are within 10% of BankFind's (identity check; values stay from the Call Report).

### 4.3 Reconciliation With the Origin Source (pilot)
- Total deposits: 0 of 8,503 shared bank-quarters differ.
- Interest expense: 63 bank-quarters differ by more than $1 thousand. The Call Report quarterly series ties to the filed year-to-date; BankFind's own quarterly field does not tie to its year-to-date field in those quarters. The Call Report is the reference.
- Window: savings institutions filed Thrift Financial Reports to the OTS until 2011 and Call Reports from March 2012, so quarters before 2012 lack some predecessors. The reference window is 2012Q1 onward (decision 2026-11-13). Earlier quarters are kept in the outputs for reference only. Inside the window, 13 of 406 bank-quarters differ from the origin pro forma rate by more than 0.005 points (median 0.000, 95th percentile 0.0025, maximum 0.045). Before 2026-11-25 it was 25 of 406 (95th percentile 0.0074, maximum 0.160); the 2012Q1 fallback (P12) brought it to 21 and the year-to-date repair (6.8) to 13; the differences trace to the two documented origin-side items (predecessors without Call Reports: Wilmington Trust NA, Federal Trust Bank; BankFind quarterly interest expense).
- Evidence files: `ffiec/outputs/reconciliation_summary.csv`, `reconciliation_quarters.csv`, `nic_event_differences.csv`, `missing_filings_check.csv`.

### 4.4 Sample
2012Q1 to 2026Q3: 59 quarters per bank, about 56 usable after lags and differencing. Sample end decided by the owner 2026-11-26 ("Rebuild FFT to 2026Q3"). FFT was rebuilt for Prod-Lvl with `build_fft.py --end 2026Q3 --out-dir ffiec/model_dev/inputs/v2-rc-3` from the committed `FEDFUNDS.csv`, with no data refresh: it equals the origin FFT in every quarter both cover, and 2026Q3 = 3.67. Hashes: FFT_2011-2026 `337ebe2f18a7cd1d`, FFT_2008-2026 `6e74cafb3f63f4d0`. The origin FFT files at the repository root are unchanged. The rebuilt files were produced by the Prod-Lvl session and are not committed from this worktree. This is shorter than the origin sample (62), which lowers test power further (limitation L1). Seven-bank results from the two sources are compared on the common window before any conclusion about the change in estimates.

---

## 5. Data Source Change Control (SR 11-7)

### 5.1 Change
Total deposits and deposit interest expense switch from BankFind to Call Reports. This is a model change: it alters the input data of every estimate.

### 5.2 Controls
1. **Separate vintage, separate repository.** Origin results stay in `Panda5130/Deposit-Beta` and are never overwritten. Prod-Lvl writes its own outputs here, with a vintage tag in the file name, so that the two sets can be compared side by side.
2. **Comparison file.** A fixed comparison (per bank: spec, lambda, long-run beta, MAE, ratings, origin versus Prod-Lvl on the same 2012Q1 window) is produced on every rerun.
3. **Lineage.** Each output records the origin commit it was synced from and the Call Report pull date.
4. **Sync.** Origin changes arrive only by merge into a dated sync branch with a validation note. Prod-Lvl does not push to the origin repository.
5. **Reproducibility.** `ffiec_pull.py` (incremental, with a resumable `--backfill` of item codes into held filings), `build_ffiec.py`, `reconcile.py`, `materiality.py`; 24 tests in `ffiec/tests`.

### 5.3 Rerun Plan (to complete before validation)
1. Rebuild the dataset on the 2012Q1 window (already built; rerun on each pull).
2. Rerun the screen (unit root, break, cointegration), model selection, estimation, asymmetric variants and pruning on the new data.
3. Rerun backtests, beta stability and scenarios; compare to the origin on the same window.
4. Retest the COVID liquidity dummy on the Prod-Lvl series when the models are developed (origin excluded it for all seven banks; not applied in the pilot).
5. Decide the champion per bank and record any change from the origin.

### 5.4 Denominator: Schedule RC-K Average Balances (owner decision 2026-11-14)
**Decision.** The owner chose to switch the denominator of the deposit rate from the two-point average of quarter-end total deposits to Schedule RC-K quarterly-average balances. The numerator (deposit interest expense) is unchanged. Under SR 11-7 this is a second change to the dependent variable, recorded separately from the source switch in 5.1 so each can be compared against the origin on its own.

**Expected effect.** The rate moves up in level (the pilot gap, 2008 to 2016: 0.03 to 0.12 points, correlation with the two-point rate 0.97 to 1.00) if the base is interest-bearing deposits, because noninterest-bearing deposits drop out. The effect on the long-run beta is expected to be small and is to be measured in the rerun, not assumed.

**Feasibility finding (2026-11-14), which blocks a complete series.** Items were checked against the current MDRM and against live filings (KeyBank, RSSD 280110, 2016Q4 and 2018Q4, service output):
| RC-K average | Code | 2012Q1 to 2016Q4 | 2017Q1 onward |
| :-- | :-- | :-: | :-: |
| Interest-bearing transaction accounts, domestic | RCON3485 | Reported | Reported |
| Savings deposits including MMDAs, domestic | RCONB563 | Reported | Reported |
| Time deposits under $100,000 | RCONA529 | Reported | Ended 2016Q4; no successor in MDRM |
| Time deposits of $100,000 or more | RCONA514 | Reported | Ended 2016Q4; no successor in MDRM |
| Interest-bearing deposits, foreign offices | RCFN3404 | Reported (031 filers) | Reported |
| Noninterest-bearing deposits, average | none | Not collected | Not collected |

The RC-K time-deposit averages were dropped when the time-deposit size split moved to $250,000 in 2017; the new items (RCONHK16 and HK17) are quarter-end balances in Schedule RC-E, not averages. Time deposits are a median 16% of total deposits for the banks and predecessors from 2017 (range 2% to 74%), so the missing piece is not small. No RC-K noninterest-bearing average exists in any period, so an RC-K rate on total deposits is not available either. Consequence: a pure RC-K interest-bearing denominator exists only for 2012Q1 to 2016Q4 (20 quarters), too short for the models.

**Decision (owner, 2026-11-14): hybrid denominator for all 58 quarters.** Final method (build pending the re-pull in 5.5):

*Balances, for entity e (an RSSD) and quarter t, in dollars:*
- `NMD_ib = RCON3485 + RCONB563` (RC-K averages: interest-bearing transaction accounts, savings including MMDAs). Excludes noninterest-bearing demand deposits (MDRM text of RCON3485).
- `FOR = RCFN3404` (RC-K average, foreign offices; filed by FFIEC 031 filers with foreign offices only).
- `TD_t` = quarter-end time deposits: to 2016Q4 `RCON6648 + RCONJ473 + RCONJ474`; from 2017Q1 `RCONHK16 + RCONHK17`. The two splits tile the same total (under $100k plus $100k and over; $250k or less plus over $250k).
- `TD_avg_t = (TD_t + TD_{t-1}) / 2`, in every quarter (not RC-K to 2016, so the definition has no break). 2012Q1 needs 2011Q4.
- **`A_t = NMD_ib + FOR + TD_avg_t`** is the interest-bearing deposit average balance.

*Interest expense:* `IE_t` = domestic RI codes (ri_dom_codes: 4508, 0093, and A517 + A518 to 2016 or HK03 + HK04 from 2017) plus `RIAD4172` (foreign), converted from year to date to quarterly, as in the pilot.

*Series:*
- **Model variable (assumed, owner to confirm): `rate_ib = 400 x IE_t / A_t`**, the interest-bearing deposit rate. NIB deposits are excluded from the base; they carry no interest expense and are not averaged in RC-K.
- **Second series: `rate_nmd = 400 x (RIAD4508 + RIAD0093) / NMD_ib`**, domestic interest-bearing non-maturity deposits, exact RC-K averages in all quarters. Superseded 2026-11-25: kept as the reference column `rate_nmd_rck`; the model's non-maturity rate is `rate_nmd_pf` on the Schedule RC base (6.6, 6.7).
- **Reconciling series (built 2026-11-16):** `rate_total_recon = 400 x IE_t / (A_t + NIB_avg_t)`, with `NIB_avg_t` the two-point average of `RCON6631 + RCFN6631` (Schedule RC quarter-end noninterest-bearing deposits; `RCFN6631` missing counts as zero only when `RCFN2200` is absent or zero). Results in section 6.4.
- **Product rates (built 2026-11-16, pro forma, O3):** transaction `400 x RIAD4508 / RCON3485`, savings including MMDA `400 x RIAD0093 / RCONB563`, time `400 x time-deposit IE / TD_avg_t` (time-deposit IE: `RIADA517 + RIADA518` to 2016, `RIADHK03 + RIADHK04` from 2017). Each leg is folded with the same merger decisions as `rate_ib_pf`.

*Pro forma:* the origin merger logic is reused; `A_t` and `IE_t` are scaled by the transfer share and summed over predecessors, as `DEP` and `IE` are in the origin. Mode A/B and the 1% materiality decisions stay on total deposits (`DEP`); the build asserts that the event set equals the origin's.

*Missing data:* a quarter is dropped if any component other than `RCFN3404` is missing; `RCFN3404` missing counts as zero only when `RIAD4172` is also absent or zero, otherwise the quarter is flagged. Nothing else is zero-filled.

*One-point fallback (owner decision 2026-11-16):* in 2012Q1 only, an entity with no Call Report for 2011Q4 uses its own 2012Q1 quarter-end time deposits as the prior value, so `TD_avg = TD_2012Q1` (the same rule applies to the NIB average). These are the 14 savings-institution predecessors that filed Thrift Financial Reports to the OTS until 2011Q4 (certs 11990, 13074, 27334, 28994, 29085, 29979, 30720, 30750, 32212, 32503, 32957, 34413, 34657, 57760). BankFind holds their 2011Q4 time-deposit balance (`NTRTIME`, which equals `6648 + J473 + J474` for all 80 Call Report filers checked) but no product interest expense or averages; the owner chose not to use it, to keep a single data source. An entity that filed in the prior quarter but lacks an item is still dropped. Rows that use the fallback are flagged (`td_fallback_in_pf`) and listed in `ffiec/outputs/hybrid_td_fallback_v2.csv`.

*Validation tests for the rerun:*
1. 2012Q1 to 2016Q4: compare `TD_avg_t` with the RC-K time-deposit averages (`RCONA529 + RCONA514`), per bank, and the effect on `rate_ib`. This measures what the two-point approximation costs on the 16% time-deposit piece.
2. `rate_ib x (A_t / DEP)` against the origin rate on the same window (expected close, not equal; the gap is the base and the averaging).
3. Pro forma event set identical to the origin's.
4. `A_t` below quarter-end total deposits in every quarter (an interest-bearing base cannot exceed total).

**Correction to the pilot data (2026-11-14).** `RCON2604` (time deposits of $100,000 or more) is in the MDRM from 2010 but is not in the service output (0 of 4,601 filings); in 2010 to 2016 the same balance is `RCONJ473 + RCONJ474`. `items.py` now lists J473 and J474 in its place. The pilot never needed this item.

### 5.5 Data to pull for the hybrid denominator
`RCONJ473` and `RCONJ474` for 2011Q4 to 2016Q4: 3,306 filings, 229 entities, one call each, read only, through the same incremental puller. Every other item of the method is already in `ffiec/data/ffiec_items.csv`. Done 2026-11-14. For the reconciling series, `RCON6631`, `RCON6636`, `RCFN6631` and `RCFN6636` were back-filled into all 4,601 held filings for 2011Q4 to 2026Q3 on 2026-11-16 (no failures; ledger `ffiec/data/backfill_done.csv`).

---

## 6. Results

### 6.1 Hybrid-denominator build (2026-11-14, rebuilt 2026-11-16)
Code `ffiec/data_build/build_ffiec.py` (`hybrid_denominator`, `pro_forma_ib`, `build_hybrid`). Output `ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv`: 413 bank-quarters, 7 banks x 59 quarters, 2012Q1 to 2026Q3; no quarter dropped (`hybrid_dropped_quarters_v2.csv` is empty). The first build (2026-11-14) dropped 2012Q1 for First Horizon, Huntington, M&T, Old National and SouthState because their thrift predecessors have no 2011Q4 Call Report; the one-point fallback (5.4) restores it. The fallback is used by 14 predecessor entity-quarters, all in 2012Q1, and flags the 2012Q1 row of those five banks.

Series per bank-quarter:
- `rate_ib`, `rate_ib_pf`: 400 x interest expense / A_t, standalone and pro forma.
- `rate_nmd` (renamed `rate_nmd_rck` in 6.6): 400 x (RIAD4508 + RIAD0093) / (RCON3485 + RCONB563), exact RC-K averages, standalone.
- `rate_tran_pf`, `rate_sav_pf`, `rate_time_pf`: product rates, pro forma, with their averages (`tran_avg_pf`, `sav_avg_pf`, `time_avg_pf`) and annualised interest expense (`*_ie_ann_pf`).
- `rate_total_recon_pf`, `tot_avg_pf`: reconciling total-deposit rate and its base (section 6.4).
- `rate_total_pf`, `dep_avg_pf`: the total-deposit pro forma rate used before.
- `td_fallback_in_pf`: the row uses the one-point fallback.

Medians across the 413 rows: `rate_ib_pf` 0.40, transaction 0.40, savings 0.24, time 1.12, `rate_total_pf` 0.35, `rate_total_recon_pf` 0.31 (percent).

Pro forma: the unchanged FDIC fold, with the Mode A/B decision taken from the total-deposit build (made on total deposits, 1% test), so the event set is identical by construction (390 events). `A_t` is already an average and is not averaged again.

### 6.2 Build checks
| # | Check | Result |
| :-: | :-- | :-- |
| 1 | 2012Q1 to 2016Q4: two-point time-deposit average vs RC-K average (`RCONA529 + RCONA514`), 3,077 entity-quarters | Median difference +0.03%; 5th to 95th percentile -3.1% to +5.8%; 1.3% of rows differ by more than 25% |
| 2 | `rate_ib_pf` / `rate_total_pf` equals total-deposit average / `A_pf` | Identity holds to 1e-15; ratio 1.006 to 2.29, median 1.14 |
| 3 | Event set equals the total-deposit build | By construction (decisions reused); unit test shows the interest-bearing fold equals the FDIC `pro_forma` when the denominator is total deposits |
| 4 | `A_pf` below the total-deposit average | Holds in all 408 rows of the first build (ratio 0.44 to 0.99, median 0.88). This check does not detect the issue in 6.4 |
| 5 | Time-deposit continuity at the 2017Q1 definition switch (2016Q4 `6648 + J473 + J474` vs 2017Q1 `HK16 + HK17`), 91 entities | Median change -0.5%, aggregate -1.5%; no break |
| 6 | Product legs: transaction + savings + time averages and interest expense never exceed `A_pf` and total interest expense (remainder = foreign offices) | Holds in all 413 rows; domestic legs are at least 97.4% of the balance and 97.5% of the interest expense |
| 7 | Quarter-end identities, 4,601 filings 2011Q4 to 2026Q3: `RCON6631 + RCON6636 = RCON2200`; `RCFN6631 + RCFN6636 = RCFN2200` (357 filings) | Domestic: exact except 232 filings off by $1 thousand (rounding); foreign: exact |
| 8 | Reconciling base `tot_avg_pf` vs two-point total-deposit average `dep_avg_pf` | **Fails**: median +11.9%, range -26.7% to +43.8%; section 6.4 |

### 6.3 Known data points
- The interest-bearing ratio `A_pf` / total-deposit average has its largest moves in merger quarters and in the 2020 to 2021 deposit inflows: Huntington 2021Q2 (TCF; ratio 0.44), SouthState 2020Q2, Glacier 2021Q3, M&T 2025Q1, KeyBank 2022Q2. In Huntington's case the RC-K interest-bearing transaction and savings averages fall from $92 billion (2021Q1) to $50 billion (2021Q2) while total deposits rise 38%; a product reclassification is the likely cause and is not resolved. Treat `rate_ib_pf` for Huntington 2021Q2 to Q4 as a candidate outlier for the estimation phase.
- KeyBank `rate_tran_pf` is 7.1% to 9.5% in 2018Q4 to 2019Q3: `RIAD4508` reaches $34 million a quarter against a transaction-account average (`RCON3485`) of about $1.4 billion, while about $95 billion sits in the savings average. It returns to 0.5% to 0.8% from 2020Q2. Same cause as 6.4: the interest expense and the average of reclassified balances are reported in different products. The transaction/savings split is not reliable where a bank runs a reclassification program; their sum (`rate_nmd_rck`; on the RC base `rate_nmd_pf`) is not affected by this misallocation.
- Huntington 2021Q2 (above) coincides with the end of its reclassification program (6.4).
- Estimation has not been rerun on this series.

### 6.4 Reconciliation finding: RC-K savings averages include noninterest-bearing balances (2026-11-16)
Since `6631 + 6636 = 2200` holds at every quarter-end, `tot_avg_pf - dep_avg_pf` equals `A` minus the two-point average of quarter-end interest-bearing deposits. If `A` measured interest-bearing balances, the two bases would agree up to averaging noise. They do not:

| Bank | 2012 to 2019 | 2020 to 2021 | 2022 to 2026Q3 |
| :-- | --: | --: | --: |
| First Horizon | +14.2% | +14.9% | +19.0% |
| Glacier | +13.5% | +22.5% | -0.1% |
| Huntington | +7.2% | +12.2% | +2.5% |
| KeyBank | +23.0% | +27.5% | -0.1% |
| M&T | +21.6% | +29.2% | +20.8% |
| Old National | +9.9% | +7.9% | -0.4% |
| SouthState | +8.3% | +8.1% | -0.8% |

(median of `tot_avg_pf / dep_avg_pf - 1` per bank and period)

*Cause, from the data:* at the filing level (4,391 filings, 2012Q1 on), the excess of `RCON3485 + RCONB563` over quarter-end interest-bearing nonmaturity deposits (`RCON6636` less time deposits) has a correlation of 0.89 with a lower bound on noninterest-bearing balances held outside transaction accounts (`RCON6631 - RCON2215`, floored at 0). 1,146 of the 1,312 filings with an excess above 10% of deposits have `RCON6631 > RCON2215`. Huntington: excess $15.1 billion vs bound $15.5 billion (2018Q1), $23.3 billion vs $23.2 billion (2021Q1), both near zero from 2022. This is the pattern of Regulation D reclassification ("sweep") programs: noninterest-bearing demand balances are moved into savings/MMDA sub-accounts, which Schedule RC still reports as noninterest-bearing but the RC-K savings average includes. Most programs ended after the six-transfer limit was removed in 2020, which is where the gap closes for four banks; First Horizon and M&T still show it.

*Consequence:* `A_t` overstates the interest-bearing base, so `rate_ib_pf` (and `rate_sav_pf`) are understated, by a bank-specific amount that changes level around 2021 to 2022. That is a structural break in the dependent variable, created by reporting rather than pricing, inside the estimation window. The cause is inferred from the data; it has not been confirmed against bank disclosures or the RC-K instructions.

*Options (owner decision, O1):*
1. Interest-bearing base from Schedule RC: two-point average of `RCON6636 + RCFN6636`. Same source and timing as the NIB and total-deposit series, reconciles exactly, no break from reclassification; loses the RC-K daily averaging for nonmaturity deposits.
2. Keep the hybrid and subtract a two-point average of the estimated noninterest-bearing nontransaction balance from `RCONB563`. The balance is only bounded, not reported (`RCON6631 - RCON2215` is a lower bound), so this adds an estimate.
3. Keep the hybrid as is and treat the break as a limitation (dummy or shorter window in estimation).
4. Use the total-deposit rate `rate_total_pf` as the model variable (origin definition; unaffected).

**Decision (owner, 2026-11-25): option 1, Schedule RC interest-bearing base.** Built 2026-11-25 (section 6.6); 6.1 to 6.3 describe the hybrid build that preceded it. The sensitivity tests behind the choice are in 6.5.
- New base: `A_t` = two-point average of quarter-end `RCON6636 + RCFN6636`, replacing the hybrid (`RCON3485 + RCONB563 + RCFN3404` + two-point time deposits).
- `RCFN6636` missing counts as zero only when `RCFN2200` is absent or zero; otherwise the quarter is flagged.
- The prior-quarter rule and the 2012Q1 one-point fallback for the 14 thrift predecessors (P9) apply unchanged.
- Reason: RC-K savings averages include swept (Regulation D reclassification) noninterest-bearing balances, which Schedule RC reports as noninterest-bearing (6.4).

### 6.5 Denominator sensitivity tests (2026-11-25)
Run on the 413 pro forma bank-quarters of the 2026-11-16 build (commit `59b094b`). Reproduce with `python -I ffiec/sweep_sensitivity.py` (committed 2026-11-25, O6); it writes `ffiec/outputs/sweep_sensitivity/ffiec_deposit_rates_hybrid_v2.csv` and `report.txt`. On the current build it reproduces Tests B and D exactly; Test A medians move by at most 0.3 points and the 5th percentile of the lower-bound gap from -5.0% to -4.3%, because the noninterest-bearing average is now folded before averaging (6.6).

Four bases were compared:
- **Hybrid:** `A_t` as built in 6.1.
- **Hybrid minus lower bound:** the hybrid less a two-point average of `max(RCON6631 - RCON2215, 0)`, a lower bound on the swept noninterest-bearing balance.
- **Hybrid minus point estimate:** the hybrid less a two-point average of `RCON6631 - (RCON2215 - RCON3485)`.
- **RC 6636:** the two-point average of `RCON6636 + RCFN6636` (decision above).

**Test A. Reconciliation and rate gap.** "Gap" means the base plus the two-point noninterest-bearing average, compared with the two-point total-deposit average. "Rate vs RC base" is the median difference from the RC-base rate, per bank.

| Base | Gap, median (5th / 95th pct) | Rate vs RC base, median per bank | Note |
| :-- | :-: | :-: | :-- |
| Hybrid | +11.9% (-1.1% / +27.2%) | -3 to -12 bp | Largest gap: First Horizon 2023Q4, 77 bp |
| Hybrid minus lower bound | +0.8% (-5.0% / +15.8%) | -5 to +2 bp | First Horizon (+16.9%) and M&T (+8.3%) still off after 2022, where the bound is 0 |
| Hybrid minus point estimate | -0.9% (-9.4% / +6.0%) | -3 to +4 bp | Overshoots SouthState (-7% to -16%) and First Horizon 2020 to 2021 (-14%) |
| RC 6636 | 0.0% at every bank | 0 | Reconciles by identity (`6631 + 6636 = 2200`, 6.2 check 7) |

**Test B. Pass-through in the hiking cycles.** The rate rise on each base, as a percentage of the rise on the RC base:

| Base | 2015Q4 to 2019Q2 | 2021Q4 to 2023Q4 |
| :-- | :-: | :-: |
| Hybrid | 68% to 86% (all 7 banks) | About 100% at five banks; 76% to 77% at First Horizon and M&T |
| Hybrid minus lower bound | 86% to 103% | Not reported |
| Hybrid minus point estimate | 95% to 116% | Not reported |

On the hybrid base, the beta would be understated by about 15% to 30% in the first cycle but not in the second. This is the reporting-driven break of 6.4, seen in the quantity the model estimates.

**Test C. Cost of two-point averaging.** At the four banks with no reclassification after 2022 (Glacier, KeyBank, Old National, SouthState), the hybrid and RC bases differ by under 1%. Losing the RC-K daily averaging for non-maturity deposits costs little where sweeps are absent.

**Test D. KeyBank product mismatch (2017 to 2021).** Transaction accounts are 1.1% to 2.1% of the non-maturity average balance but 8% to 29% of non-maturity interest expense. The transaction rate is 9.5% in 2019Q2 and still 0.5% in 2021. This mismatch is between two interest-bearing products: interest is reported by account type, while the balance sits in the savings average after reclassification. It is separate from the swept noninterest-bearing issue in 6.4. At sweep banks the transaction/savings split is unreliable, but the sum of the two is consistent (P11).

**Not caused by sweeps.** SouthState 2025Q1 is off by -33 bp under every base. That quarter is the Independent Bank Group merger quarter (P8).

**Open with the owner:**
- Restricting the model to five banks: Huntington, Old National, KeyBank, M&T and First Horizon (O7).
- The product-line definitions (O3).

The RC-base rebuild follows those decisions.

### 6.6 Schedule RC base build (2026-11-25)
Code `ffiec/data_build/build_ffiec.py` (`hybrid_denominator`, `build_hybrid`). Output `ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv` (file name kept): 413 bank-quarters, 7 banks x 59 quarters, none dropped.

*Method.*
- Quarter-end interest-bearing deposits `IB_t = RCON6636 + RCFN6636` (`RCFN6636` missing counts as zero only when `RCFN2200` is absent or zero). Legs: non-maturity `RCON6636 - TD_t`, time `TD_t` (RC-E, 5.4), foreign `RCFN6636`; they add up to `IB_t`.
- Each quarter-end series is folded pro forma with the total-deposit build's Mode A/B decisions, then two-point averaged on the pro forma series: `A_pf = (IB_pf,t + IB_pf,t-1) / 2`. This is the origin's order for `DEP` (fold, then average), so the reconciling total equals `dep_avg_pf` and a merger quarter is averaged as in the origin. The former hybrid folded entity-level averages, which differed from the origin in merger quarters (up to -21%) and wherever an entity's history broke.
- 2012Q1 fallback: a predecessor whose first Call Report is 2012Q1 gets its own 2012Q1 quarter-end balances as its 2011Q4 value (balances only), so the pro forma 2011Q4 includes it. Same 14 entities as 5.4.
- Interest expense unchanged: domestic RI codes plus `RIAD4172`, merger-quarter interest pro rata as in the origin.

*Checks.*
| # | Check | Result |
| :-: | :-- | :-- |
| 9 | Reconciling base `tot_avg_pf` vs `dep_avg_pf` | Equal to 2e-5% in all 413 rows (after P12 was resolved; before, the five 2012Q1 fallback rows differed) |
| 10 | Legs non-maturity + time + foreign vs `A_pf`; their interest expense vs total | Equal to 1e-16 in all rows |
| 11 | `A_pf` / `dep_avg_pf`, outside the fallback rows | 0.568 to 0.863, median 0.729; never above 1 |
| 12 | Huntington around TCF (2021Q2) | `A_pf` / `dep_avg_pf` 0.685 (2021Q1), 0.671 (2021Q2), 0.668 (2021Q3); the hybrid fell to 0.436. The 6.3 Huntington outlier was the reclassification effect and is gone |
| 13 | Tests | 25 pass (`ffiec/tests`), including the RC base split, missing-data rules and fallback |

*Effect.* `rate_ib_pf` on the RC base minus the hybrid rate, median per bank: +2.8 bp (Old National) to +8.8 bp (First Horizon); largest +77 bp (First Horizon 2023Q4). Medians across the 413 rows: `rate_ib_pf` 0.47 (hybrid 0.40), `rate_nmd_pf` 0.30, `rate_time_pf` 1.11, `rate_total_pf` and `rate_total_recon_pf` 0.35.

*Columns.* `A_pf`, `rate_ib_pf` (RC base, model candidate); `nmd_*`, `time_*`, `for_*` (`*_avg_pf`, `*_ie_ann_pf`, `rate_*_pf`; `rate_for_pf` is empty where the bank has no foreign offices); `tot_avg_pf`, `rate_total_recon_pf`; reference only (RC-K, affected by P10/P11): `A_hyb_pf`, `rate_ib_hyb_pf`, `tran_*`, `sav_*`, `rate_nmd_rck` (renamed from `rate_nmd`).

### 6.7 Product lines and sources (scope of five banks under O7)
*Swept balances.* No public bank-level source reports Regulation D reclassification ("reserve sweep") volumes. They were reported on the FR 2900 (confidential). The Call Report sweep items `RCONMT87` to `RCONMT95` (MDRM, from 2021-09-30) are third-party sweep deposits under the brokered-deposit rule, not reclassification sweeps. Schedule RC does not report the swept volume either; it classifies swept balances as noninterest-bearing (`RCON6631`), which is why the RC base removes them without needing the volume. The volume can only be bounded (`RCON6631 - RCON2215`, 6.5).

*Product lines for Huntington, Old National, KeyBank, M&T and First Horizon* (codes checked in the MDRM 2026-11-25; all FFIEC 031/041, Call Report source, 2012Q1 to 2026Q3):
| Line | Interest expense (Schedule RI) | Balance (quarter-end, two-point averaged) | Share of `A_pf`, median | Status |
| :-- | :-- | :-- | :-: | :-- |
| Interest-bearing non-maturity (interest-bearing transaction accounts + savings incl. MMDA) | `RIAD4508 + RIAD0093` | `RCON6636` (RC) less time deposits; the model rate uses the end-of-quarter balance (6.10) | 80% to 86% | Model line; `rate_nmd_eoq_pf` (`rate_nmd_pf` two-point reference) |
| Time deposits | `RIADA517 + RIADA518` to 2016; `RIADHK03 + RIADHK04` from 2017 | `RCON6648 + RCONJ473 + RCONJ474` to 2016; `RCONHK16 + RCONHK17` from 2017 (RC-E); the model rate uses the end-of-quarter balance (6.9) | 14% to 20% | Model line; `rate_time_eoq_pf` (`rate_time_pf` two-point reference) |
| Foreign offices | `RIAD4172` | `RCFN6636` (RC) | 0% to 2.9%; none after 2016Q4 (Huntington), 2015Q4 (KeyBank), 2021Q2 (M&T); never for First Horizon, Old National | Kept inside `rate_ib_pf`; not a model line |
| Noninterest-bearing | none (zero rate) | `RCON6631 + RCFN6631` (RC) | outside `A_pf` | Mix and weights only |

*Splits that are not available on a consistent basis:*
- Transaction vs savings: interest is split (`RIAD4508`, `RIAD0093`) but the balances that match it are not. RC-K averages (`RCON3485`, `RCONB563`) carry the reclassification effects (P10, P11); RC-E quarter-ends (`RCON2215` total transaction accounts, `RCON6810` MMDA, `RCON0352` other savings) are not split into interest-bearing and noninterest-bearing.
- MMDA vs other savings: balances exist (`RCON6810`, `RCON0352`), interest does not (`RIAD0093` covers both).
- Time deposits by size: the size bands change in 2017 ($100,000 to $250,000), so no sub-split is consistent over the window.
- Brokered deposits: balance only (`RCON2365`), no interest.

### 6.8 Year-to-date breaks in quarterly interest expense (2026-11-25)
*Finding.* Schedule RI is reported year to date; quarterly flows are derived as YTD_t - YTD_t-1 (`ffiec_pull.to_quarterly`). Two reporting events break that subtraction:
- **Restart (push-down accounting).** When a bank is acquired and applies push-down accounting, its YTD income restarts at the acquisition date, so the derived quarter is too small or negative. First Niagara 2016Q3 (cert 16004): YTD deposit interest $38.7M at 2016Q2, $9.7M at 2016Q3, giving -$29.1M for the quarter (time deposits -$15.8M), which pulled KeyBank's pro forma 2016Q3 time rate to 0.14% and non-maturity rate to 0.04%.
- **Restatement (combination under common control).** A merger of affiliates is reported from the start of the year, so the survivor's merger-quarter YTD includes the affiliates' earlier quarters, which the pro forma already counts from the affiliates' own filings. Bremer Bank NA (cert 12923, an Old National predecessor) absorbed eight affiliate charters on 2014-10-01; its 2014Q4 deposit interest was $14.0M against $3.6M expected, the excess matching the affiliates' $10.3M of Q1-Q3 interest. Old National's pro forma 2014Q4 time rate was 1.30% (0.81% and 0.72% either side).

*Repair* (`build_ffiec.repair_ytd_breaks`, applied to the cert-level frame before both builds; every repair listed in `ffiec/outputs/ytd_repairs_v2.csv`):
- Restart: detected where derived domestic deposit interest is negative. Each product's interest (`RIAD4508`, `RIAD0093`, time, `RIAD4172`) is set to the entity's previous-quarter interest scaled by the change in that product's balance (previous-quarter rate carried forward); with no previous quarter or balance it is set missing. 23 entity-quarters, 13 from 2011Q4 (12 carried forward, 1 set missing).
- Restatement: detected for a merger quarter after Q1 when the survivor's rate on quarter-end interest-bearing balances is at least 1.25 times both the combined rate of the quarter before and its own rate of the quarter after, and removing the predecessors' YTD brings it back between them. The predecessors' YTD to the prior quarter, plus the pro-rata part the pro forma adds for the pre-merger days, is subtracted per product. 5 events, all from 2012 (Glacier's charter consolidation 2012Q2, Bremer 2014Q4, three small predecessors). A test on interest expense alone was rejected: it also flagged People's United 2019Q2, an April purchase where one quarter of rate drift looks like one quarter of restated YTD.
- A restart that leaves the derived quarter positive but too small is not detected.

*Effect.* KeyBank 2016Q3: time 0.14% to 1.09%, non-maturity 0.04% to 0.18%. Old National 2014Q4: time 1.30% to 0.74%. Glacier 2012Q2: `rate_ib_pf` 0.84% to 0.58%. 20 bank-quarters change across the 7 banks, none after 2016Q4; 413 rows, events and modes unchanged; `tot_avg_pf` still equals `dep_avg_pf`. BankFind reconciliation in window improves (4.3).

*Not repaired: M&T 2022Q2 and 2022Q3 time deposits (0.087%, 0.085%).* M&T's own Call Report time-deposit interest is $1.2M and $1.1M on $5.0 to $5.5 billion, and its 10-Q reports the same figures ($1,227 thousand and $1,124 thousand), so this is reported data, not a pipeline error. The likely cause is amortization of the fair-value premium on the time deposits assumed from People's United (2022-04-01), which lowers reported interest expense; the 10-Q note was not checked. Huntington 2021Q3 (negative time-deposit interest of $0.8M after TCF) has the same signature but no visible dip. See P13.

### 6.9 Time-deposit denominator: end-of-quarter balance (D7, owner decision 2026-11-26)
*Why.* No reported time-deposit average exists after 2016 (RC-K items `RCONA529`/`RCONA514` ended 2016Q4; the FR Y-9C has quarter-end time deposits and their interest but no average). The two-point average misstates the average in quarters of fast intra-quarter growth: First Horizon 2023Q3 5.22% (First Horizon's own period-end balances imply 4.42%) and KeyBank 2023Q2 4.68%, which fell to 4.14% in Q3 while the Fed was still raising rates.

*Test (2026-11-26, scratch, not committed).* The pro forma time legs were rebuilt with the production code (two-point reproduced `rate_time_pf` exactly) and three denominators compared:

| Denominator | Quarters changed (7 banks) | Spikes above 0.3 points, 5 banks | First Horizon 2023 Q2/Q3/Q4 | KeyBank 2023 Q1/Q2/Q3 | First Horizon 2024 Q2/Q3/Q4 |
| :-- | --: | --: | :-- | :-- | :-- |
| Two-point average (previous) | 0 | 25 | 4.42 / 5.22 / 4.25 | 4.20 / 4.68 / 4.14 | 4.45 / 5.12 / 4.16 |
| End balance where growth > 10% | 39 | 15 | 3.55 / 4.39 / 4.25 | 3.32 / 3.95 / 4.14 | 4.45 / 4.65 / 4.16 |
| End balance always (chosen) | 413 | 11 | 3.55 / 4.39 / 4.45 | 3.32 / 3.95 / 4.15 | 4.43 / 4.65 / 4.37 |

A spike is a quarter more than 0.3 points away from the mean of the quarters either side; several remaining spikes are genuine turns of the 2022 to 2023 cycle. Thresholds of 10% to 35% gave the same 2023 results.

*Decision D7.* The owner's words were "End-of-quarter" and "use end balance always", chosen over the recommendation to keep the two-point average and flag outliers. The time-deposit model uses `rate_time_eoq_pf`.

*Implementation.* `rate_time_eoq_pf = 400 x time-deposit interest / time_eoq_pf`, where `time_eoq_pf` is the pro forma end-of-quarter time-deposit balance (`build_ffiec.END_BALANCE_LEGS`). `rate_time_pf` and `time_avg_pf` (two-point) are kept as the reference, so non-maturity + time + foreign still tile `A_pf`. `rate_ib_pf`, `rate_nmd_pf`, `rate_total_pf` and the reconciling series are unchanged; neither interest-bearing series uses the time-deposit denominator on its own. `rate_time_eoq_pf` minus `rate_time_pf`: median +0.008 points (5th to 95th percentile -0.25 to +0.12). Output after the change: 413 rows x 38 columns.

*Known weaknesses (P15).* Huntington 2026Q2 (time deposits +32%) becomes 3.10%, between 3.87% and 3.06%, which would be an artefact if the growth came late in the quarter; First Horizon 2024Q3 becomes 4.65% where its own balances imply 4.91%; KeyBank 2023Q1 (3.32%) depends on whether its CD growth came before or after March. M&T 2022Q2 to Q3 (P13) is unchanged at about 0.09%.

### 6.10 Non-maturity denominator: end-of-quarter balance (D8, owner decision 2026-11-26)
*Decision.* The owner asked for the end-of-quarter adjustment to be applied to the non-maturity rate as well and adopted as the default if its impact was moderate. It is (below), so both product models use end-of-quarter denominators: `rate_nmd_eoq_pf` (D8) and `rate_time_eoq_pf` (D7).

*Implementation.* `rate_nmd_eoq_pf = 400 x (RIAD4508 + RIAD0093) / nmd_eoq_pf`, where `nmd_eoq_pf` is the pro forma end-of-quarter interest-bearing non-maturity balance (`RCON6636` less time deposits). `rate_nmd_pf` and `nmd_avg_pf` (two-point) are kept as reference; no other column changed. Output: 413 rows x 40 columns.

*Impact, five banks, 2012Q1 to 2026Q3* (end-of-quarter minus two-point; "slope" is the OLS slope of the rate level on FFT, an illustration only, not the ECM long-run beta):

| Leg | Bank | Median (bp) | 95th pct of abs (bp) | Max abs (bp) | Corr. of quarterly changes | Spikes > 0.3 pt (2-pt / EOQ) | Slope 2-pt / EOQ |
| :-- | :-- | --: | --: | --: | --: | :-: | :-: |
| Non-maturity | First Horizon | -0.1 | 4.0 | 11.2 | 0.989 | 1 / 1 | 0.525 / 0.523 |
| Non-maturity | Huntington | -0.2 | 4.0 | 5.2 | 0.990 | 0 / 0 | 0.464 / 0.461 |
| Non-maturity | KeyBank | -0.2 | 2.0 | 3.8 | 0.996 | 0 / 0 | 0.418 / 0.415 |
| Non-maturity | M&T | -0.2 | 3.3 | 9.0 | 0.984 | 0 / 0 | 0.424 / 0.421 |
| Non-maturity | Old National | -0.1 | 2.1 | 3.4 | 0.997 | 0 / 0 | 0.415 / 0.414 |
| Time | First Horizon | +0.8 | 40.4 | 87.4 | 0.880 | 8 / 4 | 0.679 / 0.641 |
| Time | Huntington | +0.9 | 40.0 | 60.5 | 0.875 | 3 / 2 | 0.696 / 0.669 |
| Time | KeyBank | +1.3 | 27.7 | 87.5 | 0.938 | 6 / 2 | 0.654 / 0.621 |
| Time | M&T | +1.2 | 32.4 | 93.9 | 0.951 | 4 / 2 | 0.630 / 0.603 |
| Time | Old National | +0.5 | 25.1 | 41.4 | 0.959 | 4 / 1 | 0.675 / 0.645 |

Non-maturity balances move slowly, so the two denominators nearly coincide; the largest difference is First Horizon 2023Q2 (2.22% to 2.11%). For time deposits the change is larger and lowers the static slope by about 0.03 at every bank. The aggregate rate `rate_ib_pf` and the total-deposit rate stay on the two-point average.

### 6.11 Cumulative beta and comparison with the High-Level betas (2026-11-26, provisional)
*Definition* (`ffiec/cumulative_beta.py`, output `ffiec/outputs/cumulative_beta_v2.csv`). Weights are the sample-average pro forma balances, 2012Q1 to 2026Q3:
- `cum_beta_ib = (B_nmd b_nmd + B_time b_time) / (B_nmd + B_time)`: beta of interest-bearing deposits.
- `cum_beta_total = (B_nmd b_nmd + B_time b_time) / B_total`: beta of total deposits, with noninterest-bearing deposits (and foreign offices, at most 2.9%) at beta 0. This is the comparable figure: the High-Level beta is the beta of the total-deposit rate, whose base includes noninterest-bearing deposits.

*Segment betas are provisional.* The ten segment ECMs are not yet estimated, so `b_nmd` and `b_time` are the slope of an OLS regression of the segment rate on a constant and FFT (the long-run step of the Engle-Granger form, no dynamics). The script takes the ECM long-run betas with `--segment-betas` when they exist. High-Level betas: champion long-run betas from the High-Level document rev 2.1, section 1.3 (`ffiec/reference/high_level_champion_betas.csv`).

| Bank | b_nmd | b_time | NMD / time / NIB share of total deposits | cum_beta_ib | cum_beta_total | Static total-rate beta (Call Report / BankFind) | High-Level beta | High-Level minus cum_beta_total |
| :-- | --: | --: | :-: | --: | --: | :-: | --: | --: |
| First Horizon | 0.523 | 0.641 | 60% / 11% / 28% | 0.542 | 0.389 | 0.391 / 0.374 | 0.477 | +0.088 |
| Huntington | 0.461 | 0.669 | 64% / 13% / 23% | 0.496 | 0.380 | 0.382 / 0.366 | 0.463 | +0.083 |
| KeyBank | 0.415 | 0.621 | 64% / 9% / 27% | 0.440 | 0.322 | 0.356 / 0.341 | 0.402 | +0.080 |
| M&T | 0.421 | 0.603 | 57% / 11% / 32% | 0.450 | 0.308 | 0.304 / 0.290 | 0.402 | +0.094 |
| Old National | 0.414 | 0.645 | 60% / 15% / 25% | 0.460 | 0.346 | 0.337 / 0.317 | 0.419 | +0.073 |

*Reading.*
- Aggregation holds: on the same estimator, the segments weighted over total deposits reproduce the beta of the total-deposit rate within 0.01 at four banks and 0.034 at KeyBank (where the time-deposit share moved most with the rate cycle).
- Source and sample are not the cause of the gap: the static beta of the BankFind rate (2011Q1 to 2026Q2) and of the Call Report total rate (2012Q1 to 2026Q3) differ by at most 0.02.
- The gap of +0.07 to +0.09 to the High-Level beta is the estimator: ECM long-run beta (with lags and deterministic terms) against a static regression. The like-for-like comparison is the High-Level beta against `cum_beta_total` built from the segment ECM betas; it is to be rerun when those are estimated.
- On interest-bearing deposits only, time deposits pass through more than NMD at every bank (0.60 to 0.67 against 0.41 to 0.52, provisional).

---

## 7. Limitations and Assumptions

| # | Limitation | Impact |
| :-: | :-- | :-: |
| P1 | The origin limitations L1 to L22 carry over unchanged unless restated here, with L1 worse: 59 rather than 62 quarters | High |
| P2 | Quarters before 2012 are not reliable (missing thrift predecessors) and are excluded; the Call Report cannot be filled from BankFind without mixing sources | Medium |
| P3 | 592+ filings returned no data; each was checked against the service's filer list for that quarter and none is listed (non-filers, not outages) | Low |
| P4 | Wilmington Trust NA (cert 33911) and Federal Trust Bank (cert 32580) have no Call Report; their deposits are not in the pro forma, as for the origin 4 Mode B events | Low |
| P5 | Partial deposit transfers carry interest expense in proportion to deposits (origin L20, L21) | Low |
| P6 | The Call Report series is the reference where BankFind's quarterly interest expense does not tie to its year-to-date (63 bank-quarters) | Low |
| P7 | The hybrid denominator mixes RC-K quarterly averages (transaction and savings accounts) with a two-point average of quarter-end time deposits (RC-E). The two-point average matches the RC-K time-deposit average in 2012 to 2016 (section 6.2, test 1) but is not an exact RC-K average | Medium |
| P8 | In a merger quarter and in quarters of large deposit inflows the RC-K averages and the two-point average move at different speeds; the interest-bearing denominator shows its largest jumps there (section 6.3) | Medium |
| P9 | 2012Q1 time-deposit and NIB averages of the 14 thrift predecessors are one-point (2012Q1 quarter-end), not two-point; 5 bank-quarters flagged | Low |
| P10 | RC-K savings averages include noninterest-bearing reclassified balances; the former hybrid `A_t` overstated the interest-bearing base by up to about 30% to 2021, with a level shift in 2021 to 2022 (section 6.4). Resolved by the Schedule RC base, built 2026-11-25 (6.6). Still applies to the RC-K reference columns (`A_hyb_pf`, `rate_ib_hyb_pf`, `rate_tran_pf`, `rate_sav_pf`, `rate_nmd_rck`) | Resolved for the model series |
| P11 | Transaction/savings product split unreliable during reclassification programs (KeyBank 2017 to 2021, sections 6.3, 6.5 test D); no reporting-consistent split exists (6.7), so the model's non-maturity line is the combined interest-bearing non-maturity deposits | Medium |
| P13 | Purchase-accounting effects in reported interest expense are kept as reported: M&T 2022Q2 to Q3 time-deposit rate 0.09% (People's United), likely fair-value premium amortization (6.8). Treat as candidate outliers (dummy) in the time-deposit model | Medium |
| P15 | The time-deposit model rate `rate_time_eoq_pf` divides by the pro forma end-of-quarter balance (6.9, D7). It is exact only when balances are flat within the quarter: it understates the rate when balances grew late in a quarter (candidate: Huntington 2026Q2, 3.10%) and overstates it when balances fell late (2020 to 2021 run-off). The time leg in `A_pf` stays a two-point average, so the model's time rate is not on the same base as the interest-bearing rate | Medium |
| P14 | YTD repairs (6.8) change 18 entity-quarters from 2011Q4: 12 previous-rate carry-forwards, 1 set missing (cert 5950, 2011Q4, outside the sample) and 5 restatement corrections; a restart that leaves a positive but understated quarter is not detected | Low |
| P12 | `rate_total_pf` in 2012Q1 had no 2011Q4 balance for the 14 thrift predecessors (two-point average understated, rate overstated: M&T +13.7 bp, SouthState +5.7 bp, Old National +2.2 bp, First Horizon +0.9 bp, Huntington +0.8 bp). Resolved 2026-11-25 (owner decision): the total-deposit build applies the same one-point fallback (predecessor's 2011Q4 `DEP` = its own 2012Q1 `DEP`, interest expense not filled). Effect: those five 2012Q1 rates now match the BankFind origin within 0.005 points except SouthState (0.014, was 0.071); the 2011Q4 rows of the five banks (outside the sample) drop from the total-deposit outputs because their pro forma interest expense is incomplete (525 to 520 rows). Event set and Mode A/B decisions unchanged | Resolved |

---

## 8. Open Issues and Planned Developments

| # | Item | Status |
| :-: | :-- | :-- |
| O1 | Aggregate model variable (`rate_ib_pf` vs `rate_total_pf`) | Closed 2026-11-26: no aggregate model (D9). `rate_ib_pf` had been assumed by the build session and was never confirmed; both series stay in the file for reconciliation only |
| O2 | COVID liquidity dummy retest on the Prod-Lvl series | Deferred to model development |
| O3 | Product-level betas (now the model scope, D9) | Product lines set out in 6.7 (interest-bearing non-maturity, time; foreign and noninterest-bearing as non-modelled legs). Model rates final 2026-11-26: `rate_nmd_eoq_pf` (D8) and `rate_time_eoq_pf` (D7), five banks (O7), 2012Q1 to 2026Q3 | Data final; models in progress (Prod-Lvl session) |
| O4 | `ffiec/reference/CSV_ATTRIBUTES_*.zip` (NIC attributes) are not committed; keep or delete | Owner |
| O5 | Independent validation, model inventory registration, monitoring plan | Not started |
| O6 | Commit the sensitivity script and its outputs so section 6.5 can be reproduced | Done 2026-11-25 (`ffiec/sweep_sensitivity.py`) |
| O7 | Scope: restrict the model to five banks (Huntington, Old National, KeyBank, M&T, First Horizon) | Decided 2026-11-26 (owner: "Five banks"); filter applied at run time, data file keeps all 7 (1.2) |

---

## 9. Implementation

- Environment: Python; the Call Report pull needs FFIEC CDR credentials in the keyring (`ffiec_pws`: `token`, `user`) or `FFIEC_USER` and `FFIEC_TOKEN`.
- Pilot run: `python ffiec/data_build/ffiec_pull.py` then `build_ffiec.py`, `reconcile.py`, `materiality.py`; `pytest -q --tb=line`.
- Tests and checks: `ffiec/tests/`; `verify_isolation.py`.

## 10. Governance

| Item | Status |
| :-- | :-- |
| Model owner | Shivam Panda |
| Model inventory registration | Not registered |
| Independent validation | Not performed |
| Ongoing monitoring | Not defined. Proposed: quarterly refresh after each Call Report cycle, with the origin backtest limits |
| Change management | Git (`Panda5130/Prod-Lvl-Deposit-Beta`); source changes recorded in section 5 |
