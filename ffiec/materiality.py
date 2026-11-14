"""Materiality of the FFIEC source: rate on RC-K quarterly-average balances vs the current 2-point average rate.

    python ffiec/materiality.py

Per target bank, 2008Q1 on:
  rate_2pt  = FFIEC standalone deposit_rate (400 x quarterly deposit IE / mean of current and prior total deposits)
  rate_rck  = 400 x domestic deposit IE / RC-K quarterly-average interest-bearing domestic deposits
              (RCON3485 + RCONB563 + RCONA529 + RCONA514, available to 2016Q4 only).
BASIS NOTE: rate_rck's denominator excludes noninterest-bearing deposits, so its LEVEL is higher than rate_2pt by
construction; compare volatility and correlation (and the level gap only as a basis effect). No MDRM code was
found for RC-K time-deposit averages from 2017 on or for the noninterest-bearing average (see items.py), so
rate_rck is a coverage gap from 2017Q1; the 2026Q3 quarter is shown from the 2-point rate only (the quarter the
source adds). Writes ffiec/outputs/materiality_summary.csv, materiality_coverage.csv. Reads only ffiec/.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "data_build"))
from items import RCK_DOM_AVG, ri_dom_codes  # noqa: E402

FFIEC = HERE
RCK_CODES = RCK_DOM_AVG["old"]
PRODUCT_GROUPS = {"transaction": ["RIAD4508"], "savings_mmda": ["RIAD0093"],
                  "time": ["RIADA517", "RIADA518", "RIADHK03", "RIADHK04"], "foreign": ["RIAD4172"]}


def rck_rates(quarterly, cert_rssd):
    w = quarterly.pivot_table(index=["rssd", "period"], columns="item", values="value", aggfunc="first")
    w = w.reset_index()
    rows = []
    for _, r in w.iterrows():
        ie = [r.get(c) for c in ri_dom_codes(r["period"])]
        avg = [r.get(c) for c in RCK_CODES]
        ie_ok = not any(pd.isna(v) for v in ie)
        avg_ok = r["period"] <= "2016-12-31" and not any(pd.isna(v) for v in avg)
        rows.append({"rssd": r["rssd"], "period": r["period"], "ie_dom": sum(ie) if ie_ok else float("nan"),
                     "rck_avg_ib": sum(avg) if avg_ok else float("nan"),
                     "rck_rate": 400 * sum(ie) / sum(avg) if ie_ok and avg_ok and sum(avg) else float("nan"),
                     "products_present": ",".join(g for g, cs in PRODUCT_GROUPS.items()
                                                  if any(pd.notna(r.get(c)) for c in cs))})
    out = pd.DataFrame(rows)
    out["cert_number"] = out.rssd.map({r: c for c, r in cert_rssd.items() if r})
    out["quarter"] = out.period
    return out


def summarize(base, rck):
    """base: FFIEC standalone output (deposit_rate); rck: rck_rates output."""
    m = base[["cert_number", "bank_name", "quarter", "deposit_rate"]].merge(
        rck[["cert_number", "quarter", "rck_rate"]], on=["cert_number", "quarter"], how="left")
    rows = []
    for (cert, name), g in m.groupby(["cert_number", "bank_name"]):
        c = g.dropna(subset=["rck_rate", "deposit_rate"])
        rows.append({"cert_number": cert, "bank_name": name, "n_total": len(g), "n_with_rck": len(c),
                     "last_quarter": g.quarter.max(),
                     "mean_2pt": c.deposit_rate.mean(), "mean_rck": c.rck_rate.mean(),
                     "level_gap_basis_effect": (c.rck_rate - c.deposit_rate).mean(),
                     "std_2pt": c.deposit_rate.std(), "std_rck": c.rck_rate.std(),
                     "corr": c.deposit_rate.corr(c.rck_rate) if len(c) > 2 else float("nan"),
                     "std_dq_2pt": c.deposit_rate.diff().std(), "std_dq_rck": c.rck_rate.diff().std()})
    return pd.DataFrame(rows)


def main():
    out = FFIEC / "outputs"
    cr = pd.read_csv(FFIEC / "data" / "cert_rssd.csv")
    cert_rssd = {int(c): (int(r) if pd.notna(r) else None) for c, r in zip(cr.cert, cr.rssd)}
    quarterly = pd.read_csv(FFIEC / "data" / "ffiec_items_quarterly.csv", dtype={"period": str})
    rck = rck_rates(quarterly, cert_rssd)
    base = pd.read_csv(out / "consolidated_fdic_quarterly_financials_2008-2026_merger_adjusted_v2.csv")
    s = summarize(base, rck)
    s.to_csv(out / "materiality_summary.csv", index=False)
    rck[rck.cert_number.notna()].to_csv(out / "materiality_coverage.csv", index=False)
    print(s.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
