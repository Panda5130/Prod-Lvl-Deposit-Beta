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
| Development status | Draft; data source switch approved, estimation not yet rerun |
| Validation status | Not validated |
| Model tier / materiality | Not yet assigned |
| Developer / owner | Shivam Panda (GitHub: Panda5130) |
| Code repository | `Panda5130/Prod-Lvl-Deposit-Beta` |
| Origin model | High-Level Deposit Beta, repository `Panda5130/Deposit-Beta` (FDIC BankFind data), document "WIP Regional Banking Deposit Beta Analyses", version 2.0 (WIP), last synced origin commit `ea95980` |
| Document date | 2026-11-16 |
| Data period | 2012Q1 to 2026Q3 (59 quarters per bank, section 6.1; about 56 after lags and differencing) |

### 0.1 Naming
- **High-Level Deposit Beta** (origin repository): bank-level deposit interest expense and total deposits from FDIC BankFind. Kept as the benchmark.
- **Prod-Lvl Deposit Beta** (this repository): the same models fed by FFIEC Call Report data, the granular source that later phases need. Earlier working documents used "FDIC" and "FFIEC" for the two sources while the choice was open. The choice is made, so this document uses the two repository names.

### 0.2 Revision History
| Version | Date | Description | Validation |
| :--- | :--- | :--- | :--- |
| 0.5 (draft) | 2026-11-16 | One-point 2011Q4 fallback for thrift predecessors (all 7 banks now 59 quarters); pro forma product rates (transaction, savings including MMDA, time); reconciling total-deposit series built after the `6631`/`6636` pull; finding: RC-K savings averages include noninterest-bearing reclassified balances (section 6.4), denominator decision reopened (O1) | Quarter-end identities `6631 + 6636 = 2200` hold; reconciliation fails by a median 13% to 2021, section 6.4 |
| 0.4 (draft) | 2026-11-14 | Hybrid denominator built and validated on the Call Report data (J473/J474 re-pull complete); results of the build in section 6; P7 and O1 updated | Four build checks in section 6.2; estimation not yet rerun |
| 0.3 (draft) | 2026-11-14 | Hybrid denominator finalized (section 5.4): items, formulas, pro forma, missing-data and validation rules; time-deposit item correction (J473 + J474 replace RCON2604); re-pull specified (5.5) | Item coverage checked on 4,601 entity-quarters; build not yet run |
| 0.2 (draft) | 2026-11-14 | Owner approved the RC-K average-balance denominator; feasibility check found no RC-K time-deposit average from 2017Q1 and no noninterest-bearing average (section 5.4); fallback options recorded, build pending owner choice | MDRM search; two live filings inspected |
| 0.1 (draft) | 2026-11-14 | First SR 11-7 draft for Prod-Lvl. Source switch from BankFind to Call Reports approved by the owner; sample starts at 2012Q1. Built from the pilot record (section 4) | Pilot reconciliation (section 4.3); no model rerun yet |

---

## 1. Executive Summary

### 1.1 Purpose
Estimate the deposit beta of seven U.S. regional banks (the long-run share of a federal funds rate change that passes through to the bank's deposit rate) and the speed of adjustment toward it, using FFIEC Call Report data. Each bank is modeled separately.

### 1.2 Banks in Scope
First Horizon Bank (cert 4977), Glacier Bank (30788), Huntington National Bank (6560), KeyBank National Association (17534), Manufacturers and Traders Trust Company (588), Old National Bank (3832), SouthState Bank (33555). Merger predecessors are included pro forma (section 4.2).

### 1.3 What Changes From the Origin Model
| Item | Origin (High-Level) | Prod-Lvl |
| :-- | :-- | :-- |
| Source of deposits and interest expense | FDIC BankFind Financials API | FFIEC Call Reports, CDR Public Web Service |
| Sample | 2011Q1 to 2026Q2 (62 quarters) | 2012Q1 to 2026Q2 (58 quarters) |
| Dependent variable | `rate_pf_clean` (two-point average denominator) | Numerator from Call Report items; denominator moves to RC-K average balances (approved), form pending (section 5.4) |
| Regressor, model form, selection, backtests | As origin | Unchanged; rerun on the new data |
| Merger events | FDIC `/history` plus 7 NIC-found transfers | Same event list (read from the origin repository's shared file), cross-checked to NIC Transformations |

Results of the rerun are not yet available. This document will carry them in section 6 once the rerun is complete.

---

## 2. Model Purpose, Scope and Intended Use

### 2.1 Business Purpose
Deposit betas feed interest-rate risk measurement (NII and EVE sensitivity), deposit pricing analysis, funds-transfer pricing and peer benchmarking. The Call Report source also carries deposit detail by account type (Schedule RC-E and RC-K) that allows product-level betas as a later development.

### 2.2 Intended Use (once validated)
- Peer benchmarking of long-run deposit pass-through.
- Scenario projection of deposit rates conditional on a federal funds rate path, up to 8 quarters.

### 2.3 Uses Outside Scope
- Production pricing or regulatory capital decisions before validation.
- Product-level betas: not in this version (planned as a separate development, section 8).
- Horizons beyond 8 quarters or rate regimes outside the sample (for example negative rates).

### 2.4 Model Output
Per bank: estimated one-step ECM (speed of adjustment, long-run beta with delta-method standard errors), in-sample and rolling-origin forecast error, and long-run beta stability.

---

## 3. Model Overview

### 3.1 Variables
| Role | Variable | Definition | Source |
| :-- | :-- | :-- | :-- |
| Dependent (y) | `rate_pf_clean` | 400 x quarterly deposit interest expense / average of current and prior quarter-end total deposits, pro forma for mergers | FFIEC Call Reports |
| Regressor (x) | `FFT` | Quarterly average of the monthly effective federal funds rate | FRED `FEDFUNDS` |

Call Report items (fixed in `ffiec/data_build/items.py`, each checked against the current MDRM): total deposits `RCFD2200` if present, else `RCON2200 + RCFN2200` (domestic plus foreign offices); deposit interest expense from the Schedule RI domestic codes plus `RIAD4172` (foreign offices). Call Report income items are year to date and are converted to quarterly values; dollars are divided by 1,000.

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
- Window: savings institutions filed Thrift Financial Reports to the OTS until 2011 and Call Reports from March 2012, so quarters before 2012 lack some predecessors. The reference window is 2012Q1 onward (decision 2026-11-13). Earlier quarters are kept in the outputs for reference only. Inside the window, 25 of 406 bank-quarters differ from the origin pro forma rate by more than 0.005 points (median 0.000, 95th percentile 0.0074, maximum 0.160); the differences trace to the two documented origin-side items (predecessors without Call Reports: Wilmington Trust NA, Federal Trust Bank; BankFind quarterly interest expense).
- Evidence files: `ffiec/outputs/reconciliation_summary.csv`, `reconciliation_quarters.csv`, `nic_event_differences.csv`, `missing_filings_check.csv`.

### 4.4 Sample
2012Q1 to 2026Q3: 59 quarters per bank, about 56 usable after lags and differencing. This is shorter than the origin sample (62), which lowers test power further (limitation L1). Seven-bank results from the two sources are compared on the common window before any conclusion about the change in estimates.

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
- **Second series: `rate_nmd = 400 x (RIAD4508 + RIAD0093) / NMD_ib`**, domestic interest-bearing non-maturity deposits, exact RC-K averages in all quarters.
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
- `rate_nmd`: 400 x (RIAD4508 + RIAD0093) / (RCON3485 + RCONB563), exact RC-K averages, standalone.
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
- KeyBank `rate_tran_pf` is 7.1% to 9.5% in 2018Q4 to 2019Q3: `RIAD4508` reaches $34 million a quarter against a transaction-account average (`RCON3485`) of about $1.4 billion, while about $95 billion sits in the savings average. It returns to 0.5% to 0.8% from 2020Q2. Same cause as 6.4: the interest expense and the average of reclassified balances are reported in different products. The transaction/savings split is not reliable where a bank runs a reclassification program; their sum (`rate_nmd`) is not affected by this misallocation.
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
| P10 | RC-K savings averages include noninterest-bearing reclassified balances; `A_t` overstates the interest-bearing base by up to about 30% to 2021 and shifts level in 2021 to 2022 (section 6.4). Open under O1 | High |
| P11 | Transaction/savings product split unreliable during reclassification programs (KeyBank 2018 to 2019, section 6.3) | Medium |

---

## 8. Open Issues and Planned Developments

| # | Item | Status |
| :-: | :-- | :-- |
| O1 | Average-balance denominator: hybrid built 2026-11-14; reconciling series built 2026-11-16 and fails (section 6.4, P10). Owner to choose among the options in 6.4 and confirm the model variable (built as `rate_ib_pf`; `rate_total_pf` in the same file) | Open, blocks estimation |
| O2 | COVID liquidity dummy retest on the Prod-Lvl series | Deferred to model development |
| O3 | Product-level betas (savings and money market, time, transaction) | Product rates built (6.1); split reliability open (P11); models not started |
| O4 | `ffiec/reference/CSV_ATTRIBUTES_*.zip` (NIC attributes) are not committed; keep or delete | Owner |
| O5 | Independent validation, model inventory registration, monitoring plan | Not started |

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
