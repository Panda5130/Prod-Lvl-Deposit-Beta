"""Cumulative (balance-weighted) deposit beta from the two Prod-Lvl segments, compared with the High-Level betas.

    python -I ffiec/cumulative_beta.py --fft <FFT_2011-2026.csv to 2026Q3> [--segment-betas <csv>]

Segment betas: from --segment-betas (columns bank_name, segment in {nmd, time}, beta), i.e. the Prod-Lvl ECM long-run
betas once estimated. Without it, PROVISIONAL betas are used: the slope of an OLS regression of the segment rate on a
constant and FFT, 2012Q1 to 2026Q3 (the long-run step of the Engle-Granger form, no dynamics).

Weights: sample-average pro forma two-point balances, 2012Q1 to 2026Q3 (nmd_avg_pf, time_avg_pf, dep_avg_pf).
  cum_beta_ib    = (B_nmd b_nmd + B_time b_time) / (B_nmd + B_time)    interest-bearing deposits only
  cum_beta_total = (B_nmd b_nmd + B_time b_time) / B_total             total deposits; noninterest-bearing at beta 0
                                                                       (foreign offices, <= 2.9%, also at 0)
cum_beta_total is the one comparable with the High-Level beta, which is the beta of the total-deposit rate.
Diagnostic: static_beta_total_rate is the same regression on the Call Report total-deposit rate (rate_total_pf), and
static_beta_hl_rate on the High-Level BankFind rate (rate_pf_clean, 2011Q1 to 2026Q2, the High-Level sample), so the
gap can be split into estimator (ECM vs static) and aggregation effects.

Writes ffiec/outputs/cumulative_beta_v2.csv.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

FFIEC = Path(__file__).resolve().parent
ROOT = FFIEC.parent
BANKS = ["First Horizon Bank", "Huntington National Bank", "KeyBank National Association",
         "Manufacturers and Traders Trust Company", "Old National Bank"]                     # scope O7
START, END = "2012-03-31", "2026-09-30"


def static_beta(quarters, y, fft):
    x = pd.PeriodIndex(pd.to_datetime(quarters), freq="Q").map(fft).astype(float)
    ok = ~(np.isnan(x) | np.isnan(y))
    return float(np.polyfit(np.asarray(x)[ok], np.asarray(y)[ok], 1)[0])


def cumulative(rates, fft, hl, hl_rates=None, segment_betas=None):
    rows = []
    for bank in BANKS:
        g = rates[(rates.bank_name == bank) & rates.quarter.between(START, END)]
        if segment_betas is not None:
            sb = segment_betas[segment_betas.bank_name == bank].set_index("segment").beta
            b_nmd, b_time, basis = float(sb["nmd"]), float(sb["time"]), "model"
        else:
            b_nmd = static_beta(g.quarter, g.rate_nmd_eoq_pf.values, fft)
            b_time = static_beta(g.quarter, g.rate_time_eoq_pf.values, fft)
            basis = "provisional static OLS"
        w_nmd, w_time, w_tot = g.nmd_avg_pf.mean(), g.time_avg_pf.mean(), g.dep_avg_pf.mean()
        row = {"bank_name": bank, "segment_beta_basis": basis, "beta_nmd": b_nmd, "beta_time": b_time,
               "share_nmd": w_nmd / w_tot, "share_time": w_time / w_tot, "share_other": 1 - (w_nmd + w_time) / w_tot,
               "cum_beta_ib": (w_nmd * b_nmd + w_time * b_time) / (w_nmd + w_time),
               "cum_beta_total": (w_nmd * b_nmd + w_time * b_time) / w_tot,
               "static_beta_total_rate": static_beta(g.quarter, g.rate_total_pf.values, fft)}
        h = hl[hl.bank_name == bank].iloc[0]
        row.update({"hl_beta": h.hl_beta, "hl_champion": h.hl_champion})
        if hl_rates is not None:
            r = hl_rates[(hl_rates.bank_name == bank) & hl_rates.quarter.between("2011-03-31", "2026-06-30")]
            row["static_beta_hl_rate"] = static_beta(r.quarter, r.rate_pf_clean.values, fft)
        row["gap_hl_minus_cum_total"] = row["hl_beta"] - row["cum_beta_total"]
        rows.append(row)
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--fft", required=True, help="FFT csv (quarter, FFT) covering 2011Q1 to 2026Q3")
    ap.add_argument("--segment-betas", help="csv with bank_name, segment (nmd/time), beta")
    a = ap.parse_args(argv)
    f = pd.read_csv(a.fft)
    fft = dict(zip(pd.PeriodIndex(f.iloc[:, 0], freq="Q"), f.FFT))
    rates = pd.read_csv(FFIEC / "outputs" / "ffiec_deposit_rates_hybrid_v2.csv")
    hl = pd.read_csv(FFIEC / "reference" / "high_level_champion_betas.csv")
    hl_path = ROOT / "consolidated_fdic_quarterly_financials_2008-2026_merger_adjusted.csv"
    hl_rates = pd.read_csv(hl_path) if hl_path.exists() else None
    sb = pd.read_csv(a.segment_betas) if a.segment_betas else None
    out = cumulative(rates, fft, hl, hl_rates, sb)
    out.to_csv(FFIEC / "outputs" / "cumulative_beta_v2.csv", index=False)
    with pd.option_context("display.width", 250):
        print(out.drop(columns="hl_champion").round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
