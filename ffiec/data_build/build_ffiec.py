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

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from items import NEW_REGIME_START, ri_dom_codes  # noqa: E402
from ffiec_pull import load_cert_rssd, load_extra_rssd  # noqa: E402

FFIEC = HERE.parent
ROOT = FFIEC.parent
OUT = FFIEC / "outputs"
UNIT_DIVISOR = 1000.0
TD_FALLBACK_PERIOD = "2012-03-31"
# Product legs: (balance column, interest-expense column) in the hybrid frame.
# QE_PRODUCTS are Schedule RC / RC-E quarter-end balances: folded pro forma first, then two-point averaged (as the
# origin does for DEP); nmd + time + for tile the interest-bearing base exactly.
# AVG_PRODUCTS are RC-K quarterly averages (folded as averages): the RC-K split of nmd, kept for reference only,
# unreliable at banks with reclassification (sweep) programs (doc 6.4, 6.5 test D, P11).
QE_PRODUCTS = {"nmd": ("NMD_Q", "NMD_IE"), "time": ("TD_Q", "TD_IE"), "for": ("FOR_Q", "FOR_IE")}
AVG_PRODUCTS = {"tran": ("RCON3485", "RIAD4508"), "sav": ("RCONB563", "RIAD0093")}
PRODUCTS = {**QE_PRODUCTS, **AVG_PRODUCTS}
# Legs that also get an end-of-quarter rate (owner decisions 2026-11-26: time D7, doc 6.9; non-maturity D8, doc 6.10;
# both are the model defaults): rate_<leg>_eoq_pf = 400 x interest
# / <leg>_eoq_pf, the pro forma end-of-quarter balance. No reported time-deposit average exists after 2016, and the
# two-point average misstates the average in quarters of fast intra-quarter growth (First Horizon 2023, KeyBank 2023).
# rate_<leg>_pf (two-point) is kept as the reference, so the two-point legs still tile the interest-bearing base A_pf.
END_BALANCE_LEGS = {"time", "nmd"}
log = logging.getLogger("build_ffiec")


def load_fdic_module(root=ROOT):
    spec = importlib.util.spec_from_file_location("fdic_build_dataset", root / "data_build" / "build_dataset.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hybrid_denominator(w):
    """Interest-bearing average balance A_t (dollars) per (rssd, period); NaN when a required piece is missing.

    A_t (Schedule RC base, owner decision 2026-11-25, doc 6.4/6.5) = two-point average of quarter-end
    RCON6636 + RCFN6636 (RCFN6636 missing counts as 0 only when RCFN2200 is absent or 0). Same prior-quarter rule
    and 2012Q1 one-point fallback as below. It splits exactly into NMD_RC (two-point RCON6636 less TD_avg), TD_AVG
    and FOR_RC (two-point RCFN6636). Schedule RC reports swept (Reg D reclassification) balances as
    noninterest-bearing, which the RC-K savings average does not.

    A_HYB (former hybrid, kept for reference) = NMD_ib + FOR + TD_avg.
    NMD_ib = RCON3485 + RCONB563 (RC-K averages). FOR = RCFN3404 (RC-K average, 031
    filers); missing counts as 0 only when RIAD4172 is absent or 0, otherwise A_t is NaN (never zero-filled).
    TD_avg = mean of this and the prior quarter-end time deposits (RC-E): 6648 + J473 + J474 to 2016Q4,
    HK16 + HK17 from 2017Q1. A prior quarter-end that is not the previous calendar quarter gives NaN.
    One-point fallback (owner decision 2026-11-16): in TD_FALLBACK_PERIOD only, an entity with no Call Report in
    the prior quarter (savings institutions filed the Thrift Financial Report until 2011Q4) uses its own quarter-end
    time deposits as the prior value, so TD_avg = TD_t; flagged in TD_FALLBACK. No other source is used."""
    w = w.sort_values(["rssd", "period"]).copy()
    for c in ("RCON3485", "RCONB563", "RCFN3404", "RIAD4172", "RCON6648", "RCONJ473", "RCONJ474", "RCONHK16",
              "RCONHK17", "RIAD4508", "RIAD0093", "RIADA517", "RIADA518", "RIADHK03", "RIADHK04"):
        if c not in w:
            w[c] = float("nan")
    new = w.period >= NEW_REGIME_START
    td = (w.RCONHK16 + w.RCONHK17).where(new, w.RCON6648 + w.RCONJ473 + w.RCONJ474)   # NaN if any piece missing
    prev_p = pd.PeriodIndex(pd.to_datetime(w.period), freq="Q") - 1
    prior = pd.Series(td.values, index=pd.MultiIndex.from_arrays([w.rssd.values, pd.PeriodIndex(
        pd.to_datetime(w.period), freq="Q")]))
    prior = prior[~prior.index.duplicated()]
    td_prev = pd.Series(prior.reindex(pd.MultiIndex.from_arrays([w.rssd.values, prev_p])).values, index=w.index)
    filed_prev = pd.Series(pd.MultiIndex.from_arrays([w.rssd.values, prev_p]).isin(prior.index), index=w.index)
    w["TD_FALLBACK"] = (w.period == TD_FALLBACK_PERIOD) & ~filed_prev & td.notna()
    td_prev = td_prev.where(~w.TD_FALLBACK, td)

    def two_point(x):                       # same prior-quarter rule and the same one-point fallback as TD
        ser = pd.Series(x.values, index=pd.MultiIndex.from_arrays(
            [w.rssd.values, pd.PeriodIndex(pd.to_datetime(w.period), freq="Q")]))
        ser = ser[~ser.index.duplicated()]
        prev = pd.Series(ser.reindex(pd.MultiIndex.from_arrays([w.rssd.values, prev_p])).values, index=w.index)
        fb = (w.period == TD_FALLBACK_PERIOD) & ~filed_prev
        return (x + prev.where(~fb, x)) / 2
    foreign = w.RCFN3404.where(w.RCFN3404.notna() | w.RIAD4172.fillna(0).ne(0), 0.0)
    w["FOR_BAL"] = foreign
    w["NMD_IB"] = w.RCON3485 + w.RCONB563
    w["TD_AVG"] = (td + td_prev) / 2
    w["TD_IE"] = (w.RIADHK03 + w.RIADHK04).where(new, w.RIADA517 + w.RIADA518)
    w["A_HYB"] = w.NMD_IB + foreign + w.TD_AVG
    # Schedule RC quarter-end split. RCFN6631/6636 missing count as 0 only when the filer reports no
    # foreign-office deposits (RCFN2200 absent or 0); otherwise NaN, never filled.
    for c in ("RCON6631", "RCFN6631", "RCON6636", "RCFN6636", "RCFN2200"):
        if c not in w:
            w[c] = float("nan")
    no_for = w.RCFN2200.fillna(0).eq(0)
    w["TD_Q"] = td
    w["FOR_Q"] = w.RCFN6636.where(w.RCFN6636.notna() | ~no_for, 0.0)
    w["NMD_Q"] = w.RCON6636 - td
    w["IB_Q"] = w.RCON6636 + w.FOR_Q
    w["FOR_RC"] = two_point(w.FOR_Q)
    w["NMD_RC"] = two_point(w.RCON6636) - w.TD_AVG
    w["A"] = two_point(w.IB_Q)
    w["NMD_IE"] = w.RIAD4508 + w.RIAD0093
    w["FOR_IE"] = w.RIAD4172.fillna(0.0)                 # as EDEPFORQ in financials_from_items
    # Reconciling total-deposit leg: noninterest-bearing quarter-end balances, two-point average.
    nib = w.RCON6631 + w.RCFN6631.where(w.RCFN6631.notna() | ~no_for, 0.0)
    w["NIB_AVG"] = two_point(nib)
    w["TOT_AVG"] = w.A + w.NIB_AVG
    w["TOT_Q"] = w.IB_Q + nib
    return w


def financials_from_items(quarterly, cert_rssd, cert_quarters=None, extra=None, hybrid=False):
    """Wide FDIC-shaped frame (CERT, REPDTE, DEP, EDEPDOMQ, EDEPFORQ) in $ thousands from quarterly long items.
    hybrid=True adds A (Schedule RC interest-bearing average balance, $ thousands), A_HYB (former hybrid base),
    the RC-K NMD_IB/NMD_IE pair and the product legs of PRODUCTS."""
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
        out["A_HYB"] = w.A_HYB / UNIT_DIVISOR
        out["NMD_IB"] = w.NMD_IB / UNIT_DIVISOR
        out["NMD_IE"] = (w.RIAD4508 + w.RIAD0093) / UNIT_DIVISOR
        for name, (bal, ie) in PRODUCTS.items():
            out[f"{name.upper()}_BAL"] = w[bal] / UNIT_DIVISOR
            out[f"{name.upper()}_IE"] = w[ie] / UNIT_DIVISOR
        out["TD_FALLBACK"] = w.TD_FALLBACK.astype(float)
        out["IB_Q"] = w.IB_Q / UNIT_DIVISOR
        out["TOT_Q"] = w.TOT_Q / UNIT_DIVISOR
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
    hy = ["A", "A_HYB", "NMD_IB", "NMD_IE", "TD_FALLBACK", "IB_Q", "TOT_Q"] + [f"{n.upper()}_{x}" for n in PRODUCTS for x in ("BAL", "IE")]
    cols = ["CERT", "REPDTE", "DEP", "EDEPDOMQ", "EDEPFORQ"] + (list(dict.fromkeys(hy)) if hybrid else [])
    return out.drop(columns=[c for c in ("rssd", "gap") if c in out])[cols].astype({"CERT": int})


# Interest-expense series repaired by repair_ytd_breaks: (interest column, balance column used for the rate).
# NMD_IE, EDEPDOMQ and EDEPFORQ are recomputed from them afterwards.
YTD_REPAIR_COLS = {"TRAN_IE": "TRAN_BAL", "SAV_IE": "SAV_BAL", "TIME_IE": "TIME_BAL", "FOR_IE": "FOR_BAL"}


def repair_ytd_breaks(fin, hist):
    """Repair quarterly interest expense where year-to-date reporting breaks (doc 6.8). Quarterly flows are derived
    as YTD_t - YTD_t-1 (ffiec_pull.to_quarterly), which fails in two documented cases:

    1. Restart. When a bank is acquired and applies push-down accounting, its YTD income restarts at the
       acquisition date, so YTD_t - YTD_t-1 is too small or negative (First Niagara 2016Q3). Detected where the
       derived domestic deposit interest (EDEPDOMQ) is negative. Each product's interest is replaced by the
       entity's previous-quarter interest scaled by the change in that product's balance (previous-quarter rate
       carried forward); with no previous quarter the values are set to NaN (the quarter is dropped).
    2. Restatement. Combinations of entities under common control are reported from the start of the year, so in
       the merger quarter the survivor's YTD includes the absorbed affiliates' earlier quarters, which the pro forma
       already counts from the affiliates' own filings (Bremer Bank NA 2014Q4). Detected for a merger quarter mq
       after Q1 from the rate on interest-bearing quarter-end balances (IB_Q, available from 2011Q4): the survivor's
       mq rate is at least 1.25 x both the combined (survivor + predecessors) mq-1 rate and its mq+1 rate, AND
       removing the predecessors' YTD brings it closer to those neighbours (log distance to their geometric mean).
       A rate-driven rise lies between its neighbours and is not flagged; interest expense alone cannot tell a
       Q2 restatement from one quarter of rate drift. The predecessors' YTD at mq-1, plus the pro-rata pre-merger
       part of mq that the pro forma adds (frac x predecessor mq-1), is subtracted per product.

    Returns the repaired frame and a log (one row per repaired cert-quarter). Never zero-fills."""
    if not set(YTD_REPAIR_COLS) <= set(fin.columns):
        return fin, pd.DataFrame(columns=["CERT", "REPDTE", "case", "detail"])
    f = fin.copy()
    f["q"] = pd.to_datetime(f.REPDTE.astype(str)).dt.to_period("Q")
    f["_order"] = range(len(f))
    t = f.set_index(["CERT", "q"]).sort_index()
    log = []

    def derive():
        t["NMD_IE"] = t.TRAN_IE + t.SAV_IE
        t["EDEPDOMQ"] = t.TRAN_IE + t.SAV_IE + t.TIME_IE
        t["EDEPFORQ"] = t.FOR_IE

    for c, q in list(t.index[t.EDEPDOMQ < 0]):
        before = t.at[(c, q), "EDEPDOMQ"]
        if (c, q - 1) in t.index:
            for ie, bal in YTD_REPAIR_COLS.items():
                pb, cb, pi = t.at[(c, q - 1), bal], t.at[(c, q), bal], t.at[(c, q - 1), ie]
                t.at[(c, q), ie] = pi * cb / pb if pb else (0.0 if pi == 0 and cb == 0 else float("nan"))
            how = "previous-quarter rate carried forward" if pd.notna(t.at[(c, q), "TIME_IE"] + t.at[(c, q), "TRAN_IE"]
                                                                     + t.at[(c, q), "SAV_IE"]) else "balance missing: set missing"
        else:
            for ie in YTD_REPAIR_COLS:
                t.at[(c, q), ie] = float("nan")
            how = "no previous quarter: set missing"
        derive()
        log.append({"CERT": c, "REPDTE": int(q.end_time.strftime("%Y%m%d")), "case": "restart",
                    "detail": f"EDEPDOMQ {before:.0f} -> {t.at[(c, q), 'EDEPDOMQ']:.0f} ({how})"})
    derive()
    tot = t.EDEPDOMQ + t.EDEPFORQ
    h = hist.assign(eff=pd.to_datetime(hist.EFFDATE).dt.tz_localize(None))
    h["mq"] = h.eff.dt.to_period("Q")
    for (s, mq), g in h.groupby(["ACQ_CERT", "mq"]):
        if mq.quarter == 1 or any((s, x) not in t.index for x in (mq - 1, mq, mq + 1)):
            continue
        preds = [int(p) for p in g.OUT_CERT if (int(p), mq - 1) in t.index]
        if not preds:
            continue
        prior = [pd.Period(f"{mq.year}Q{k}") for k in range(1, mq.quarter)]
        ytd = sum(tot.get((p, k), 0.0) for p in preds for k in prior)
        days = (mq.end_time.normalize() - mq.start_time).days + 1
        pro_rata = sum((e.eff - mq.start_time).days / days * tot.get((int(e.OUT_CERT), mq - 1), 0.0)
                       for _, e in g.iterrows())
        ib = t.IB_Q
        r_prev = (tot[(s, mq - 1)] + sum(tot[(p, mq - 1)] for p in preds)) / (
            ib[(s, mq - 1)] + sum(ib[(p, mq - 1)] for p in preds))
        r_cur, r_next = tot[(s, mq)] / ib[(s, mq)], tot[(s, mq + 1)] / ib[(s, mq + 1)]
        r_cor = (tot[(s, mq)] - ytd - pro_rata) / ib[(s, mq)]
        if not (ytd > 0 and r_prev > 0 and r_next > 0 and r_cor > 0 and r_cur >= 1.25 * max(r_prev, r_next)):
            continue
        mid = np.sqrt(r_prev * r_next)
        if abs(np.log(r_cor / mid)) >= abs(np.log(r_cur / mid)):
            continue
        before = tot[(s, mq)]
        for ie in YTD_REPAIR_COLS:
            sub = 0.0
            for _, e in g.iterrows():
                p = int(e.OUT_CERT)
                if (p, mq - 1) not in t.index:
                    continue
                frac = (e.eff - mq.start_time).days / days
                sub += sum(t[ie].get((p, k), 0.0) for k in prior) + frac * t.at[(p, mq - 1), ie]
            t.at[(s, mq), ie] -= sub
        derive()
        log.append({"CERT": s, "REPDTE": int(mq.end_time.strftime("%Y%m%d")), "case": "restatement",
                    "detail": f"total IE {before:.0f} -> {t.at[(s, mq), 'EDEPDOMQ'] + t.at[(s, mq), 'EDEPFORQ']:.0f};"
                              f" predecessors {preds}; their YTD {ytd:.0f}; quarterly rate % {400 * r_prev:.2f} /"
                              f" {400 * r_cur:.2f} -> {400 * r_cor:.2f} / {400 * r_next:.2f} (mq-1 / mq / mq+1)"})
    out = t.reset_index().sort_values("_order").set_index(fin.index)[fin.columns]
    return out, pd.DataFrame(log, columns=["CERT", "REPDTE", "case", "detail"])


def make_source_class(bd, fin, hist, prior_fallback=None):
    """`prior_fallback` ({CERT: DEP at TD_FALLBACK_PERIOD}, $ thousands): one-point 2012Q1 fallback for the
    total-deposit build (owner decision 2026-11-25, doc P12). Such a cert gets a quarter-end the quarter before,
    with DEP equal to its own 2012Q1 DEP and interest expense missing (NaN, never 0). The survivor's two-point
    average for 2012Q1 then includes the predecessor; its 2011Q4 pro forma rate is NaN and the row is dropped
    (2011Q4 is outside the sample, doc 4.4)."""
    fb_q = pd.Period(TD_FALLBACK_PERIOD, "Q") - 1

    class FfiecSource(bd.Fdic):
        def __init__(self, refresh=False, supplementary=None):   # no FDIC loader: no network, no raw cache
            self.refresh, self.fin, self.hist = refresh, fin, hist
            self.supp = bd.load_supplementary(supplementary)      # FDIC supplementary transfers (issue #20), read only

        def series(self, cert):
            s = super().series(cert)
            if prior_fallback and cert in prior_fallback and fb_q not in s.index:
                s.loc[fb_q] = [prior_fallback[cert], float("nan")]
                s = s.sort_index()
            return s

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
    fin, ytd_log = repair_ytd_breaks(fin, hist)
    fb = fin[(fin.REPDTE == int(TD_FALLBACK_PERIOD.replace("-", ""))) & (fin.TD_FALLBACK > 0)]
    src = make_source_class(bd, fin, hist, prior_fallback=dict(zip(fb.CERT, fb.DEP)))
    outdir.mkdir(parents=True, exist_ok=True)
    bd.Fdic, bd.ROOT = src, outdir                  # in-memory only; build_dataset.py on disk is untouched
    data, events = bd.build(False, root / "data_build" / "raw" / "supplementary_transfer_events.csv")
    checks = bd.validate(data)
    for old in outdir.glob(f"*_{bd.VINTAGE}.*"):   # FDIC write() never overwrites a vintage; FFIEC outputs are rebuilt
        old.unlink()
    bd.write(data, events, checks)
    supp = root / "data_build" / "raw" / "supplementary_transfer_events.csv"
    build_hybrid(data, events, fin, hist, bd, supp, outdir)
    ytd_log.to_csv(outdir / f"ytd_repairs_{bd.VINTAGE}.csv", index=False)
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
    """Interest-bearing deposit-rate dataset on the Schedule RC base (doc 6.4, owner decision 2026-11-25), plus pro
    forma product rates. Every series is folded with `pro_forma_ib` using the Mode A/B decisions of the total-deposit
    build (made on DEP), so the event set is identical by construction.

    Quarter-end series (interest-bearing RCON6636 + RCFN6636, its legs nmd / time / for, and the reconciling total
    IB + NIB) are folded first and then two-point averaged on the pro forma series, exactly as the origin averages
    DEP, so the reconciling total equals the origin's dep_avg_pf. 2012Q1 one-point fallback: a predecessor whose
    first Call Report is 2012Q1 (thrifts, TFR to 2011Q4) gets its 2012Q1 quarter-end balances as its 2011Q4 value
    (balances only; doc 5.4). RC-K series (former hybrid A_HYB, tran, sav) are averages and are folded as such."""
    modes = {}
    for r in events.itertuples():
        modes.setdefault((int(r.predecessor_cert), int(r.survivor_cert), str(r.effective_date)), r.mode_applied)

    qcols = ["IB_Q", "TOT_Q"] + [f"{n.upper()}_BAL" for n in QE_PRODUCTS]
    fb = fin[(fin.REPDTE == int(TD_FALLBACK_PERIOD.replace("-", ""))) & (fin.TD_FALLBACK > 0)]
    synth = fb[["CERT"] + qcols].assign(REPDTE=int(pd.Period(TD_FALLBACK_PERIOD, "Q").__sub__(1)
                                                   .end_time.strftime("%Y%m%d")))
    fin_q = pd.concat([fin, synth], ignore_index=True)       # interest expense of the synthetic rows: never used

    def source(bal, ie=None, ie_for=True, frame=fin):
        f = frame.assign(DEP=frame[bal], EDEPDOMQ=frame[ie] if ie else 0.0,
                         EDEPFORQ=frame["EDEPFORQ"] if ie_for else 0.0)
        return make_source_class(bd, f, hist)(False, supplementary)

    def averaged(pf):                                        # two-point average on the pro forma quarter-ends
        prev = pf["DEP"].reindex(pf.index - 1)              # the previous calendar quarter only, else NaN
        return (pf["DEP"] + prev.values) / 2

    src = source("IB_Q", "EDEPDOMQ", frame=fin_q)              # all interest-bearing deposits, incl. foreign
    qprod = {n: source(f"{n.upper()}_BAL", f"{n.upper()}_IE", ie_for=False, frame=fin_q) for n in QE_PRODUCTS}
    aprod = {n: source(f"{n.upper()}_BAL", f"{n.upper()}_IE", ie_for=False) for n in AVG_PRODUCTS}
    flag = source("TD_FALLBACK", None, ie_for=False)
    tot = source("TOT_Q", "EDEPDOMQ", frame=fin_q)             # reconciling total: IB + NIB quarter-ends
    hyb = source("A_HYB", "EDEPDOMQ")                           # former hybrid base (RC-K averages), reference only
    std = source("A", "EDEPDOMQ")                               # standalone entity-level two-point average
    rows = []
    for cert, name in bd.TARGETS.items():
        sa, pf = std.series(cert), pro_forma_ib(src, cert, modes)
        a_pf = averaged(pf)
        d = pd.DataFrame({"bank_name": name, "cert_number": cert,
                          "quarter": sa.index.to_timestamp(how="end").strftime("%Y-%m-%d"),
                          "ie": sa["ie"], "A": sa["DEP"], "rate_ib": 400 * sa["ie"] / sa["DEP"]}, index=sa.index)
        d = d.join(pd.DataFrame({"ie_ann_pf": 4 * pf["ie"], "A_pf": a_pf, "rate_ib_pf": 400 * pf["ie"] / a_pf,
                                 "n_predecessors_included": pf["n_pred"]}), how="left")
        for n, s in qprod.items():
            ppf = pro_forma_ib(s, cert, modes)
            avg = averaged(ppf)
            d[f"{n}_avg_pf"] = avg
            d[f"{n}_ie_ann_pf"] = 4 * ppf["ie"]
            d[f"rate_{n}_pf"] = (400 * ppf["ie"] / avg).where(avg != 0)
            if n in END_BALANCE_LEGS:
                eoq = ppf["DEP"]                                 # pro forma end-of-quarter balance
                d[f"{n}_eoq_pf"] = eoq
                d[f"rate_{n}_eoq_pf"] = (400 * ppf["ie"] / eoq).where(eoq != 0)
        for n, s in aprod.items():
            ppf = pro_forma_ib(s, cert, modes)
            d[f"{n}_avg_pf"] = ppf["DEP"]
            d[f"{n}_ie_ann_pf"] = 4 * ppf["ie"]
            d[f"rate_{n}_pf"] = 400 * ppf["ie"] / ppf["DEP"]
        tpf = pro_forma_ib(tot, cert, modes)
        d["tot_avg_pf"] = averaged(tpf)
        d["rate_total_recon_pf"] = 400 * tpf["ie"] / d["tot_avg_pf"]
        hpf = pro_forma_ib(hyb, cert, modes)
        d["A_hyb_pf"] = hpf["DEP"]
        d["rate_ib_hyb_pf"] = 400 * hpf["ie"] / hpf["DEP"]
        d["td_fallback_in_pf"] = pro_forma_ib(flag, cert, modes)["DEP"].gt(0).astype(int)
        f = fin[fin.CERT == cert].assign(q=lambda x: pd.to_datetime(x.REPDTE.astype(str)).dt.to_period("Q"))
        f = f.set_index("q").sort_index()
        d["rate_nmd_rck"] = 400 * f["NMD_IE"] / f["NMD_IB"]
        rows.append(d)
    out = pd.concat(rows).reset_index(drop=True)
    out = out[out.quarter >= HYBRID_START]
    ref = data[data.quarter >= HYBRID_START][["bank_name", "cert_number", "quarter", "rate_pf", "dep_avg_pf",
                                              "adjustment_mode", "merger_quarter", "pct_deposits_acquired_in_quarter"]]
    out = ref.rename(columns={"rate_pf": "rate_total_pf"}).merge(out.drop(columns="bank_name"),
                                                                  on=["cert_number", "quarter"], how="left")
    dropped = out[out.rate_ib_pf.isna()][["bank_name", "cert_number", "quarter"]]
    out = out.dropna(subset=["rate_ib_pf"])
    out.to_csv(outdir / f"ffiec_deposit_rates_hybrid_{bd.VINTAGE}.csv", index=False)
    dropped.to_csv(outdir / f"hybrid_dropped_quarters_{bd.VINTAGE}.csv", index=False)
    fb = fin[fin.TD_FALLBACK > 0][["CERT", "REPDTE"]]
    fb.to_csv(outdir / f"hybrid_td_fallback_{bd.VINTAGE}.csv", index=False)
    return out, dropped


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    data, events, checks = build_ffiec()
    log.info("wrote %d rows, %d events to %s; checks %s", len(data), len(events), OUT, checks)
    return 0


if __name__ == "__main__":
    sys.exit(main())
