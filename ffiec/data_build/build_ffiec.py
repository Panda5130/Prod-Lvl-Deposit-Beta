"""FFIEC dataset builder: reuses the merger logic in data_build/build_dataset.py by importing it (not editing it).

    python ffiec/data_build/build_ffiec.py

The FDIC module is loaded from its file, its `Fdic` loader class is replaced in memory by `FfiecSource` (same
interface: .fin, .hist, .series, .events, .extend) and its output root is pointed at ffiec/outputs/, then the
unchanged `build`, `validate` and `write` run. So pro_forma, rate_frame, the 1% materiality test, Mode A/B and
the recursion are exactly the FDIC code. No hook in shared code was needed.

Inputs: ffiec/data/ffiec_items_quarterly.csv, ffiec/data/cert_rssd.csv; FDIC /history events from
data_build/raw/history_targets.csv (read only; the primary event source, per the plan).
Units: Call Report values are dollars; BankFind DEP/EDEPDOMQ/EDEPFORQ are $ thousands, so values are divided
by UNIT_DIVISOR (ASSUMPTION to confirm on the first pull against BankFind; the reconciliation exposes it).
Rows missing total deposits or any domestic RI code for the quarter are dropped (never zero-filled).
"""
import importlib.util
import logging
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from items import ri_dom_codes  # noqa: E402

FFIEC = HERE.parent
ROOT = FFIEC.parent
OUT = FFIEC / "outputs"
UNIT_DIVISOR = 1000.0
log = logging.getLogger("build_ffiec")


def load_fdic_module(root=ROOT):
    spec = importlib.util.spec_from_file_location("fdic_build_dataset", root / "data_build" / "build_dataset.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def financials_from_items(quarterly, cert_rssd, cert_quarters=None):
    """Wide FDIC-shaped frame (CERT, REPDTE, DEP, EDEPDOMQ, EDEPFORQ) in $ thousands from quarterly long items."""
    w = quarterly.pivot_table(index=["rssd", "period"], columns="item", values="value", aggfunc="first")
    w = w.reset_index()
    for col in ("RCFD2200", "RCON2200", "RCFN2200", "RIAD4172"):
        if col not in w:
            w[col] = float("nan")
    # Total deposits = domestic offices (RCON2200) + foreign offices (RCFN2200). Filers with foreign offices
    # report no RCFD2200 in the service output, so using RCON2200 alone drops foreign deposits (root cause of
    # the 2008-2015 reconciliation gap for Huntington, M&T and KeyBank). RCFD2200, if present, is the total.
    w["DEP"] = w.RCFD2200.fillna(w.RCON2200 + w.RCFN2200.fillna(0.0))
    dom = []
    for _, r in w.iterrows():
        codes = ri_dom_codes(r["period"])
        vals = [r.get(c, float("nan")) for c in codes]
        dom.append(sum(vals) if not any(pd.isna(v) for v in vals) else float("nan"))
    w["EDEPDOMQ"] = dom
    # 2007 flows are not needed (rates start 2008Q1; 2007Q4 only supplies DEP for the average), and a Q4 YTD
    # cannot be de-cumulated without Q3, so 2007 IE gaps are set to 0 here; later gaps are dropped, never zero-filled.
    w.loc[(w.period < "2008-01-01") & w.EDEPDOMQ.isna(), "EDEPDOMQ"] = 0.0
    w["EDEPFORQ"] = w.RIAD4172.fillna(0.0)
    w = w.dropna(subset=["DEP", "EDEPDOMQ"])
    out = pd.DataFrame({"rssd": w.rssd, "REPDTE": w.period.str.replace("-", "").astype(int),
                        "DEP": w.DEP / UNIT_DIVISOR, "EDEPDOMQ": w.EDEPDOMQ / UNIT_DIVISOR,
                        "EDEPFORQ": w.EDEPFORQ / UNIT_DIVISOR})
    # One RSSD can belong to several certs over time (e.g. a charter change retired the cert but kept the RSSD).
    # The filing is the RSSD's, so each row goes to every cert sharing it; for a shared RSSD the quarter must fall
    # inside that cert's life, which `cert_quarters` ((CERT, REPDTE) pairs the FDIC history knows) tells us.
    cert_map = pd.DataFrame([(r, c) for c, r in cert_rssd.items() if r], columns=["rssd", "CERT"])
    shared = cert_map.rssd.duplicated(keep=False)
    out = out.merge(cert_map, on="rssd", how="inner")
    if cert_quarters is not None:
        in_life = pd.Series([(c, d) in cert_quarters for c, d in zip(out.CERT, out.REPDTE)], index=out.index)
        keep = ~out.rssd.isin(set(cert_map.rssd[shared])) | in_life
        out = out[keep]
    return out.drop(columns="rssd")[["CERT", "REPDTE", "DEP", "EDEPDOMQ", "EDEPFORQ"]].astype({"CERT": int})


def make_source_class(bd, fin, hist):
    class FfiecSource(bd.Fdic):
        def __init__(self, refresh=False):          # does not call the FDIC loader: no network, no raw cache
            self.refresh, self.fin, self.hist = refresh, fin, hist

        def extend(self, certs):                    # predecessors come from the pre-pulled FFIEC items
            missing = sorted(set(certs) - set(self.fin.CERT))
            if missing:
                log.warning("no FFIEC financials for predecessor certs %s (flagged by pro_forma)", missing[:10])
    return FfiecSource


def build_ffiec(items_path=None, cert_rssd_path=None, hist_path=None, outdir=OUT, root=ROOT):
    bd = load_fdic_module(root)
    quarterly = pd.read_csv(items_path or FFIEC / "data" / "ffiec_items_quarterly.csv", dtype={"period": str})
    cr = pd.read_csv(cert_rssd_path or FFIEC / "data" / "cert_rssd.csv")
    cert_rssd = {int(c): (int(r) if pd.notna(r) else None) for c, r in zip(cr.cert, cr.rssd)}
    fdic_fin = pd.read_csv(root / "data_build" / "raw" / "financials_targets.csv", usecols=["CERT", "REPDTE"])  # read only
    fin = financials_from_items(quarterly, cert_rssd, set(zip(fdic_fin.CERT, fdic_fin.REPDTE)))
    hist = pd.read_csv(hist_path or root / "data_build" / "raw" / "history_targets.csv")
    src = make_source_class(bd, fin, hist)
    outdir.mkdir(parents=True, exist_ok=True)
    bd.Fdic, bd.ROOT = src, outdir                  # in-memory only; build_dataset.py on disk is untouched
    data, events = bd.build(False)
    checks = bd.validate(data)
    bd.write(data, events, checks)
    return data, events, checks


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    data, events, checks = build_ffiec()
    log.info("wrote %d rows, %d events to %s; checks %s", len(data), len(events), OUT, checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
