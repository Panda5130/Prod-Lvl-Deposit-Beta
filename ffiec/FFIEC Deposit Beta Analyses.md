# FFIEC Deposit Beta Analyses

**Model v2.0 (FFIEC Call Report)**, successor to Model v1.0 (FDIC BankFind). Model versions and document revisions are separate; this document has its own revision numbers (table in section 6).
Last synced FDIC commit: `057d5dd` (2026-11-12).

This document is the SR 11-7 record for the FFIEC model. It never edits `WIP Regional Banking Deposit Beta Analyses.md`,
which is the FDIC 1.0 document and arrives unchanged with each sync.

## 1. Status
- Phase 1 (pilot): FFIEC pull, merger-adjusted rebuild, reconciliation with BankFind, materiality. **Does not feed the model.**
- Phase 2 (source switch) and Phase 3 (product-level betas): not started; each needs its own plan and approval.

## 2. Data source
- FFIEC CDR Public Web Service, Call Reports for the 7 target banks and their merger predecessors, by RSSD ID.
- FDIC certificate to RSSD via the `FED_RSSD` field of the FDIC institutions API.
- Item codes are fixed in `ffiec/data_build/items.py`, each checked against the current MDRM dictionary.
- Raw responses are hashed; amended filings are detected by hash change and logged in `ffiec/data/amendments.csv`.

## 3. Merger adjustment
Unchanged FDIC logic (`data_build/build_dataset.py`, imported not edited). Events: FDIC `/history` (primary),
cross-checked against NIC Transformations (`ffiec/outputs/nic_event_differences.csv`).

## 4. Pilot results
Pull (2026-11-13): 8,791 filings, 100,748 item records, 0 amendments; 536 filings (53 entities, all 2007Q4 to 2013Q3) returned HTTP 500 and are listed in `ffiec/data/missing_filings.csv` (mostly predecessors before they existed; to be confirmed per entity). Build: 525 rows, 358 events, all validation checks pass.
Reconciliation with BankFind (`ffiec/outputs/reconciliation_summary.csv`): 279 quarters flagged, all 272 "differs" and 7 "ffiec_only" (2026Q3, not yet in BankFind). Deposit totals differ by a median of about $0.3bn in 2010 to 2015, under $0.2m from 2016 to 2020; interest expense and rate differences are about zero. Cause of the early-year deposit gap not yet established.
Materiality (`ffiec/outputs/materiality_summary.csv`): RC-K interest-bearing rate versus the 2-point rate, 2008 to 2016 only (36 quarters per bank). Correlations 0.97 to 1.00; level gap (RC-K minus 2-point) from -0.001 to 0.121 points, largest for SouthState (0.121) and First Horizon (0.084).
NIC cross-check: not run (NIC download blocked; needs a CSV via `--file`).

## 5. Open items
- Endpoint, header names and XBRL element naming confirmed on the first authenticated pull (SIS611 v1.10); units confirmed (dollars, divided by 1,000).
- Explain the 2010 to 2015 deposit-total differences versus BankFind; review `missing_filings.csv` for any entity that should have filed.
- NIC Transformations cross-check not yet run.
- No MDRM code found for RC-K time-deposit averages from 2017 on, nor for the RC-K noninterest-bearing average.
- Unit check (dollars vs $ thousands) to be confirmed by the reconciliation.

## 6. Document revision history
| Date | Revision | Change | Validation |
| :-- | :-- | :-- | :-- |
| 2026-11-12 | 1 | Seeded from FDIC Model v1.0, document revision 2.0 (WIP), commit 057d5dd (2026-11-12). | Lineage entry |
| 2026-11-12 | 1 | First upstream sync (4287c8a to 057d5dd): FDIC PR #19, tighter Figure 32 axes and doc revision relabel; no model change. FFIEC scaffold with mocked-response tests. | 69 tests pass; isolation check clean |
