"""Cross-check NIC Transformations (mergers/acquisitions) against merger_events_used.csv.

    python ffiec/data_build/nic_events.py --file <NIC transformations csv>   # or omit --file to try the download

The NIC file is a download from https://www.ffiec.gov/npw/ (Data Download, Transformations); the site blocks
scripted requests without a browser session in some environments, so a manually saved CSV is accepted with --file.
Column names are matched case-insensitively against aliases (ASSUMPTION: predecessor/successor RSSD, transaction
date, transformation code) and the match fails loudly if they are not found.

Events are matched on (predecessor RSSD, successor RSSD) via ffiec/data/cert_rssd.csv. FDIC /history stays the
primary source; this only flags differences. Output: ffiec/outputs/nic_event_differences.csv with columns
status in {fdic_only, nic_only, date_differs}. Reads merger_events_used.csv without writing it.
"""
import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
FFIEC = HERE.parent
ROOT = FFIEC.parent
NIC_URL = "https://www.ffiec.gov/npw/FinancialReport/ReturnTransformationsCSV"
ALIASES = {"pred": ["id_rssd_predecessor", "predecessor_rssd", "pred_rssd"],
           "succ": ["id_rssd_successor", "successor_rssd", "succ_rssd"],
           "date": ["dt_trans", "trans_date", "effective_date"],
           "code": ["trnsfm_cd", "transformation_code"]}
DATE_TOLERANCE_DAYS = 31
START = pd.Timestamp("2007-01-01")


def read_nic(src):
    d = pd.read_csv(src, dtype=str)
    d.columns = [c.strip().lstrip("#").lower() for c in d.columns]
    rename = {}
    for k, names in ALIASES.items():
        hit = next((n for n in names if n in d.columns), None)
        if hit is None and k != "code":
            raise ValueError(f"NIC file lacks a {k} column; have {list(d.columns)[:12]}")
        if hit:
            rename[hit] = k
    d = d.rename(columns=rename)
    d["pred"] = pd.to_numeric(d.pred, errors="coerce").astype("Int64")
    d["succ"] = pd.to_numeric(d.succ, errors="coerce").astype("Int64")
    d["date"] = pd.to_datetime(d.date, errors="coerce")
    return d.dropna(subset=["pred", "succ", "date"])


def download_nic():
    r = requests.get(NIC_URL, timeout=120)
    r.raise_for_status()
    return io.StringIO(r.text)


def compare(nic, events, cert_rssd):
    """Differences between NIC and the FDIC events used. Only NIC rows whose successor is a survivor in our events
    (targets and merger predecessors) and dated 2007 or later are in scope."""
    ev = events.copy()
    ev["pred"] = ev.predecessor_cert.map(cert_rssd)
    ev["succ"] = ev.survivor_cert.map(cert_rssd)
    ev["fdic_date"] = pd.to_datetime(ev.effective_date)
    unmapped = ev[ev.pred.isna() | ev.succ.isna()]
    ev = ev.dropna(subset=["pred", "succ"]).astype({"pred": int, "succ": int})
    scope_succ = set(ev.succ)
    n = nic[(nic.succ.isin(scope_succ)) & (nic.date >= START)].astype({"pred": int, "succ": int})
    n = n.groupby(["pred", "succ"], as_index=False).date.min().rename(columns={"date": "nic_date"})
    m = ev[["pred", "succ", "predecessor_cert", "survivor_cert", "fdic_date", "mode_applied"]].merge(
        n, on=["pred", "succ"], how="outer", indicator="src")
    m["status"] = m.src.map({"left_only": "fdic_only", "right_only": "nic_only", "both": "both"}).astype(str)
    both = m.status == "both"
    m.loc[both & ((m.fdic_date - m.nic_date).abs().dt.days > DATE_TOLERANCE_DAYS), "status"] = "date_differs"
    diff = m[m.status != "both"].drop(columns="src")
    summary = {"fdic_events": len(ev), "nic_in_scope": len(n), "matched": int((m.status == "both").sum()),
               "unmapped_fdic_events": len(unmapped)}
    return diff, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="NIC Transformations cross-check")
    ap.add_argument("--file", help="NIC transformations CSV saved locally")
    a = ap.parse_args(argv)
    nic = read_nic(a.file if a.file else download_nic())
    cr = pd.read_csv(FFIEC / "data" / "cert_rssd.csv")
    cert_rssd = {int(c): r for c, r in zip(cr.cert, cr.rssd) if pd.notna(r)}
    diff, summary = compare(nic, pd.read_csv(ROOT / "merger_events_used.csv"), cert_rssd)
    out = FFIEC / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    diff.to_csv(out / "nic_event_differences.csv", index=False)
    print(summary, "differences:", len(diff))
    return 0


if __name__ == "__main__":
    sys.exit(main())
