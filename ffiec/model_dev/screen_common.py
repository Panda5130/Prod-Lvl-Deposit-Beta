"""Shared settings for the Prod-Lvl model screen (data vintage v2-rc-6, data commit cddc1d1).

Pinned inputs are checked by SHA-256 of the checked-out (LF) file before any run; a mismatch stops the run.
The five-bank filter and the 2012Q1-2026Q3 window are applied at run time: `run_input()` writes a filtered copy
of the pinned dependent file into the vintage output directory (the pinned file is only read). Nothing is
written outside ffiec/model_dev/outputs/<vintage>/.
"""
import hashlib
import os
import sys
from pathlib import Path

import pandas as pd

MODEL_DEV = Path(__file__).resolve().parent
FFIEC = MODEL_DEV.parent
ROOT = FFIEC.parent
VINTAGE = "v2-rc-6"
OUT = MODEL_DEV / "outputs" / VINTAGE

DEPENDENTS = FFIEC / "outputs" / "ffiec_deposit_rates_hybrid_v2.csv"
FFT = MODEL_DEV / "inputs" / "v2-rc-3" / "FFT_2011-2026.csv"
FFT_2008 = MODEL_DEV / "inputs" / "v2-rc-3" / "FFT_2008-2026.csv"
PINNED_LF = {
    DEPENDENTS: "1cc31d8694afd042b89aac290f3ab80521abd8306477dff88ac4d4bfc503b1bf",
    FFT: "d1c83be581d0c04b04cbeed58084b7ec853a336fa4ed0be8e6364a5870dde1bc",
    FFT_2008: "38298c661ff571457fb4c2f7e058ed9c9f4946c06683c81e60b674e375fb18c6",
}

CERTS = {4977: "First Horizon Bank", 6560: "Huntington National Bank", 17534: "KeyBank National Association",
         588: "Manufacturers and Traders Trust Company", 3832: "Old National Bank"}
BANKS = list(CERTS.values())
SHORT = {"First Horizon Bank": "First Horizon", "Huntington National Bank": "Huntington",
         "KeyBank National Association": "KeyBank", "Manufacturers and Traders Trust Company": "M&T",
         "Old National Bank": "Old National"}
START, END = "2012-03-31", "2026-09-30"
SEGMENTS = {"nmd": "rate_nmd_eoq_pf", "time": "rate_time_eoq_pf"}
X = "FFT"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_pinned():
    bad = [(p, sha256(p), h) for p, h in PINNED_LF.items() if sha256(p) != h]
    if bad:
        for p, got, want in bad:
            print(f"PINNED INPUT MISMATCH: {p}: {got} != {want}", file=sys.stderr)
        sys.exit(3)
    return {str(p.relative_to(ROOT)): h for p, h in PINNED_LF.items()}


def run_input(start=START, path=None):
    """Five-bank, in-window copy of the pinned dependent file (rows only filtered, never edited)."""
    check_pinned()
    df = pd.read_csv(DEPENDENTS)
    df = df[df.cert_number.isin(CERTS) & df.quarter.between(start, END)].copy()
    assert set(df.bank_name) == set(BANKS), set(df.bank_name)
    path = Path(path or OUT / "inputs" / f"run_input_{start[:4]}Q{(int(start[5:7]) - 1) // 3 + 1}.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def pipeline_env(segment_dir):
    """Environment for origin scripts: every default write goes under <segment_dir> (inside ffiec/)."""
    return {**os.environ, "DEPOSIT_OUTPUT_VINTAGE": str(Path(segment_dir).resolve()), "MPLBACKEND": "Agg"}


def bank_series(df, bank, y, fft=None):
    """(y, FFT) for one bank indexed by quarterly PeriodIndex."""
    g = df[df.bank_name == bank].copy()
    g.index = pd.PeriodIndex(pd.to_datetime(g.quarter), freq="Q")
    out = g[[y]].astype(float)
    if fft is not None:
        out[X] = fft.reindex(out.index)
    return out


def load_fft(path=FFT):
    f = pd.read_csv(path)
    f.index = pd.PeriodIndex(f.iloc[:, 0].astype(str), freq="Q")
    return f[X].astype(float)
