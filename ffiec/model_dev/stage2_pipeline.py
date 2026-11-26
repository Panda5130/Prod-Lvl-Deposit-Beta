"""Screen steps 5-7 (Prod-Lvl, v2-rc-6): cointegration screen, ECM selection/estimation/pruning, backtests.

    python ffiec/model_dev/stage2_pipeline.py [--segments nmd time] [--start 2012Q1] [--tag base] [--covid]

Runs the origin scripts unchanged, as subprocesses, with explicit arguments (the Prod-Lvl data, the rebuilt
FFT, the segment's dependent column) and with DEPOSIT_OUTPUT_VINTAGE pointing at the segment's output folder,
so every default write of the origin code lands under ffiec/model_dev/outputs/v2-rc-6/<tag>/<segment>/:
    1. Co-integration Tests.py (baseline: trend c, max lag 4, EG/ARDL by AIC, Johansen det_order 0, k=1, case 3)
    2. FlaggedRates_co-integration_respecification.py (full grid, the five banks)
    3. ECM workflow.py (model screen p < 0.05, parameter screen, one-step ECM, short-run pruning,
       deterministic pruning after the screen without re-check, asymmetric variants)
    4. MAE_Backtesting/run_backtest.py --select out-of-sample --first-origin 2016Q1 --limits peer
       (peer limits from the five banks of the segment; the origin's approved fixed reference is NOT used)
    5. Beta_Backtesting/run_beta_backtest.py (theta stability from 2016Q1, then --realized)
--covid offers the covid_liq dummy (D6 retest) to estimation and the asymmetric variants.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

import screen_common as sc

PY = sys.executable


def run(cmd, env, log):
    print(">>", " ".join(map(str, cmd[1:])), flush=True)
    with open(log, "a") as fh:
        fh.write(">> " + " ".join(map(str, cmd)) + "\n")
        fh.flush()
        r = subprocess.run(list(map(str, cmd)), env=env, cwd=sc.ROOT, stdout=fh, stderr=subprocess.STDOUT)
    if r.returncode not in (0, 2):
        raise SystemExit(f"step failed ({r.returncode}): {cmd[1]}; see {log}")
    return r.returncode


def segment(seg, start, tag, covid):
    y = sc.SEGMENTS[seg]
    d = sc.OUT / tag / seg
    d.mkdir(parents=True, exist_ok=True)
    log = d / "pipeline.log"
    log.write_text("")
    env = sc.pipeline_env(d)
    data = sc.run_input(start)
    params = d / "test_params.csv"
    pd.DataFrame([{"time_series_name": y, "dependents": sc.X, "group_column": "bank_name", "group_value": "*"}]
                 ).to_csv(params, index=False)
    coint, respec = d / "Co-integration_results.csv", d / "co-integration_respecification_results.csv"
    common = ["--dependents", data, "--independents", sc.FFT, "--y", y]
    run([PY, sc.ROOT / "Co-integration Tests.py", data, sc.FFT, params, "-o", coint], env, log)
    run([PY, sc.ROOT / "FlaggedRates_co-integration_respecification.py", *common, "--x", sc.X,
         "--banks", *sc.BANKS, "-o", respec], env, log)
    if covid:
        # ECM workflow.py has no --covid switch: run its four steps with the same arguments plus --covid.
        ms, ps = d / "ECM model selection results.csv", d / "ECM param selection results.csv"
        run([PY, sc.ROOT / "ECM model selection.py", "--cointegration", coint, "--respecification", respec,
             "-o", ms], env, log)
        run([PY, sc.ROOT / "ECM Param selection.py", "-i", ms, "-o", ps], env, log)
        run([PY, sc.ROOT / "ECM estimation.py", "-i", ps, *common, "--x", sc.X, "--covid",
             "-o", d / "ECM estimation results (det pruned).csv",
             "--summary", d / "estimation result summary (det pruned).csv",
             "--pruning-log", d / "deterministic_pruning_log.csv"], env, log)
        run([PY, sc.ROOT / "ECM asymmetric variants.py", "-i", ms, *common, "--x", sc.X, "--covid",
             "--out-dir", d, "--pruning-log", d / "deterministic_pruning_log.csv"], env, log)
    else:
        run([PY, sc.ROOT / "ECM workflow.py", "--cointegration", coint, "--respecification", respec,
             *common, "--x", sc.X, "--out-dir", d], env, log)
    cand = ["--summary", d / "estimation result summary (det pruned).csv",
            "--estimates", d / "ECM estimation results (det pruned).csv",
            "--asym-summary", d / "asymmetric estimation result summary (det pruned).csv",
            "--asym-estimates", d / "ECM asymmetric estimation results (det pruned).csv", *common, "--x", sc.X]
    run([PY, sc.ROOT / "MAE_Backtesting" / "run_backtest.py", "--horizon", "8Q", "--bank-name", "All",
         "--first-origin", "2016Q1", "--limits", "peer", "--reference-dir", d / "no_reference", *cand], env, log)
    run([PY, sc.ROOT / "Beta_Backtesting" / "run_beta_backtest.py", "--horizon", "8Q", "--bank-name", "All",
         "--first-origin", "2016Q1", *cand], env, log)
    run([PY, sc.ROOT / "Beta_Backtesting" / "run_beta_backtest.py", "--horizon", "8Q", "--bank-name", "All",
         "--first-origin", "2016Q1", "--realized", *cand], env, log)
    return d


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--segments", nargs="+", default=list(sc.SEGMENTS))
    ap.add_argument("--start", default="2012Q1")
    ap.add_argument("--tag", default="base")
    ap.add_argument("--covid", action="store_true")
    a = ap.parse_args(argv)
    sc.check_pinned()
    start = str(pd.Period(a.start, "Q").end_time.date())
    for seg in a.segments:
        print("segment", seg, "->", segment(seg, start, a.tag, a.covid))
    return 0


if __name__ == "__main__":
    sys.exit(main())
