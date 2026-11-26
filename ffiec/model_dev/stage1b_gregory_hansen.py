"""Screen step 4 (Prod-Lvl, v2-rc-6): Gregory-Hansen cointegration tests with one unknown break.

    python ffiec/model_dev/stage1b_gregory_hansen.py [--reps 2000]

Uses model_form/gregory_hansen.py unchanged (C, C/T, C/S, C/S/T; ADF*, Zt*, Za*; trimming 15%; ADF lags by
AIC, max 4). Finite-sample critical values are simulated as in the origin (2,000 replications, same seed), at
this sample's length T = 59 (origin: 62). They govern; the asymptotic values are reported alongside.

Outputs (ffiec/model_dev/outputs/v2-rc-6/stage1/): gregory_hansen.csv, gregory_hansen_cv_sim.csv,
gregory_hansen_summary.csv
"""
import argparse
import sys

import pandas as pd

import screen_common as sc

sys.path.insert(0, str(sc.ROOT / "model_form"))
import gregory_hansen as gh  # noqa: E402

OUT = sc.OUT / "stage1"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(sc.run_input())
    fft = sc.load_fft()
    n = int(df.groupby("bank_name").size().iloc[0])
    cv = {m: gh.simulate_cv(n, m, a.reps) for m in gh.MODELS}
    pd.DataFrame([{"T": n, "model": m, "statistic": f"{k}*", "cv_1": v[0], "cv_5": v[1], "cv_10": v[2]}
                  for m, d in cv.items() for k, v in d.items()]).to_csv(OUT / "gregory_hansen_cv_sim.csv", index=False)
    rows = []
    for seg, y in sc.SEGMENTS.items():
        for bank in sc.BANKS:
            data = sc.bank_series(df, bank, y, fft)
            rows += [{"segment": seg, "bank_name": bank, **r} for r in gh.run(data, y, sc.X, cv)]
    full = pd.DataFrame(rows)
    full.to_csv(OUT / "gregory_hansen.csv", index=False)
    adf = full[full.statistic == "ADF*"]
    summ = adf.pivot_table(index=["segment", "bank_name"], columns="model", values="value", aggfunc="first")
    brk = adf.pivot_table(index=["segment", "bank_name"], columns="model", values="break_quarter", aggfunc="first")
    summ = summ.join(brk, rsuffix=" break")
    summ["any_reject_5_sim (any stat)"] = full.groupby(["segment", "bank_name"]).reject_5_sim.any()
    summ["ADF*_reject_5_sim"] = adf.groupby(["segment", "bank_name"]).reject_5_sim.any()
    summ.to_csv(OUT / "gregory_hansen_summary.csv")
    print(summ.round(2).to_string())
    print(full[full.reject_5_sim][["segment", "bank_name", "model", "statistic", "value", "cv_5_sim", "break_quarter"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
