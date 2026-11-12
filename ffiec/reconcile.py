"""Reconcile the FFIEC-built dataset with the current FDIC datasets, per bank per quarter.

    python ffiec/reconcile.py

Reads (never writes): FDIC consolidated_fdic_quarterly_financials_2008-2026[_merger_adjusted].csv at the repo root.
Reads ffiec/outputs/ (build_ffiec.py) and ffiec/data/amendments.csv (optional).
Writes ffiec/outputs/reconciliation_summary.csv (max abs difference per bank and measure, standalone and pro forma)
and reconciliation_quarters.csv (quarters whose difference exceeds the tolerance, with an amendment flag).
Quarters only in FFIEC (e.g. 2026Q3) are listed as ffiec_only; quarters only in FDIC as fdic_only.
"""
import sys
from pathlib import Path

import pandas as pd

FFIEC = Path(__file__).resolve().parent
ROOT = FFIEC.parent
TOL = {"total_deposits": 1.0, "deposit_interest_expense": 1.0, "deposit_rate": 0.005, "rate_pf_clean": 0.005}
MEASURES = ["total_deposits", "deposit_interest_expense", "deposit_rate", "rate_pf_clean"]


def reconcile(fdic, ffiec, amendments=None, tol=TOL):
    keys = ["cert_number", "quarter"]
    m = fdic[keys + MEASURES].merge(ffiec[keys + MEASURES], on=keys, how="outer", suffixes=("_fdic", "_ffiec"),
                                    indicator="src")
    rows, summ = [], []
    for k in MEASURES:
        m[f"d_{k}"] = (m[f"{k}_ffiec"] - m[f"{k}_fdic"]).abs()
    both = m[m.src == "both"]
    for cert, g in both.groupby("cert_number"):
        for k in MEASURES:
            d = g[f"d_{k}"]
            summ.append({"cert_number": cert, "measure": k, "n_quarters": int(d.notna().sum()),
                         "max_abs_diff": d.max(), "n_over_tol": int((d > tol[k]).sum())})
    for r in both.itertuples():
        bad = [k for k in MEASURES if getattr(r, f"d_{k}") > tol[k]]
        if bad:
            rows.append({"cert_number": r.cert_number, "quarter": r.quarter, "status": "differs",
                         "measures": ",".join(bad), **{f"d_{k}": getattr(r, f"d_{k}") for k in MEASURES}})
    for r in m[m.src != "both"].itertuples():
        rows.append({"cert_number": r.cert_number, "quarter": r.quarter,
                     "status": "ffiec_only" if r.src == "right_only" else "fdic_only", "measures": ""})
    q = pd.DataFrame(rows)
    if amendments is not None and len(q):
        am = {pd.Timestamp(p).strftime("%Y-%m-%d") for p in amendments.period}
        q["amendment_in_window"] = q.quarter.isin(am)
    return pd.DataFrame(summ), q


def main():
    out = FFIEC / "outputs"
    fdic = pd.read_csv(ROOT / "consolidated_fdic_quarterly_financials_2008-2026_merger_adjusted.csv")
    ffiec = pd.read_csv(out / "consolidated_fdic_quarterly_financials_2008-2026_merger_adjusted.csv")
    ap = FFIEC / "data" / "amendments.csv"
    summ, q = reconcile(fdic, ffiec, pd.read_csv(ap) if ap.exists() else None)
    summ.to_csv(out / "reconciliation_summary.csv", index=False)
    q.to_csv(out / "reconciliation_quarters.csv", index=False)
    print(summ.groupby("measure").max_abs_diff.max().to_string())
    print("quarters flagged:", len(q), q.status.value_counts().to_dict() if len(q) else {})
    return 0


if __name__ == "__main__":
    sys.exit(main())
