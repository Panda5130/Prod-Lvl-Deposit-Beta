"""FFIEC dataset builder: reuses the merger logic in data_build/build_dataset.py by importing it (not editing it).

    python ffiec/data_build/build_ffiec.py

The FDIC module is loaded from its file, its `Fdic` loader class is replaced in memory by `FfiecSource` (same
interface: .fin, .hist, .series, .events, .extend) and its output root is pointed at ffiec/outputs/, then the
unchanged `build`, `validate` and `write` run. So pro_forma, rate_frame, the 1% materiality test, Mode A/B and
the recursion are exactly the FDIC code. No hook in shared code was needed.

Inputs: ffiec/data/ffiec_items_quarterly.csv, ffiec/data/cert_rssd.csv; FDIC /history events from
data_build/raw/history_targets.csv and supplementary_transfer_events.csv (read only; FDIC /history is the primary
event source, plus the supplementary NIC transfers of FDIC issue #20). Outputs carry the FDIC vintage suffix (_v2).
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
from items import NEW_REGIME_START, ri_dom_codes  # noqa: E402
from ffiec_pull import load_cert_rssd, load_extra_rssd  # noqa: E402

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


def hybrid_denominator(w):
    """Interest-bearing average balance A_t (dollars) per (rssd, period); NaN when a required piece is missing.

    A_t = NMD_ib + FOR + TD_avg.  NMD_ib = RCON3485 + RCONB563 (RC-K averages). FOR = RCFN3404 (RC-K average, 031
    filers); missing counts as 0 only when RIAD4172 is absent or 0, otherwise A_t is NaN (never zero-filled).
    TD_avg = mean of this and the prior quarter-end time deposits (RC-E): 6648 + J473 + J474 to 2016Q4,
    HK16 + HK17 from 2017Q1. A prior quarter-end that is not the previous calendar quarter gives NaN."""
    w = w.sort_values(["rssd", "period"]).copy()
    for c in ("RCON3485", "RCONB563", "RCFN3404", "RIAD4172", "RCON6648", "RCONJ473", "RCONJ474", "RCONHK16",
              "RCONHK17"):
        if c not in w:
            w[c] = float("nan")
    new = w.period >= NEW_REGIME_START
    td = (w.RCONHK16 + w.RCONHK17).where(new, w.RCON6648 + w.RCONJ473 + w.RCONJ474)   # NaN if any piece missing
    prev_p = pd.PeriodIndex(pd.to_datetime(w.period), freq="Q") - 1
    prior = pd.Series(td.values, index=pd.MultiIndex.from_arrays([w.rssd.values, pd.PeriodIndex(
        pd.to_datetime(w.period), freq="Q")]))
    prior = prior[~prior.index.duplicated()]
    td_prev = pd.Series(prior.reindex(pd.MultiIndex.from_arrays([w.rssd.values, prev_p])).values, index=w.index)
    foreign = w.RCFN3404.where(w.RCFN3404.notna() | w.RIAD4172.fillna(0).ne(0), 0.0)
    w["NMD_IB"] = w.RCON3485 + w.RCONB563
    w["TD_AVG"] = (td + td_prev) / 2
    w["A"] = w.NMD_IB + foreign + w.TD_AVG
    return w


def financials_from_items(quarterly, cert_rssd, cert_quarters=None, extra=None, hybrid=False):
    """Wide FDIC-shaped frame (CERT, REPDTE, DEP, EDEPDOMQ, EDEPFORQ) in $ thousands from quarterly long items.
    hybrid=True adds A (hybrid interest-bearing average balance, $ thousands) and RATE_NMD_NUM/DEN columns."""
    w = quarterly.pivot_table(index=["rssd", "period"], columns="item", values="value", aggfunc="first")
    w = w.reset_index()
    if hybrid:
        w = hybrid_denominator(w)
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
    if hybrid:
        out["A"] = w.A / UNIT_DIVISOR
        out["NMD_IB"] = w.NMD_IB / UNIT_DIVISOR
        out["NMD_IE"] = (w.RIAD4508 + w.RIAD0093) / UNIT_DIVISOR
    # A cert can have several RSSDs and an RSSD several certs (the FDIC API sometimes gives a cert another cert's
    # RSSD, or the RSSD of a later charter). `extra` adds the known further RSSDs per cert. Where a cert or an RSSD
    # is ambiguous, a filing is assigned to a cert only if the cert existed that quarter and the filing's total
    # deposits are within 10% of BankFind's DEP for that cert-quarter (identity check only; values stay FFIEC);
    # with two candidates the closest wins. `cert_quarters` is {(CERT, REPDTE): DEP in $ thousands}.
    pairs = {(r, c) for c, r in cert_rssd.items() if r}
    pairs |= {(r, c) for c, rs in (extra or {}).items() for r in rs}
    cert_map = pd.DataFrame(sorted(pairs), columns=["rssd", "CERT"])
    ambiguous = cert_map.rssd.duplicated(keep=False) | cert_map.CERT.duplicated(keep=False)
    amb = set(map(tuple, cert_map[ambiguous].values))
    out = out.merge(cert_map, on="rssd", how="inner")
    if cert_quarters is not None:
        ref = pd.Series([cert_quarters.get((c, d)) for c, d in zip(out.CERT, out.REPDTE)], index=out.index, dtype=float)
        is_amb = pd.Series([(r, c) in amb for r, c in zip(out.rssd, out.CERT)], index=out.index)
        out["gap"] = ((out.DEP - ref).abs() / ref.abs().where(ref != 0))
        out = out[~is_amb | (ref.notna() & (out.gap <= 0.10))]
        out = out.sort_values("gap").drop_duplicates(["CERT", "REPDTE"], keep="first")
    cols = ["CERT", "REPDTE", "DEP", "EDEPDOMQ", "EDEPFORQ"] + (["A", "NMD_IB", "NMD_IE"] if hybrid else [])
    return out.drop(columns=[c for c in ("rssd", "gap") if c in out])[cols].astype({"CERT": int})


def make_source_class(bd, fin, hist):
    class FfiecSource(bd.Fdic):
        def __init__(self, refresh=False, supplementary=None):   # no FDIC loader: no network, no raw cache
            self.refresh, self.fin, self.hist = refresh, fin, hist
            self.supp = bd.load_supplementary(supplementary)      # FDIC supplementary transfers (issue #20), read only

        def extend(self, certs):                    # predecessors come from the pre-pulled FFIEC items
            missing = sorted(set(certs) - set(self.fin.CERT))
            if missing:
                log.warning("no FFIEC financials for predecessor certs %s (flagged by pro_forma)", missing[:10])
    return FfiecSource


def build_ffiec(items_path=None, cert_rssd_path=None, hist_path=None, outdir=OUT, root=ROOT):
    bd = load_fdic_module(root)
    quarterly = pd.read_csv(items_path or FFIEC / "data" / "ffiec_items_quarterly.csv", dtype={"period": str})
    cert_rssd = load_cert_rssd(cert_rssd_path or FFIEC / "data" / "cert_rssd.csv")   # includes rssd_overrides.csv
    fdic_fin = pd.read_csv(root / "data_build" / "raw" / "financials_targets.csv", usecols=["CERT", "REPDTE", "DEP"])  # read only
    fin = financials_from_items(quarterly, cert_rssd, dict(zip(zip(fdic_fin.CERT, fdic_fin.REPDTE), fdic_fin.DEP)),
                                load_extra_rssd(), hybrid=True)
    hist = pd.read_csv(hist_path or root / "data_build" / "raw" / "history_targets.csv")
    src = make_source_class(bd, fin, hist)
    outdir.mkdir(parents=True, exist_ok=True)
    bd.Fdic, bd.ROOT = src, outdir                  # in-memory only; build_dataset.py on disk is untouched
    data, events = bd.build(False, root / "data_build" / "raw" / "supplementary_transfer_events.csv")
    checks = bd.validate(data)
    for old in outdir.glob(f"*_{bd.VINTAGE}.*"):   # FDIC write() never overwrites a vintage; FFIEC outputs are rebuilt
        old.unlink()
    bd.write(data, events, checks)
    supp = root / "data_build" / "raw" / "supplementary_transfer_events.csv"
    build_hybrid(data, events, fin, hist, bd, supp, outdir)
    return data, events, checks


HYBRID_START = "2012-01-01"


def pro_forma_ib(src, cert, modes, depth=0):
    """Same fold as FDIC `pro_forma` (predecessors scaled by transfer share, Mode A recursion, merger-quarter
    interest expense pro rata to the days before the effective date) but with the Mode A/B decision taken from
    `modes` ({(predecessor, survivor, effective date): mode}, i.e. the total-deposit build's decision on DEP).
    The series' DEP column holds A_t; a predecessor quarter with A_t missing makes the survivor's A_pf missing
    for that quarter (NaN propagates; the row is then dropped, never zero-filled)."""
    pf = src.series(cert).copy()
    pf["n_pred"] = 0
    for e in src.events(cert).itertuples():
        pred_cert, mq, share = int(e.OUT_CERT), pd.Period(e.EFFDATE, "Q"), float(e.transfer_share)
        if modes.get((pred_cert, cert, str(e.EFFDATE.date()))) != "A":
            continue
        pred = src.series(pred_cert)
        pred = pred[pred.index < mq]
        if pred.empty:
            continue
        last_q = pred.index.max()
        pred_pf = pro_forma_ib(src, pred_cert, modes, depth + 1)
        pred_pf = pred_pf[pred_pf.index < mq].copy()
        pred_pf[["DEP", "ie"]] *= share
        idx = pf.index.intersection(pred_pf.index)
        pf.loc[idx, ["DEP", "ie"]] += pred_pf.loc[idx, ["DEP", "ie"]]
        pf.loc[idx, "n_pred"] += 1 + pred_pf.loc[idx, "n_pred"]
        if mq in pf.index:
            frac = (e.EFFDATE - mq.start_time).days / ((mq.end_time.normalize() - mq.start_time).days + 1)
            pf.loc[mq, "ie"] += frac * pred_pf.loc[last_q, "ie"]
    return pf


def build_hybrid(data, events, fin, hist, bd, supplementary, outdir=OUT):
    """Interest-bearing deposit-rate dataset on the hybrid denominator A_t (doc 5.4). A_t is already an
    average, so no further averaging. Merger Mode A/B decisions are those of the total-deposit build (made on
    DEP), so the event set is identical by construction."""
    src = make_source_class(bd, fin.assign(DEP=fin["A"]), hist)(False, supplementary)
    modes = {}
    for r in events.itertuples():
        modes.setdefault((int(r.predecessor_cert), int(r.survivor_cert), str(r.effective_date)), r.mode_applied)
    rows = []
    for cert, name in bd.TARGETS.items():
        sa, pf = src.series(cert), pro_forma_ib(src, cert, modes)
        d = pd.DataFrame({"bank_name": name, "cert_number": cert,
                          "quarter": sa.index.to_timestamp(how="end").strftime("%Y-%m-%d"),
                          "ie": sa["ie"], "A": sa["DEP"], "rate_ib": 400 * sa["ie"] / sa["DEP"],
                          "ie_ann_pf": 4 * pf["ie"], "A_pf": pf["DEP"], "rate_ib_pf": 400 * pf["ie"] / pf["DEP"],
                          "n_predecessors_included": pf["n_pred"].astype(int)}, index=sa.index)
        f = fin[fin.CERT == cert].assign(q=lambda x: pd.to_datetime(x.REPDTE.astype(str)).dt.to_period("Q"))
        f = f.set_index("q").sort_index()
        d["rate_nmd"] = 400 * f["NMD_IE"] / f["NMD_IB"]
        rows.append(d)
    out = pd.concat(rows).reset_index(drop=True)
    out = out[out.quarter >= HYBRID_START]
    ref = data[data.quarter >= HYBRID_START][["cert_number", "quarter", "rate_pf", "dep_avg_pf", "adjustment_mode",
                                              "merger_quarter", "pct_deposits_acquired_in_quarter"]]
    out = ref.rename(columns={"rate_pf": "rate_total_pf"}).merge(out, on=["cert_number", "quarter"], how="left")
    dropped = out[out.rate_ib_pf.isna()][["bank_name", "cert_number", "quarter"]]
    out = out.dropna(subset=["rate_ib_pf"])
    out.to_csv(outdir / f"ffiec_deposit_rates_hybrid_{bd.VINTAGE}.csv", index=False)
    dropped.to_csv(outdir / f"hybrid_dropped_quarters_{bd.VINTAGE}.csv", index=False)
    for old in outdir.glob(f"hybrid_event_set_differences_{bd.VINTAGE}.csv"):
        old.unlink()
    return out, dropped


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    data, events, checks = build_ffiec()
    log.info("wrote %d rows, %d events to %s; checks %s", len(data), len(events), OUT, checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
