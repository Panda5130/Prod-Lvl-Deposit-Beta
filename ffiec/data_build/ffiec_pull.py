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

Endpoint and headers follow CDR SIS611 v1.10 (https://cdr.ffiec.gov/public/Files/SIS611_-_Retrieve_Public_Data_via_Web_Service.pdf).
The PWS allows about 2500 downloads per hour (CDR help page), so the pull throttles (PAUSE_S) and checkpoints to
disk every CHECKPOINT records; rerunning resumes. XBRL element naming in parse_facsimile is confirmed on the
first real response.
"""
import argparse
import hashlib
import io
import json
import logging
import os
import re
import sys
import time
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

PWS_BASE = "https://ffieccdr.azure-api.us/public"
FDIC_API = "https://api.fdic.gov/banks"
KEYRING_SERVICE = "ffiec_pws"
TARGET_CERTS = [4977, 30788, 6560, 17534, 588, 3832, 33555]
FIRST_PERIOD = "2007-12-31"       # 2007Q4 is needed for the 2008Q1 two-point average
LAST_PERIOD = "2026-09-30"
PAUSE_S = 0.5           # plus ~1.1 s call latency = ~2250 calls/hour, under the ~2500/hour limit
CHECKPOINT = 100
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
    """Thin wrapper; the only place that knows endpoint and header names. Per CDR SIS611 v1.10: all parameters
    are request HEADERS (plus UserID and "Authentication: Bearer <token>"); host ffieccdr.azure-api.us."""

    def __init__(self, user, token, session=None, fmt="XBRL"):
        self._h = {"UserID": user, "Authentication": f"Bearer {token}", "dataSeries": "Call",
                   "User-Agent": "ffiec-pull/1.0 (research client)"}   # never logged; the gateway returns 403 to the default python-requests agent
        self.s = session or requests.Session()
        self.fmt = fmt

    def _get(self, op, **headers):
        r = self.s.get(f"{PWS_BASE}/{op}", headers={**self._h, **headers}, timeout=60)
        r.raise_for_status()
        return r.content

    def facsimile(self, rssd, period):
        return decode_stream(self._get("RetrieveFacsimile", reportingPeriodEndDate=_us(period), fiIdType="ID_RSSD",
                                       fiId=str(rssd), facsimileFormat=self.fmt))

    def filers_since(self, period, since):
        """RSSD IDs of filers whose submission was updated since `since` (amendment detection)."""
        raw = self._get("RetrieveFilersSinceDate", reportingPeriodEndDate=_us(period), lastUpdateDateTime=since)
        try:
            return {int(x) for x in json.loads(raw).get("ID_RSSDs", [])}
        except (ValueError, AttributeError):
            return {int(x) for x in re.findall(r"\d+", raw.decode("utf-8", "ignore"))}


def decode_stream(raw):
    """The facsimile comes back as a byte stream; tolerate a JSON byte array, JSON {FacsimileFile: base64|list},
    or the file itself."""
    try:
        j = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(j, dict):
        j = j.get("FacsimileFile", j)
    if isinstance(j, list) and all(isinstance(x, int) for x in j):
        return bytes(j)
    if isinstance(j, str):
        import base64
        return base64.b64decode(j)
    return raw


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


def _with_retry(fn, tries=3, base=30, cap=300):
    """Retry transient failures with capped backoff. Connection errors (laptop asleep, network down) retry
    without limit; 429/5xx retry `tries` times; other HTTP errors raise at once."""
    i = 0
    while True:
        try:
            return fn()
        except requests.HTTPError as e:
            code = e.response.status_code
            if code not in (429, 500, 502, 503, 504) or i >= tries - 1:
                raise
            why = f"HTTP {code}"
        except (requests.ConnectionError, requests.Timeout) as e:
            why = type(e).__name__
        wait = min(cap, base * 2 ** min(i, 10))
        log.warning("transient failure (%s), retry %d after %ds", why, i + 1, wait)
        time.sleep(wait)
        i += 1


def _canary_ok(client, key):
    try:
        client.facsimile(*key)
        return True
    except requests.RequestException:
        return False


def pull(client, plan, items, check_hash_for=(), now=None, pause=0.0, checkpoint=None):
    """Fetch (rssd, period) pairs not held, plus `check_hash_for` (amendment re-pulls). A re-pull whose hash
    differs replaces the old records and is reported. Returns (items, amendments, n_calls)."""
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    have = held(items)
    known_missing = load_missing()
    todo = [(r, p) for r, per in plan.items() for p in per if (r, p) not in have and (r, p) not in known_missing]
    todo += [k for k in check_hash_for if k in have]
    rows, amend, calls, skipped, consec, failed_entities = [], [], 0, [], 0, set()
    canary = sorted(have)[0] if have else None
    for rssd, period in todo:
        if pause and calls:
            time.sleep(pause)
        try:
            raw = _with_retry(lambda: client.facsimile(rssd, period),
                              tries=1 if rssd in failed_entities else 3)   # an entity with no filings fails fast
        except requests.HTTPError as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (401, 403):                 # auth or gateway problem: stop, do not hammer
                if checkpoint and rows:
                    checkpoint(pd.concat([items, pd.DataFrame(rows)], ignore_index=True), pd.DataFrame())
                raise
            log.warning("no filing returned for rssd %s %s (HTTP %s); recorded as missing", rssd, period, code)
            skipped.append((rssd, period))
            record_missing([(rssd, period)], now)  # persisted at once: a crash or stop must not repeat these
            if rssd not in failed_entities:
                consec += 1                      # count distinct entities, so one filer with no history is not an outage
            failed_entities.add(rssd)
            if consec >= 5:
                # Many predecessors did not exist in early quarters, so a run of failures is not proof of an outage.
                # Canary: re-fetch a filing known to exist; stop only if that fails too.
                if canary and not _canary_ok(client, canary):
                    if checkpoint and rows:
                        checkpoint(pd.concat([items, pd.DataFrame(rows)], ignore_index=True), pd.DataFrame())
                    raise RuntimeError("service outage (known-good filing also fails); stopping; rerun to resume")
                consec = 0
            continue
        consec = 0
        failed_entities.discard(rssd)
        calls += 1
        if checkpoint and rows and calls % CHECKPOINT == 0:
            checkpoint(pd.concat([items, pd.DataFrame(rows)], ignore_index=True), pd.DataFrame())
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
    if skipped:
        log.warning("%d filings returned no data and are listed in ffiec/data/missing_filings.csv", len(skipped))
    return items, pd.DataFrame(amend), calls


MISSING = DATA / "missing_filings.csv"


def load_missing():
    if MISSING.exists():
        d = pd.read_csv(MISSING, dtype={"period": str})
        return set(zip(d.rssd.astype(int), d.period))
    return set()


def record_missing(skipped, now):
    """Filings the service answered with a persistent error (no such filing). Not retried on later runs;
    delete the file to retry them."""
    old = pd.read_csv(MISSING) if MISSING.exists() else pd.DataFrame(columns=["rssd", "period", "recorded_at"])
    new = pd.DataFrame([{"rssd": r, "period": p, "recorded_at": now} for r, p in skipped])
    MISSING.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([old, new], ignore_index=True).drop_duplicates(["rssd", "period"]).to_csv(MISSING, index=False)


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


LOCK = DATA / ".pull.lock"
LOCK_STALE_S = 1800


def acquire_lock():
    """True if this process may run. A lock younger than LOCK_STALE_S (touched at every checkpoint) means another
    run is active; an older one is a crashed run and is taken over."""
    DATA.mkdir(parents=True, exist_ok=True)
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < LOCK_STALE_S:
        return False
    LOCK.write_text(str(os.getpid()))
    return True


def _checkpoint(items, amend):
    save(items, amend)
    LOCK.touch()


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
    if not acquire_lock():
        log.info("another pull is active (lock is fresh); exiting")
        return 0
    user, token = get_credentials()
    client = PwsClient(user, token)
    check = []
    if a.check_amendments and len(items):
        since = items.pulled_at.min()
        for p in sorted(set(items.period)):
            check += [(r, p) for r in client.filers_since(p, since) if (r, p) in held(items)]
    try:
        items, amend, calls = pull(client, plan, items, check, pause=PAUSE_S, checkpoint=_checkpoint)
        save(items, amend)
    finally:
        LOCK.unlink(missing_ok=True)
    log.info("calls %d, records %d, amendments %d", calls, len(items), len(amend))
    return 0


if __name__ == "__main__":
    sys.exit(main())
