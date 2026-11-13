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
Pull (2026-11-13): 8,848 filings, about 101,400 item records, 0 amendments. 592+ filings (53+ entities, 2007Q4 to 2021Q4) returned HTTP 500 and are in `ffiec/data/missing_filings.csv`. Each was checked against the service's own filer list for that quarter (`RetrieveFilersSinceDate`; `ffiec/outputs/missing_filings_check.csv`): none is listed, so these are non-filers, not outages. 13 entities miss exactly 2007Q4 to 2011Q4 and file from 2012Q1 (consistent with institutions that filed another report before 2012; not confirmed which). Build: 525 rows, 383 events, all validation checks pass.

Reconciliation with BankFind (`ffiec/outputs/reconciliation_summary.csv`): total deposits match in every shared bank-quarter (0 of 8,503 differ). 121 quarters flagged: 114 "differs" (rate_pf_clean; 6 also interest expense) and 7 "ffiec_only" (2026Q3). Root causes, with fixes in the builder and pull:
1. Total deposits omitted foreign offices (filers with foreign offices report RCON2200 and RCFN2200, no RCFD2200): total is now RCON2200 + RCFN2200.
2. A cert and an RSSD are not one-to-one. 9 certs share 4 RSSDs, and the FDIC API gives 3 certs another cert's RSSD (4999, 35525, 57276; true RSSDs 115641, 2920737, 3049653, taken from the filings' own identifiers and listed with evidence in `ffiec/data/rssd_extra.csv`). A cert can also file under two RSSDs over time (4999: 115641 to 2011Q3, then 4262534). The builder now assigns a filing to a cert only if the cert existed that quarter and the filing's deposits are within 10% of BankFind's (identity check; values stay FFIEC).
3. Remaining predecessor-count differences (85 of 113 rate differences): 667 BankFind cert-quarters have no FFIEC row: 449 where the service lists no Call Report (certs with BankFind data in 2008 to 2011 but no Call Report), 109 for 5 certs with no RSSD (27120, 33001, 57128, 57422, 91385), 89 beyond the predecessors' last merger quarter (not needed), 20 filed but dropped. These predecessors are absent from the FFIEC pro forma, so FFIEC rates differ before 2012.
4. Interest expense (63 of 8,503 bank-quarters differ by more than 1): year-to-date levels match BankFind exactly (checked via EDEPDOM, e.g. KeyBank 2016Q4 174,819 in both). BankFind's own quarterly field does not tie to its own year-to-date field in those quarters (KeyBank 2016Q4: 58,289 against the filed step of 68,020). The FFIEC quarterly series ties to the filed year-to-date.
Decision (owner, 2026-11-13): FFIEC Call Reports are the reference from 2012Q1 onward; earlier quarters are kept in the outputs for reference but are not reliable, because savings institutions filed Thrift Financial Reports to the OTS until 2011 (Call Reports from March 2012), so pre-2012 pro forma lacks those predecessors. `reconcile.py` marks this with `in_window` (quarter >= 2012-03-31). Inside the window: 33 flagged quarters (7 "ffiec_only" 2026Q3, 26 "differs"), 25 rate differences in 406 bank-quarters, median 0.012 and maximum 0.16 points, almost all with the same predecessors (the BankFind quarterly interest-expense difference in point 4). Four previously unmapped trust-company certs (27120, 33001, 57422, 91385) now map through `ffiec/data/rssd_extra.csv` (all Mode B, one quarter each).
Materiality (`ffiec/outputs/materiality_summary.csv`): RC-K interest-bearing rate versus the 2-point rate, 2008 to 2016 only (36 quarters per bank). Correlations 0.97 to 1.00; level gap (RC-K minus 2-point) 0.03 to 0.12 points (SouthState 0.121, First Horizon 0.084, others 0.03 to 0.05).
NIC cross-check (NIC Transformations CSV, 2026-11-13, `ffiec/reference/CSV_TRANSFORMATIONS.CSV`; `ffiec/outputs/nic_event_differences.csv`): 380 of 387 FDIC events match, 1 date differs (same quarter), 6 FDIC-only (same-RSSD charter changes, which NIC does not record, and one below materiality). 67 NIC-only events: 50 predecessors do not file Call Reports, 7 predate 2008, 10 do (`ffiec/outputs/nic_only_filer_check.csv`); 3 of those 10 are the charter swaps above, 7 are candidate mergers missing from the FDIC history (predecessor RSSDs 272218, 430670, 1160853, 1416279, 1459575, 2111508, 2934930; 272218 merged into a target in 2011).

## 5. Open items
- Endpoint, header names, element naming and units (dollars, divided by 1,000) confirmed on the first authenticated pull (SIS611 v1.10).
- Pre-2012 predecessors: resolved by starting the reference window at 2012Q1 (section 4). Possible fill from the OCC archive of OTS Thrift Financial Reports (bulk files for September and December 2011 are published; earlier quarters by request to the OCC, not verified): not pursued, and BankFind is not used as a fill because it would mix sources.
- Interest-expense quarters where BankFind's quarterly field does not tie to its own year-to-date: FFIEC stays the reference (it ties to the filed year-to-date); the 63 bank-quarters are recorded as a BankFind-side difference.
- Three NIC-only mergers still to raise with the FDIC side (FFIEC does not edit FDIC events): Wilmington Trust Company (RSSD 272218, into M&T 2011-05-16), Voyager Bank (430670), SouthBank FSB (2111508).
- No MDRM code found for RC-K time-deposit averages from 2017 on, nor for the RC-K noninterest-bearing average.

## 6. Document revision history
| Date | Revision | Change | Validation |
| :-- | :-- | :-- | :-- |
| 2026-11-12 | 1 | Seeded from FDIC Model v1.0, document revision 2.0 (WIP), commit 057d5dd (2026-11-12). | Lineage entry |
| 2026-11-12 | 1 | First upstream sync (4287c8a to 057d5dd): FDIC PR #19, tighter Figure 32 axes and doc revision relabel; no model change. FFIEC scaffold with mocked-response tests. | 69 tests pass; isolation check clean |
