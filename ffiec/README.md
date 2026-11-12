# FFIEC Call Report pipeline (Model v2.0)

Downstream of the FDIC repo (Model v1.0, `Panda5130/Deposit-Beta`). Same ECM pipeline for the 7 target banks,
with financials from FFIEC Call Reports instead of FDIC BankFind. Phase 1 (pilot) does not feed the model.

## Layout
| Path | What |
| :-- | :-- |
| `data_build/items.py` | Fixed item codes (each checked against MDRM) |
| `data_build/ffiec_pull.py` | Incremental PWS pull, keyring credentials, YTD to quarterly, response hashes |
| `data_build/nic_events.py` | NIC Transformations cross-check against `merger_events_used.csv` |
| `data_build/build_ffiec.py` | Dataset builder; imports FDIC `build_dataset.py`, edits nothing |
| `reconcile.py`, `materiality.py` | Phase 1 reports |
| `verify_isolation.py` | Checks nothing outside `ffiec/` changed |
| `data/`, `outputs/`, `figures/`, `reference/` | All FFIEC outputs; `reference/` is the FFIEC MAE reference (`--reference-dir ffiec/reference/`) |
| `FFIEC Deposit Beta Analyses.md` | The FFIEC SR 11-7 doc, version 2.0 |

## Credentials
Read only from `keyring` (service `ffiec_pws`, keys `token` and `user`), else env `FFIEC_USER`, `FFIEC_TOKEN`.
Missing: the pull stops with instructions, never prompts. The token is never printed, logged or committed.

## Isolation rules
1. The FFIEC pipeline writes only under `ffiec/`.
2. Shared code files, FDIC outputs and `WIP Regional Banking Deposit Beta Analyses.md` are never edited or deleted.
   FDIC outputs are read only (reconciliation).
3. If FFIEC needs a hook in shared code, propose it as a neutral, behaviour-preserving FDIC change first; sync it down.
4. FDIC's MAE reference (`MAE_Backtesting/reference/`) is never read by FFIEC.
5. No Obsidian vault; the docs are the record.
6. Run `python ffiec/verify_isolation.py` before every PR.

## Sync procedure (FDIC to FFIEC only; nothing flows back)
```bash
git remote add upstream https://github.com/Panda5130/Deposit-Beta.git   # once
git fetch upstream
git switch -c sync/<yyyy-mm-dd>
git merge upstream/main
python ffiec/verify_isolation.py --allow-sync
pytest -q --tb=line
```
Then rerun the FFIEC pipeline (`ffiec_pull.py`, `build_ffiec.py`, `reconcile.py`, `materiality.py`), and open a sync
PR linking the FDIC issue or PR it brings in, with a validation note: what reran, what changed, the decision for
FFIEC. That note is the FFIEC change log under SR 11-7. Update the "last synced FDIC commit" in the FFIEC doc.
An FFIEC improvement wanted upstream is made deliberately as an FDIC PR.

## Pilot run
```bash
python ffiec/data_build/ffiec_pull.py --plan      # entities, unmapped certs, call count; no calls
python ffiec/data_build/ffiec_pull.py             # needs credentials
python ffiec/data_build/build_ffiec.py
python ffiec/reconcile.py
python ffiec/materiality.py
python ffiec/data_build/nic_events.py --file <NIC transformations csv>
```
