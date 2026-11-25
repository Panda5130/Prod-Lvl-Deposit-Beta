"""Denominator sensitivity tests of doc section 6.5 (reproduces Tests A, B and D).

    python -I ffiec/sweep_sensitivity.py

Rebuilds the hybrid dataset into ffiec/outputs/sweep_sensitivity/ (the committed outputs are not touched) with three
extra RC-K-style legs, each an entity-level two-point average folded pro forma as an average (as section 6.5 ran):
  swlb  lower bound on swept noninterest-bearing balances, max(RCON6631 - RCON2215, 0), capped at RCONB563
  swpe  point estimate, max(RCON6631 - (RCON2215 - RCON3485), 0), capped at RCONB563
  ibrc  RCON6636 + RCFN6636 (the Schedule RC base, entity-level averaged)
and prints the tables (also written to report.txt in that folder). The "hybrid" base is A_hyb_pf. The production RC base (A_pf) folds quarter-ends first and
averages after (doc 6.6); it differs from ibrc only in merger and 2012Q1 fallback quarters.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FFIEC = Path(__file__).resolve().parent
sys.path.insert(0, str(FFIEC / "data_build"))
import build_ffiec as b  # noqa: E402

OUTDIR = FFIEC / "outputs" / "sweep_sensitivity"
_orig = b.hybrid_denominator


def _with_sweep_legs(w):
    w = _orig(w)
    q = pd.PeriodIndex(pd.to_datetime(w.period), freq="Q")
    key_prev = pd.MultiIndex.from_arrays([w.rssd.values, q - 1])

    def two_point(x):                       # same prior-quarter rule and 2012Q1 fallback as hybrid_denominator
        ser = pd.Series(x.values, index=pd.MultiIndex.from_arrays([w.rssd.values, q]))
        ser = ser[~ser.index.duplicated()]
        prev = pd.Series(ser.reindex(key_prev).values, index=w.index)
        fb = (w.period == b.TD_FALLBACK_PERIOD) & ~pd.Series(key_prev.isin(ser.index), index=w.index)
        return (x + prev.where(~fb, x)) / 2

    w["SWLB"] = two_point((w.RCON6631 - w.RCON2215).clip(lower=0)).clip(upper=w.RCONB563)
    w["SWPE"] = two_point((w.RCON6631 - (w.RCON2215 - w.RCON3485)).clip(lower=0)).clip(upper=w.RCONB563)
    w["IBRC"] = two_point(w.IB_Q)
    w["ZERO"] = 0.0
    return w


def build():
    b.hybrid_denominator = _with_sweep_legs
    extra = {"swlb": ("SWLB", "ZERO"), "swpe": ("SWPE", "ZERO"), "ibrc": ("IBRC", "ZERO")}
    b.AVG_PRODUCTS = {**b.AVG_PRODUCTS, **extra}
    b.PRODUCTS = {**b.PRODUCTS, **extra}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    b.build_ffiec(outdir=OUTDIR)
    keep = OUTDIR / "ffiec_deposit_rates_hybrid_v2.csv"
    for f in OUTDIR.iterdir():                          # the rest are by-products of the full rebuild
        if f != keep and f.name != "report.txt":
            f.unlink()
    return pd.read_csv(keep)


def report(h):
    h = h.assign(bank=h.bank_name.str.split().str[0], yr=h.quarter.str[:4].astype(int))
    h["per"] = pd.cut(h.yr, [2011, 2019, 2021, 2026], labels=["2012-19", "2020-21", "2022-26"])
    nib = h.tot_avg_pf - h.A_pf                         # two-point NIB average, pro forma
    base = {"hybrid": h.A_hyb_pf, "hybrid - lower bound": h.A_hyb_pf - h.swlb_avg_pf,
            "hybrid - point estimate": h.A_hyb_pf - h.swpe_avg_pf, "RC 6636": h.ibrc_avg_pf}
    rate = {k: 100 * h.ie_ann_pf / v for k, v in base.items()}
    print("Test A: gap = (base + NIB average) / dep_avg_pf - 1, %; rate vs RC base, bp")
    for k, v in base.items():
        g = 100 * ((v + nib) / h.dep_avg_pf - 1)
        bp = 100 * (rate[k] - rate["RC 6636"])
        print(f"  {k:24s} gap median {g.median():6.1f} (p5 {np.percentile(g, 5):6.1f}, p95 {np.percentile(g, 95):6.1f});"
              f" bp vs RC, bank medians {bp.groupby(h.bank).median().min():6.1f} to {bp.groupby(h.bank).median().max():6.1f}")
        print(h.assign(g=g).pivot_table(index="bank", columns="per", values="g", aggfunc="median",
                                        observed=False).round(1).to_string())
    print("\nTest B: rate rise as % of the RC-base rise")
    for lo, hi in [("2015-12-31", "2019-06-30"), ("2021-12-31", "2023-12-31")]:
        rise = {k: (r[h.quarter == hi].values - r[h.quarter == lo].values) for k, r in rate.items()}
        banks = h[h.quarter == hi].bank.values
        t = pd.DataFrame({k: 100 * rise[k] / rise["RC 6636"] for k in base if k != "RC 6636"}, index=banks).round(0)
        print(f"  {lo} to {hi}\n{t.to_string()}")
    k = h[(h.bank == "KeyBank") & h.quarter.between("2017-03-31", "2021-12-31")]
    nmd_ie = k.tran_ie_ann_pf + k.sav_ie_ann_pf
    nmd_bal = k.tran_avg_pf + k.sav_avg_pf
    print("\nTest D: KeyBank transaction share of NMD balance and interest, %")
    print(f"  balance {100 * (k.tran_avg_pf / nmd_bal).min():.1f} to {100 * (k.tran_avg_pf / nmd_bal).max():.1f};"
          f" interest {100 * (k.tran_ie_ann_pf / nmd_ie).min():.1f} to {100 * (k.tran_ie_ann_pf / nmd_ie).max():.1f};"
          f" max transaction rate {k.rate_tran_pf.max():.2f}%")


if __name__ == "__main__":
    import contextlib
    import io
    buf = io.StringIO()
    data = build()
    with contextlib.redirect_stdout(buf):
        report(data)
    (OUTDIR / "report.txt").write_text(buf.getvalue(), encoding="utf-8")
    print(buf.getvalue())
