"""Incremental FFIEC Call Report pull (CDR Public Web Service) into a long CSV under ffiec/data/.

    python ffiec/data_build/ffiec_pull.py --plan           # entities/periods and call counts, no calls
    python ffiec/data_build/ffiec_pull.py                  # pull what is not held yet
    python ffiec/data_build/ffiec_pull.py --check-amendments

Credentials: keyring service "ffiec_pws" (keys "user", "token"), else env FFIEC_USER / FFIEC_TOKEN. If neither
is present the script stops with instructions; it never prompts and never prints or logs the token.

Outputs (ffiec/data/):
    cert_rssd.csv              FDIC cert -> FED_RSSD (FDIC institutions API), cached
    ffiec_items.csv            long: rssd, period, item, value, response_hash, pulled_at (RI items YTD as reported)
    ffiec_items_quarterly.csv  same keys, RI items converted to quarterly flows
    amendments.csv             records whose response hash changed on a later pull
Reads (never writes) merger_events_used.csv at the repo root for the predecessor list.

ASSUMPTION TO CONFIRM ON THE FIRST AUTHENTICATED CALL: the PWS endpoint and header names in PwsClient and the
XBRL element naming in parse_facsimile were written without access to the service documentation (the host
blocked unauthenticated fetches). They are isolated in those two places; the tests use mocked responses.
"""
import argparse
import hashlib
import io
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from items import ITEMS  # noqa: E402

HERE = Path(__file__).resolve().parent
FFIEC = HERE.parent
ROOT = FFIEC.parent
DATA = FFIEC / "data"
log = logging.getLogger("ffiec_pull")

PWS_BASE = "https://ffieccdr.azure-api.net/public"
FDIC_API = "https://api.fdic.gov/banks"
KEYRING_SERVICE = "ffiec_pws"
TARGET_CERTS = [4977, 30788, 6560, 17534, 588, 3832, 33555]
FIRST_PERIOD = "2007-12-31"       # 2007Q4 is needed for the 2008Q1 two-point average
LAST_PERIOD = "2026-09-30"
ITEM_COLS = ["rssd", "period", "item", "value", "response_hash", "pulled_at"]

NO_CREDS_MSG = (
    "FFIEC credentials not found. Store them once, yourself (never paste the token into chat or the repo):\n"
    "  pip install keyring\n"
    "  python -c \"import keyring, getpass; keyring.set_password('ffiec_pws', 'token', getpass.getpass('FFIEC token: '))\"\n"
    "  python -c \"import keyring; keyring.set_password('ffiec_pws', 'user', input('FFIEC user name: '))\"\n"
    "or set user environment variables FFIEC_USER and FFIEC_TOKEN, then open a new terminal.")


def get_credentials():
    """(user, token) from keyring, else env vars. Stops with instructions if absent; never prompts."""
    user = token = None
    try:
        import keyring
        user = keyring.get_password(KEYRING_SERVICE, "user")
        token = keyring.get_password(KEYRING_SERVICE, "token")
    except Exception:  # keyring missing or no backend
        pass
    user = user or os.environ.get("FFIEC_USER")
    token = token or os.environ.get("FFIEC_TOKEN")
    if not (user and token):
        raise SystemExit(NO_CREDS_MSG)
    return user, token


# ---------------------------------------------------------------- periods and plan
def quarter_ends(first=FIRST_PERIOD, last=LAST_PERIOD):
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(first, last, freq="QE")]


def read_events(root=ROOT):
    return pd.read_csv(root / "merger_events_used.csv")


def plan_pulls(cert_rssd, events, targets=TARGET_CERTS, first=FIRST_PERIOD, last=LAST_PERIOD):
    """({rssd: [period,...]}, missing_certs). Targets: every quarter. Predecessors: first..predecessor_last_quarter
    for Mode A (financials feed the adjustment), only the last quarter for Mode B (the materiality test)."""
    wanted = {int(c): quarter_ends(first, last) for c in targets}
    for e in events.itertuples():
        cert = int(e.predecessor_cert)
        if not isinstance(e.predecessor_last_quarter, str):
            continue
        lq = pd.Period(e.predecessor_last_quarter, "Q").end_time.strftime("%Y-%m-%d")
        per = quarter_ends(first, lq) if e.mode_applied == "A" else [lq]
        wanted[cert] = sorted(set(wanted.get(cert, [])) | set(per))
    plan, missing = {}, []
    for cert, per in wanted.items():
        rssd = cert_rssd.get(cert)
        if rssd is None or pd.isna(rssd):
            missing.append(cert)
        else:
            plan[int(rssd)] = sorted(set(plan.get(int(rssd), [])) | set(per))
    return plan, sorted(missing)


# ---------------------------------------------------------------- cert -> RSSD
def load_cert_rssd(path=None):
    path = Path(path or DATA / "cert_rssd.csv")
    if not path.exists():
        return {}
    d = pd.read_csv(path)
    return {int(c): (int(r) if pd.notna(r) and r != 0 else None) for c, r in zip(d.cert, d.rssd)}


def fetch_cert_rssd(certs, session=None, path=None, chunk=50):
    """FDIC institutions API, FED_RSSD field, cached in ffiec/data/cert_rssd.csv. Certs the API does not return
    are kept with an empty rssd (not re-asked) and reported as unmapped."""
    path = Path(path or DATA / "cert_rssd.csv")
    have = load_cert_rssd(path)
    new = sorted(set(int(c) for c in certs) - set(have))
    s = session or requests
    for i in range(0, len(new), chunk):
        part = new[i:i + chunk]
        r = s.get(f"{FDIC_API}/institutions", params={
            "filters": f"CERT:({' OR '.join(map(str, part))})", "fields": "CERT,FED_RSSD", "limit": 10000,
            "format": "csv"}, timeout=60)
        r.raise_for_status()
        got = pd.read_csv(io.StringIO(r.text)) if r.text.strip() else pd.DataFrame(columns=["CERT", "FED_RSSD"])
        found = {int(c): (int(x) if pd.notna(x) and x else None) for c, x in zip(got.CERT, got.FED_RSSD)}
        for c in part:
            have[c] = found.get(c)
    if new:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"cert": list(have), "rssd": [have[c] for c in have]}).sort_values("cert").to_csv(
            path, index=False)
    return have


# ---------------------------------------------------------------- PWS client and parser
def _us(period):
    d = datetime.strptime(period, "%Y-%m-%d")
    return f"{d.month}/{d.day}/{d.year}"


class PwsClient:
    """Thin wrapper; the only place that knows endpoint and header names (see module ASSUMPTION note)."""

    def __init__(self, user, token, session=None):
        self._h = {"UserID": user, "Authentication": f"Bearer {token}"}   # never logged
        self.s = session or requests.Session()

    def _get(self, op, params):
        r = self.s.get(f"{PWS_BASE}/{op}", headers=self._h, params=params, timeout=120)
        r.raise_for_status()
        return r.content

    def facsimile(self, rssd, period):
        return self._get("RetrieveFacsimile", {"dataSeries": "Call", "reportingPeriodEndDate": _us(period),
                                               "fiIDType": "ID_RSSD", "fiID": rssd, "facsimileFormat": "XBRL"})

    def filers_since(self, period, since):
        """RSSD IDs of filers whose submission was updated since `since` (amendment detection)."""
        raw = self._get("RetrieveFilersSinceDate", {"dataSeries": "Call", "reportingPeriodEndDate": _us(period),
                                                    "lastUpdateDateTime": since})
        return {int(x) for x in re.findall(r"\d+", raw.decode("utf-8", "ignore"))}


_FACT = re.compile(r"<(?:[\w.-]+:)?((?:RCON|RCFD|RCFN|RIAD)[0-9A-Z]{4})\b[^>]*>\s*([-+0-9.eE]+)\s*</", re.I)


def parse_facsimile(raw, wanted=ITEMS):
    """{item: value} for wanted codes from an XBRL facsimile. Facts are elements whose local name is
    mnemonic+code (any case, any namespace prefix); the first occurrence wins."""
    text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
    out = {}
    for code, val in _FACT.findall(text):
        code = code.upper()
        if code in wanted and code not in out:
            out[code] = float(val)
    return out


def response_hash(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


# ---------------------------------------------------------------- store
def load_items(path=None):
    path = Path(path or DATA / "ffiec_items.csv")
    if path.exists():
        return pd.read_csv(path, dtype={"period": str})
    return pd.DataFrame(columns=ITEM_COLS)


def held(items):
    return set(zip(items.rssd.astype(int), items.period))


def pull(client, plan, items, check_hash_for=(), now=None):
    """Fetch (rssd, period) pairs not held, plus `check_hash_for` (amendment re-pulls). A re-pull whose hash
    differs replaces the old records and is reported. Returns (items, amendments, n_calls)."""
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    have = held(items)
    todo = [(r, p) for r, per in plan.items() for p in per if (r, p) not in have]
    todo += [k for k in check_hash_for if k in have]
    rows, amend, calls = [], [], 0
    for rssd, period in todo:
        raw = client.facsimile(rssd, period)
        calls += 1
        h = response_hash(raw)
        vals = parse_facsimile(raw)
        old = items[(items.rssd == rssd) & (items.period == period)]
        if len(old):
            if old.response_hash.iloc[0] == h:
                continue
            amend.append({"rssd": rssd, "period": period, "old_hash": old.response_hash.iloc[0], "new_hash": h,
                          "detected_at": now})
            items = items.drop(old.index)
        rows += [{"rssd": rssd, "period": period, "item": k, "value": v, "response_hash": h, "pulled_at": now}
                 for k, v in vals.items()]
        if not vals:
            log.warning("no wanted items parsed for rssd %s %s", rssd, period)
    if rows:
        items = pd.concat([items, pd.DataFrame(rows)], ignore_index=True)
    return items, pd.DataFrame(amend), calls


def to_quarterly(items):
    """YTD RI items -> quarterly: Q1 = YTD; later quarters = YTD minus the previous quarter's YTD (NaN if that
    quarter is missing). Level items unchanged."""
    d = items.copy()
    d["date"] = pd.to_datetime(d.period)
    is_ytd = d["item"].map(lambda c: ITEMS[c][0] == "ytd")
    y = d[is_ytd].sort_values(["rssd", "item", "date"])
    g = y.groupby(["rssd", "item"])
    prev_date, prev_val = g.date.shift(1), g.value.shift(1)
    ok = prev_date.notna() & ((y.date - prev_date).dt.days.between(80, 100)) & (y.date.dt.year == prev_date.dt.year)
    q = y.value - prev_val.where(ok)
    q[y.date.dt.month == 3] = y.value
    d.loc[y.index, "value"] = q
    return d.drop(columns="date")


def save(items, amendments, outdir=DATA):
    outdir.mkdir(parents=True, exist_ok=True)
    items.sort_values(["rssd", "period", "item"]).to_csv(outdir / "ffiec_items.csv", index=False)
    to_quarterly(items).sort_values(["rssd", "period", "item"]).to_csv(outdir / "ffiec_items_quarterly.csv",
                                                                         index=False)
    if len(amendments):
        p = outdir / "amendments.csv"
        old = pd.read_csv(p) if p.exists() else pd.DataFrame()
        pd.concat([old, amendments], ignore_index=True).to_csv(p, index=False)


def verify_items(mdrm_csv):
    """Every item code must exist in MDRM; returns the list of problems (empty if none)."""
    d = pd.read_csv(mdrm_csv, skiprows=1, dtype=str, encoding="latin1", index_col=False)
    keys = set(d.Mnemonic.str.strip() + d["Item Code"].str.strip())
    return [(c, "not in MDRM") for c in ITEMS if c not in keys]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Incremental FFIEC Call Report pull")
    ap.add_argument("--plan", action="store_true", help="show the pull plan and call count; make no calls")
    ap.add_argument("--check-amendments", action="store_true", help="re-pull filers updated since the last pull")
    ap.add_argument("--verify-items", metavar="MDRM_CSV")
    ap.add_argument("--first", default=FIRST_PERIOD)
    ap.add_argument("--last", default=LAST_PERIOD)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    if a.verify_items:
        bad = verify_items(a.verify_items)
        print("item check:", "all codes present" if not bad else bad)
        return 1 if bad else 0
    ev = read_events()
    cert_rssd = fetch_cert_rssd(TARGET_CERTS + ev.predecessor_cert.astype(int).tolist())
    plan, missing = plan_pulls(cert_rssd, ev, first=a.first, last=a.last)
    items = load_items()
    todo = sum(1 for r, per in plan.items() for p in per if (r, p) not in held(items))
    log.info("entities %d, unmapped certs %d %s, calls needed %d", len(plan), len(missing), missing[:10], todo)
    if a.plan:
        return 0
    user, token = get_credentials()
    client = PwsClient(user, token)
    check = []
    if a.check_amendments and len(items):
        since = items.pulled_at.min()
        for p in sorted(set(items.period)):
            check += [(r, p) for r in client.filers_since(p, since) if (r, p) in held(items)]
    items, amend, calls = pull(client, plan, items, check)
    save(items, amend)
    log.info("calls %d, records %d, amendments %d", calls, len(items), len(amend))
    return 0


if __name__ == "__main__":
    sys.exit(main())
