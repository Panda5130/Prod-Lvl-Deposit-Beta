# FFIEC Deposit Beta Analyses

**Document version 2.0** (FFIEC Call Report source). Baseline: FDIC document version 1.0 as at FDIC `main` commit
`4287c8a178494eddce7dc6899c0f10cdbfa0df21`. Last synced FDIC commit: `4287c8a178494eddce7dc6899c0f10cdbfa0df21`.

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

## 6. Change log
| Date | Change | Validation |
| :-- | :-- | :-- |
| 2026-11-12 | Scaffold, version 2.0 skeleton | Unit tests with mocked responses; isolation check |
