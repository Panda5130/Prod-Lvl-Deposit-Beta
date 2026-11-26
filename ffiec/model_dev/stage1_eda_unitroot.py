"""Screen steps 1-3 (Prod-Lvl, v2-rc-6): EDA, ADF/KPSS unit-root grid, Zivot-Andrews breaks.

    python ffiec/model_dev/stage1_eda_unitroot.py

Reuses the origin grid, summary rule and Zivot-Andrews runner from diagnostics/stationarity_and_breaks.py
(imported, not edited): ADF c/n x AIC/BIC/t-stat, KPSS c/ct x auto/short/long; default ADF c/AIC with
KPSS c/auto, a series is classified only when both agree. Adds an I(2) check (the same grid on second
differences) and ACF/PACF of levels and first differences. Sample 2012Q1-2026Q3, five banks, plus FFT.

Outputs (ffiec/model_dev/outputs/v2-rc-6/stage1/): unit_root_grid.csv, unit_root_summary.csv,
i2_check.csv, zivot_andrews.csv, acf_pacf.csv, figures/*.png
"""
import importlib.util
import sys
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import acf, pacf

import screen_common as sc

spec = importlib.util.spec_from_file_location("sb", sc.ROOT / "diagnostics" / "stationarity_and_breaks.py")
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)

OUT = sc.OUT / "stage1"
NLAGS = 12


def series_set():
    df = pd.read_csv(sc.run_input())
    fft = sc.load_fft()
    out = {}
    for seg, y in sc.SEGMENTS.items():
        for bank in sc.BANKS:
            out[(seg, bank)] = sc.bank_series(df, bank, y)[y]
    idx = next(iter(out.values())).index
    out[("FFT", "FFT")] = fft.reindex(idx)
    return out, df, fft


def eda(series, fft):
    figs = OUT / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    for seg, y in sc.SEGMENTS.items():
        fig, ax = plt.subplots(figsize=(11, 5))
        for bank in sc.BANKS:
            s = series[(seg, bank)]
            ax.plot(s.index.to_timestamp(how="end"), s.values, label=sc.SHORT[bank], linewidth=1.5)
        f = series[("FFT", "FFT")]
        ax.plot(f.index.to_timestamp(how="end"), f.values, color="black", linestyle="--", linewidth=1.8, label="FFT")
        ax.set_title(f"{y} (five banks) vs FFT, 2012Q1-2026Q3")
        ax.set_ylabel("percent")
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left", fontsize=8)
        fig.savefig(figs / f"{seg}_rates_vs_FFT.png", dpi=120, bbox_inches="tight")
        plt.close(fig)
    rows = []
    for (seg, bank), s in series.items():
        fig, axes = plt.subplots(2, 2, figsize=(10, 6))
        for j, (lab, v) in enumerate((("level", s), ("diff", s.diff().dropna()))):
            a, p = acf(v, nlags=NLAGS), pacf(v, nlags=NLAGS, method="ywm")
            band = 1.96 / np.sqrt(len(v))
            for k in range(1, NLAGS + 1):
                rows.append([seg, bank, lab, k, a[k], p[k], band])
            for i, (name, vals) in enumerate((("ACF", a), ("PACF", p))):
                ax = axes[i, j]
                ax.bar(range(1, NLAGS + 1), vals[1:], color="#1f4e79")
                ax.axhline(band, color="red", linestyle=":"), ax.axhline(-band, color="red", linestyle=":")
                ax.set_title(f"{name} of {lab}", fontsize=9)
        fig.suptitle(f"{sc.SHORT.get(bank, bank)} {seg}", fontsize=10)
        fig.tight_layout()
        fig.savefig(figs / f"acf_pacf_{seg}_{sc.SHORT.get(bank, bank).replace('&', 'and').replace(' ', '_')}.png", dpi=100)
        plt.close(fig)
    pd.DataFrame(rows, columns=["segment", "bank_name", "transform", "lag", "acf", "pacf", "band_95"]).to_csv(
        OUT / "acf_pacf.csv", index=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    series, df, fft = series_set()
    eda(series, fft)
    grids, summaries, i2, breaks = [], [], [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for (seg, bank), s in series.items():
            grid = sb.unit_root_grid(s).assign(segment=seg, bank_name=bank)
            grids.append(grid)
            summaries.append({"segment": seg, "bank_name": bank, "n": len(s), **sb.summarise(grid)})
            # I(2) check: the same grid on first differences; its "I(1)" rows test the second difference.
            g2 = sb.unit_root_grid(s.diff().dropna())
            d2 = g2[g2.order == "I(1)"]
            adf = d2[(d2.test == "ADF") & (d2.regression == "c") & (d2.lag_rule == "AIC")].iloc[0]
            kp = d2[(d2.test == "KPSS") & (d2.regression == "c") & (d2.lag_rule == "auto")].iloc[0]
            i2.append({"segment": seg, "bank_name": bank, "D2 ADF c/AIC p": adf.p_value, "D2 KPSS c/auto p": kp.p_value,
                       "D2 ADF stationary share": f"{int(d2[d2.test == 'ADF'].indicates_stationary.sum())}/6",
                       "D2 KPSS stationary share": f"{int(d2[d2.test == 'KPSS'].indicates_stationary.sum())}/6",
                       "I(2) under default": not (adf.indicates_stationary and kp.indicates_stationary)})
            breaks.append(sb.zivot(s, s.index).assign(segment=seg, bank_name=bank))
    front = ["segment", "bank_name"]
    for d, name in ((pd.concat(grids), "unit_root_grid.csv"), (pd.DataFrame(summaries), "unit_root_summary.csv"),
                    (pd.DataFrame(i2), "i2_check.csv"), (pd.concat(breaks), "zivot_andrews.csv")):
        d[front + [c for c in d.columns if c not in front]].to_csv(OUT / name, index=False)
    print(pd.DataFrame(summaries)[["segment", "bank_name", "I(0) ADF c/AIC p", "I(0) KPSS c/auto p",
                                   "I(1) ADF c/AIC p", "I(1) KPSS c/auto p", "classification"]].round(4).to_string())
    print(pd.DataFrame(i2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
