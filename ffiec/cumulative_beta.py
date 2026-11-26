"""Cumulative (balance-weighted) beta of the two Prod-Lvl segments and its gap to the High-Level beta (doc 6.11).

    python -I ffiec/cumulative_beta.py --segment-betas <csv: bank_name, segment (nmd|time), beta> --out <csv>

To be run only after the segment ECMs are estimated: the segment betas are the champions' long-run coefficients.
Weights are each bank's pro forma two-point average balances from ffiec/outputs/ffiec_deposit_rates_hybrid_v2.csv,
averaged over the estimation sample 2012Q1 to 2026Q3:
  cum_beta_ib    = (B_nmd b_nmd + B_time b_time) / (B_nmd + B_time)   shares of interest-bearing deposits (sum to 1)
  cum_beta_total = (B_nmd b_nmd + B_time b_time) / B_total            shares of total deposits; noninterest-bearing
                                                                      deposits and foreign offices at beta 0
B_nmd = mean(nmd_avg_pf), B_time = mean(time_avg_pf), B_total = mean(dep_avg_pf). The High-Level beta (champion
long-run beta of the total-deposit rate, ffiec/reference/high_level_champion_betas.csv) compares with cum_beta_total.
Writes the csv given by --out (nothing is written under ffiec/outputs).
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

FFIEC = Path(__file__).resolve().parent
BANKS = ["First Horizon Bank", "Huntington National Bank", "KeyBank National Association",
         "Manufacturers and Traders Trust Company", "Old National Bank"]                     # scope O7
START, END = "2012-03-31", "2026-09-30"


def cumulative(rates, segment_betas, hl):
    rows = []
    for bank in BANKS:
        g = rates[(rates.bank_name == bank) & rates.quarter.between(START, END)]
        sb = segment_betas[segment_betas.bank_name == bank].set_index("segment").beta
        b_nmd, b_time = float(sb["nmd"]), float(sb["time"])
        w_nmd, w_time, w_tot = g.nmd_avg_pf.mean(), g.time_avg_pf.mean(), g.dep_avg_pf.mean()
        cum_total = (w_nmd * b_nmd + w_time * b_time) / w_tot
        hl_beta = float(hl.loc[hl.bank_name == bank, "hl_beta"].iloc[0])
        rows.append({"bank_name": bank, "beta_nmd": b_nmd, "beta_time": b_time,
                     "share_nmd": w_nmd / w_tot, "share_time": w_time / w_tot,
                     "cum_beta_ib": (w_nmd * b_nmd + w_time * b_time) / (w_nmd + w_time),
                     "cum_beta_total": cum_total, "hl_beta": hl_beta, "gap_hl_minus_cum_total": hl_beta - cum_total})
    return pd.DataFrame(rows)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--segment-betas", required=True, help="csv with bank_name, segment (nmd/time), beta")
    ap.add_argument("--out", required=True, help="output csv path (development runs write to their own vintage dir)")
    a = ap.parse_args(argv)
    out = cumulative(pd.read_csv(FFIEC / "outputs" / "ffiec_deposit_rates_hybrid_v2.csv"),
                     pd.read_csv(a.segment_betas), pd.read_csv(FFIEC / "reference" / "high_level_champion_betas.csv"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(a.out, index=False)
    print(out.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
