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
_To be completed after the first authenticated pull: reconciliation, materiality, NIC differences._

## 5. Open items
- PWS endpoint/header names and XBRL element naming to be confirmed on the first authenticated call.
- No MDRM code found for RC-K time-deposit averages from 2017 on, nor for the RC-K noninterest-bearing average.
- Unit check (dollars vs $ thousands) to be confirmed by the reconciliation.

## 6. Document revision history
| Date | Revision | Change | Validation |
| :-- | :-- | :-- | :-- |
| 2026-11-12 | 1 | Seeded from FDIC Model v1.0, document revision 2.0 (WIP), commit 057d5dd (2026-11-12). | Lineage entry |
| 2026-11-12 | 1 | First upstream sync (4287c8a to 057d5dd): FDIC PR #19, tighter Figure 32 axes and doc revision relabel; no model change. FFIEC scaffold with mocked-response tests. | 69 tests pass; isolation check clean |
