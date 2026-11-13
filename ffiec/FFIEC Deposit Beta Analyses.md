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
Pull (2026-11-13): 8,791 filings, 100,748 item records, 0 amendments. 536 filings (53 entities, 2007Q4 to 2013Q3) returned HTTP 500 and are in `ffiec/data/missing_filings.csv`. Each was checked against the service's own filer list for that quarter (`RetrieveFilersSinceDate`; `ffiec/outputs/missing_filings_check.csv`): none of the 536 is listed, so these are non-filers, not outages. 13 entities miss exactly 2007Q4 to 2011Q4 and file from 2012Q1, consistent with institutions that filed another report before 2012 (not yet confirmed which). Build: 525 rows, 383 events, all validation checks pass.

Reconciliation with BankFind (`ffiec/outputs/reconciliation_summary.csv`): total deposits match exactly in every quarter. 133 quarters flagged: 126 "differs" (rate_pf_clean; 6 of them also interest expense and deposit rate) and 7 "ffiec_only" (2026Q3). Root causes found and fixed in the builder:
1. Total deposits omitted foreign offices. Filers with foreign offices report RCON2200 and RCFN2200 and no RCFD2200, so total deposits is now RCON2200 + RCFN2200 (Huntington, M&T, KeyBank; gap equalled RCFN2200 exactly).
2. One RSSD maps to several certs over time (9 certs share 4 RSSDs, e.g. 4999 and 59026), and a rssd-to-cert dictionary kept only one. Rows now go to each cert alive in that quarter (per FDIC cert/quarter coverage, read only).
Remaining 126 differences: 89 have a different count of predecessors included (predecessors with no Call Report in the pre-2012 quarters, plus 5 certs with no RSSD in the FDIC API: 27120, 33001, 57128, 57422, 91385); 37 have the same predecessors and differ by small interest-expense amounts (68 of 8,384 bank-quarters differ by more than 1 in EDEPDOMQ, mostly Q2 to Q4; cause not established, restated year-to-date figures are the leading suspect).
Materiality (`ffiec/outputs/materiality_summary.csv`), after the fixes: RC-K interest-bearing rate versus the 2-point rate, 2008 to 2016 only (36 quarters per bank). Correlations 0.97 to 1.00; level gap (RC-K minus 2-point) 0.03 to 0.12 points (SouthState 0.121, First Horizon 0.084, others 0.03 to 0.05).
NIC cross-check: not run (NIC download blocked; needs a CSV via `--file`).

## 5. Open items
- Endpoint, header names, element naming and units (dollars, divided by 1,000) confirmed on the first authenticated pull (SIS611 v1.10).
- 37 quarters with the same predecessors still differ on interest expense (small); test whether BankFind uses restated or as-originally-filed year-to-date figures.
- The 89 quarters with fewer predecessors than BankFind: decide whether FFIEC may use a different predecessor set pre-2012 (Mode A needs the pre-merger history).
- NIC Transformations cross-check not yet run.
- No MDRM code found for RC-K time-deposit averages from 2017 on, nor for the RC-K noninterest-bearing average.

## 6. Document revision history
| Date | Revision | Change | Validation |
| :-- | :-- | :-- | :-- |
| 2026-11-12 | 1 | Seeded from FDIC Model v1.0, document revision 2.0 (WIP), commit 057d5dd (2026-11-12). | Lineage entry |
| 2026-11-12 | 1 | First upstream sync (4287c8a to 057d5dd): FDIC PR #19, tighter Figure 32 axes and doc revision relabel; no model change. FFIEC scaffold with mocked-response tests. | 69 tests pass; isolation check clean |
