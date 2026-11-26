"""Screen steps 7-9 (Prod-Lvl, v2-rc-6): champions, residual diagnostics, treatment tests, segment betas.

    python ffiec/model_dev/stage3_champions.py

Reads the stage-2 outputs (base run, and the covid / start-2012Q2 reruns if present) and writes to
ffiec/model_dev/outputs/v2-rc-6/stage3/:
    champions.csv               the out-of-sample champion per bank and segment (default rule), its terms,
                                lambda, theta, MAE ratings (peer-derived limits, provisional) and theta rating
    champion_estimates.csv      the champions' coefficient rows
    residual_diagnostics.csv    residual ACF (lags 1-8) and Ljung-Box Q at lags 4 and 8 (champion residuals)
    treatment_tests.csv         dummy tests added to each champion (data never edited):
                                  AO_P13  M&T time 2022Q2-Q3 additive outlier (dD_t and D_{t-1})
                                  AO_P15  Huntington time 2026Q2 additive outlier (dD_t and D_{t-1})
                                  merger  impulse on merger_quarter = 1 (flag only; origin: pro forma, no dummy)
                                  start2012Q2  champion refit on 2012Q2-2026Q3 (fallback-row sensitivity)
    covid_decision.csv          D6 retest with the origin's three-part exclusion rule
    start2012Q2_comparison.csv  full rerun from 2012Q2: champion and theta against the base run
    segment_betas.csv           bank_name, segment, beta (champion long-run theta) for cumulative_beta.py
Dummy refits use the champion's own regressors (bank_plots.regressor) plus the dummy columns, by OLS. For a
lambda-split (asymmetric TAR) champion the error-correction terms are held at the champion's long-run
coefficients, so the dummy test is conditional on them (recorded in the `note` column).
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf

import screen_common as sc

OUT = sc.OUT / "stage3"
os.environ["DEPOSIT_OUTPUT_VINTAGE"] = str(OUT)  # bank_plots: any default path stays inside ffiec/
sys.path.insert(0, str(sc.ROOT))
sys.path.insert(0, str(sc.ROOT / "MAE_Backtesting"))
import bank_plots as bp  # noqa: E402

KEYS = ["bank_name", "test_name", "IC/selected lag", "trend type"]
MAE_DIR = "MAE_Backtesting/output/out_of_sample"
BETA_DIR = "Beta_Backtesting/output/out_of_sample"
AO = {("time", "Manufacturers and Traders Trust Company"): ("AO_P13", "2022Q2", "2022Q3"),
      ("time", "Huntington National Bank"): ("AO_P15", "2026Q2", "2026Q2")}


def seg_dir(tag, seg):
    return sc.OUT / tag / seg


def load(tag, seg):
    d = seg_dir(tag, seg)
    if not (d / MAE_DIR / "selection_oos_scores_8Q.csv").exists():
        return None
    scores = pd.read_csv(d / MAE_DIR / "selection_oos_scores_8Q.csv")
    est = pd.concat([pd.read_csv(d / "ECM estimation results (det pruned).csv").assign(asymmetric=False),
                     pd.read_csv(d / "ECM asymmetric estimation results (det pruned).csv").assign(asymmetric=True)])
    multi = pd.read_csv(d / MAE_DIR / "backtest_multiorigin_assessment_8Q.csv")
    single = pd.read_csv(d / MAE_DIR / "backtest_assessment_8Q.csv")
    hstep = pd.read_csv(d / MAE_DIR / "backtest_multiorigin_8Q.csv")
    beta = pd.read_csv(d / BETA_DIR / "beta_backtest_multiorigin_assessment.csv")
    realized = d / BETA_DIR / "realized_beta_summary_8Q.csv"
    realized = pd.read_csv(realized) if realized.exists() else None
    return dict(scores=scores, est=est, multi=multi, single=single, hstep=hstep, beta=beta, realized=realized)


def champion_rows(r, bank):
    s = r["scores"]
    pick = s[(s.bank_name == bank) & s.pick.astype(bool)]
    if len(pick) != 1:
        raise ValueError(f"{bank}: {len(pick)} picks")
    p = pick.iloc[0]
    e = r["est"]
    rows = e[(e[KEYS].astype(str) == [bank, p["test_name"], p["IC/selected lag"], p["trend type"]]).all(axis=1)]
    return p, rows


def data_for(df, bank, y):
    g = df[df.bank_name == bank].copy()
    g.index = pd.PeriodIndex(pd.to_datetime(g.quarter), freq="Q")
    fft = sc.load_fft()
    out = g[[y]].astype(float)
    out[sc.X] = fft.reindex(out.index)
    return out, g


def design(data, y, rows):
    coefs = rows[~rows.term.str.startswith("LR: ")].set_index("term")["coef"]
    weights = bp.ect_weights(rows, y)
    X = pd.concat({t: bp.regressor(data, t, weights) for t in coefs.index}, axis=1)
    return X, coefs, weights is not None


def refit(data, y, rows, extra=None):
    X, coefs, split = design(data, y, rows)
    if extra is not None:
        X = pd.concat([X, extra], axis=1)
    frame = pd.concat([data[y].diff().rename("dy"), X], axis=1).dropna()
    return sm.OLS(frame["dy"], frame[X.columns]).fit(), coefs, split


def lr(res, y):
    lam = res.params.get(f"{y}.L1", np.nan)
    th = -res.params.get(f"{sc.X}.L1", np.nan) / lam if np.isfinite(lam) else np.nan
    return lam, th


def ao_columns(index, q1, q2, name):
    D = pd.Series(((index >= pd.Period(q1, "Q")) & (index <= pd.Period(q2, "Q"))).astype(float), index=index)
    return pd.DataFrame({f"{name}_dD": D.diff(), f"{name}_Dlag": D.shift(1)}, index=index)


def f_test(res, cols):
    R = np.zeros((len(cols), len(res.params)))
    for i, c in enumerate(cols):
        R[i, list(res.params.index).index(c)] = 1
    t = res.f_test(R)
    return float(np.squeeze(t.fvalue)), float(t.pvalue)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(sc.run_input())
    champs, ests, resid_rows, treat, betas = [], [], [], [], []
    warnings.simplefilter("ignore")
    for seg, y in sc.SEGMENTS.items():
        r = load("base", seg)
        for bank in sc.BANKS:
            p, rows = champion_rows(r, bank)
            ests.append(rows.assign(segment=seg))
            data, g = data_for(df, bank, y)
            model = " | ".join([p["test_name"], p["IC/selected lag"], p["trend type"]])
            ma = r["multi"][r["multi"].bank_name == bank].iloc[0]
            sw = r["single"][r["single"].bank_name == bank].iloc[0]
            bt = r["beta"][r["beta"].bank_name == bank].iloc[0]
            hs = r["hstep"][r["hstep"].bank_name == bank].sort_values("horizon_q")
            lrrows = rows[rows.term.str.startswith("LR: ")].set_index("term")
            coef = rows.set_index("term")
            theta_pos = lrrows.coef.get(f"LR: {sc.X}{bp.POS}", np.nan)
            theta_neg = lrrows.coef.get(f"LR: {sc.X}{bp.NEG}", np.nan)
            theta = lrrows.coef.get(f"LR: {sc.X}", np.nan)
            theta_se = (lrrows.coef / lrrows.t_stat).get(f"LR: {sc.X}", np.nan)
            champs.append({
                "segment": seg, "bank_name": bank, "champion": model, "asymmetric": bool(p["asymmetric"]),
                "n_params": p["n_params"], "terms": p["terms"],
                "lambda": p["lambda"], "lambda_pos": p["lambda_pos"], "lambda_neg": p["lambda_neg"],
                "theta": theta, "theta_se": theta_se, "theta_pos": theta_pos, "theta_neg": theta_neg,
                "theta_split": bool(p["theta_split"]), "lambda_split": bool(p["lambda_split"]),
                "in_sample_mae": p["in_sample_mae"], "oos_mean_hstep_mae": p["oos_mae"], "oos_se": p["oos_se"],
                "n_candidates": int((r["scores"].bank_name == bank).sum()),
                "n_admissible": int(r["scores"][(r["scores"].bank_name == bank)].admissible.sum()),
                "hstep_mae_1_8": " ".join(f"{v:.3f}" for v in hs.mae),
                "hstep_naive_1_8": " ".join(f"{v:.3f}" for v in hs.naive_mae),
                "worst_skill_ratio": ma.worst_skill_ratio, "worst_skill_h": ma.worst_skill_h,
                "skill_rating": ma.skill_rating, "absolute_rating_peer_limits": ma.absolute_rating,
                "mae_rating_peer_limits": ma.rating, "mae_reason": ma.reason,
                "single_window_mean": sw.mean_mae, "single_window_naive": sw.naive_mean_mae,
                "single_window_beats_naive": sw.horizons_beating_naive, "single_window_rating": sw.rating,
                "theta_stability_rating": bt.rating, "theta_stability_detail": bt.ratings_by_param,
                "theta_min_max_2020on": f"{bt.min_beta:.3f}-{bt.max_beta:.3f}",
                "theta_failing_origins": bt.failing_origins,
            })
            source = "champion theta"
            beta = theta
            if not np.isfinite(beta):
                # theta split: the champion has no single long-run beta (open item). Default: theta of the
                # symmetric specification the asymmetric champion was built from (same keys, no split).
                parent = r["scores"][(r["scores"].bank_name == bank)
                                     & (r["scores"].test_name == p["test_name"].removesuffix(" | asymmetric"))
                                     & (r["scores"]["IC/selected lag"] == p["IC/selected lag"])
                                     & (r["scores"]["trend type"] == p["trend type"])]
                beta = float(parent.theta.iloc[0])
                source = (f"theta split in champion (theta+ {theta_pos:.4f}, theta- {theta_neg:.4f}); default = "
                          f"symmetric parent {p['test_name'].removesuffix(' | asymmetric')} theta")
            betas.append({"bank_name": bank, "segment": seg, "beta": beta, "theta_pos": theta_pos,
                          "theta_neg": theta_neg, "source": source})

            # residual diagnostics -------------------------------------------------------------
            res, coefs, split = refit(data, y, rows)
            recon = float(np.max(np.abs(res.params[coefs.index] - coefs))) if not split else np.nan
            actual, pred = bp.predict(data, y, rows)
            e = actual - pred
            a = acf(e, nlags=8)
            lb = acorr_ljungbox(e, lags=[4, 8])
            resid_rows.append({"segment": seg, "bank_name": bank, "champion": model, "nobs": len(e),
                               **{f"acf_{k}": a[k] for k in range(1, 9)}, "acf_band_95": 1.96 / np.sqrt(len(e)),
                               "LB_Q4": lb.lb_stat.iloc[0], "LB_p4": lb.lb_pvalue.iloc[0],
                               "LB_Q8": lb.lb_stat.iloc[1], "LB_p8": lb.lb_pvalue.iloc[1],
                               "max_abs_resid": float(e.abs().max()), "max_abs_resid_quarter": str(e.abs().idxmax()),
                               "ols_refit_max_coef_diff": recon})

            # treatment tests ------------------------------------------------------------------
            note = "conditional on champion long-run (lambda-split TAR)" if split else ""
            lam0, th0 = lr(res, y)
            tests = []
            if (seg, bank) in AO:
                name, q1, q2 = AO[(seg, bank)]
                tests.append((name, f"additive outlier {q1}-{q2}: dD_t, D_t-1", ao_columns(data.index, q1, q2, name)))
            mq = pd.Series(g.merger_quarter.astype(float).values, index=data.index, name="merger_imp")
            if mq.sum() > 0:
                tests.append(("merger", f"impulse on {int(mq.sum())} merger quarter(s): "
                               + " ".join(str(q) for q in mq[mq > 0].index), mq.to_frame()))
            for name, desc, extra in tests:
                r2, _, _ = refit(data, y, rows, extra)
                cols = list(extra.columns)
                F, pF = f_test(r2, cols)
                lam1, th1 = lr(r2, y)
                treat.append({"segment": seg, "bank_name": bank, "test": name, "description": desc,
                              "F": F, "p_value": pF, "significant_5pct": pF < 0.05,
                              "dummy_coefs": " ".join(f"{c}={r2.params[c]:.4f} (p {r2.pvalues[c]:.3f})" for c in cols),
                              "lambda_before": lam0, "lambda_after": lam1, "theta_before": th0, "theta_after": th1,
                              "note": note, "treatment": "flag only; champion and data unchanged"})
            # start-2012Q2 refit of the same champion
            sub = data.loc[pd.Period("2012Q2", "Q"):]
            r3, _, _ = refit(sub, y, rows)
            lam1, th1 = lr(r3, y)
            treat.append({"segment": seg, "bank_name": bank, "test": "start2012Q2",
                          "description": f"champion refit from 2012Q2 (fallback row {'present' if g.td_fallback_in_pf.iloc[0] else 'absent'})",
                          "F": np.nan, "p_value": np.nan, "significant_5pct": np.nan, "dummy_coefs": "",
                          "lambda_before": lam0, "lambda_after": lam1, "theta_before": th0, "theta_after": th1,
                          "note": note, "treatment": "sensitivity only"})
    pd.DataFrame(champs).to_csv(OUT / "champions.csv", index=False)
    pd.concat(ests).to_csv(OUT / "champion_estimates.csv", index=False)
    pd.DataFrame(resid_rows).to_csv(OUT / "residual_diagnostics.csv", index=False)
    pd.DataFrame(treat).to_csv(OUT / "treatment_tests.csv", index=False)
    b = pd.DataFrame(betas)
    b.to_csv(OUT / "segment_betas_detail.csv", index=False)
    b[["bank_name", "segment", "beta"]].to_csv(OUT / "segment_betas.csv", index=False)
    for side in ("theta_pos", "theta_neg"):  # theta-split sensitivity: the split champion's theta+ or theta-
        v = b.copy()
        v["beta"] = np.where(v[side].notna(), v[side], v.beta)
        v[["bank_name", "segment", "beta"]].to_csv(OUT / f"segment_betas_{side}.csv", index=False)
    covid_and_start()
    print(pd.DataFrame(champs)[["segment", "bank_name", "champion", "lambda", "theta", "theta_pos", "theta_neg",
                                "oos_mean_hstep_mae", "skill_rating", "mae_rating_peer_limits",
                                "theta_stability_rating"]].to_string())
    return 0


def covid_and_start():
    rows, srows = [], []
    for seg in sc.SEGMENTS:
        base = load("base", seg)
        cov = load("covid", seg)
        st = load("start2012Q2", seg)
        for bank in sc.BANKS:
            pb, rb_ = champion_rows(base, bank)
            mb = " | ".join([pb["test_name"], pb["IC/selected lag"], pb["trend type"]])
            bb = base["beta"][base["beta"].bank_name == bank].iloc[0].rating
            if cov is not None:
                pc, rc = champion_rows(cov, bank)
                mc = " | ".join([pc["test_name"], pc["IC/selected lag"], pc["trend type"]])
                survives = bool((rc.term == bp.COVID).any())
                bc = cov["beta"][cov["beta"].bank_name == bank].iloc[0].rating
                mae_ok = pc["oos_mae"] <= pb["oos_mae"] + pb["oos_se"]
                order = ["Green", "Amber", "Red"]
                beta_ok = order.index(bc) <= order.index(bb)
                n_surv = int(cov["est"][(cov["est"].bank_name == bank) & (cov["est"].term == bp.COVID)]
                             .drop_duplicates(KEYS).shape[0])
                rows.append({"segment": seg, "bank_name": bank, "champion_without": mb, "champion_with": mc,
                             "same_champion": mb == mc, "covid_in_champion": survives,
                             "covid_coef": rc.set_index("term").coef.get(bp.COVID, np.nan),
                             "covid_p": rc.set_index("term").p_value.get(bp.COVID, np.nan),
                             "models_keeping_covid": n_surv,
                             "oos_mae_without": pb["oos_mae"], "oos_se_without": pb["oos_se"], "oos_mae_with": pc["oos_mae"],
                             "theta_without": pb["theta"], "theta_with": pc["theta"],
                             "beta_rating_without": bb, "beta_rating_with": bc,
                             "rule1_survives": survives, "rule2_mae_within_1se": mae_ok, "rule3_beta_not_worse": beta_ok,
                             "decision": "include" if (survives and mae_ok and beta_ok) else "exclude"})
            if st is not None:
                ps, rs = champion_rows(st, bank)
                ms = " | ".join([ps["test_name"], ps["IC/selected lag"], ps["trend type"]])
                srows.append({"segment": seg, "bank_name": bank, "champion_2012Q1": mb, "champion_2012Q2": ms,
                              "same_champion": mb == ms, "theta_2012Q1": pb["theta"], "theta_2012Q2": ps["theta"],
                              "theta_pos_2012Q2": ps["theta_pos"], "theta_neg_2012Q2": ps["theta_neg"],
                              "lambda_2012Q1": pb["lambda"], "lambda_2012Q2": ps["lambda"],
                              "oos_mae_2012Q1": pb["oos_mae"], "oos_mae_2012Q2": ps["oos_mae"]})
    if rows:
        pd.DataFrame(rows).to_csv(OUT / "covid_decision.csv", index=False)
    if srows:
        pd.DataFrame(srows).to_csv(OUT / "start2012Q2_comparison.csv", index=False)


if __name__ == "__main__":
    sys.exit(main())
