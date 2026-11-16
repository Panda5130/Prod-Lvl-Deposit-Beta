"""Tests for the FFIEC pilot with mocked responses (no network, no credentials)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

FFIEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FFIEC / "data_build"))
sys.path.insert(0, str(FFIEC))
import ffiec_pull as fp  # noqa: E402
import build_ffiec as bf  # noqa: E402
import nic_events as ne  # noqa: E402
import reconcile as rc  # noqa: E402
import verify_isolation as vi  # noqa: E402


def facsimile(values):
    body = "".join(f"<cc:{k}>{v}</cc:{k}>" for k, v in values.items())
    return f"<xbrl>{body}<cc:RCON9999>5</cc:RCON9999></xbrl>".encode()


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def facsimile(self, rssd, period):
        self.calls.append((rssd, period))
        return self.responses[(rssd, period)]


class Resp:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self, text):
        self.text, self.n = text, 0

    def get(self, url, **kw):
        self.n += 1
        return Resp(self.text)


# ---------------------------------------------------------------- parsing and YTD conversion
def test_parse_keeps_only_wanted_items():
    got = fp.parse_facsimile(facsimile({"RCON2200": 1000, "RIAD4508": "12.5"}))
    assert got == {"RCON2200": 1000.0, "RIAD4508": 12.5}


def test_ytd_to_quarterly_and_levels_untouched():
    rows = []
    for p, ytd in [("2008-03-31", 10), ("2008-06-30", 25), ("2008-09-30", 45), ("2008-12-31", 70),
                   ("2009-03-31", 8)]:
        rows.append({"rssd": 1, "period": p, "item": "RIAD4508", "value": ytd})
        rows.append({"rssd": 1, "period": p, "item": "RCON2200", "value": 999})
    q = fp.to_quarterly(pd.DataFrame(rows))
    flow = q[q["item"] == "RIAD4508"].sort_values("period").value.tolist()
    assert flow == [10, 15, 20, 25, 8]
    assert (q[q["item"] == "RCON2200"].value == 999).all()


def test_ytd_gap_gives_nan_not_wrong_value():
    rows = [{"rssd": 1, "period": p, "item": "RIAD4508", "value": v}
            for p, v in [("2008-03-31", 10), ("2008-09-30", 45)]]
    q = fp.to_quarterly(pd.DataFrame(rows)).sort_values("period")
    assert q.value.iloc[0] == 10 and pd.isna(q.value.iloc[1])


# ---------------------------------------------------------------- incremental cache and amendments
def test_second_run_makes_no_calls_and_amendment_detected():
    plan = {7: ["2008-03-31", "2008-06-30"]}
    r1 = {(7, p): facsimile({"RCON2200": 100 + i}) for i, p in enumerate(plan[7])}
    c1 = FakeClient(r1)
    items, am, n = fp.pull(c1, plan, fp.load_items("nonexistent.csv"))
    assert n == 2 and len(items) == 2 and am.empty
    c2 = FakeClient(r1)
    items2, am2, n2 = fp.pull(c2, plan, items)
    assert n2 == 0 and c2.calls == []
    # amendment: same key re-pulled with different content
    r3 = dict(r1)
    r3[(7, "2008-06-30")] = facsimile({"RCON2200": 555})
    c3 = FakeClient(r3)
    items3, am3, n3 = fp.pull(c3, plan, items2, check_hash_for=[(7, "2008-06-30")])
    assert n3 == 1 and len(am3) == 1 and am3.period.iloc[0] == "2008-06-30"
    assert items3[(items3.period == "2008-06-30")].value.iloc[0] == 555
    # unchanged re-pull: no amendment
    items4, am4, _ = fp.pull(FakeClient(r3), plan, items3, check_hash_for=[(7, "2008-06-30")])
    assert am4.empty and len(items4) == 2


# ---------------------------------------------------------------- identifier mapping
def test_cert_rssd_mapping_cached_and_unmapped_flagged(tmp_path):
    path = tmp_path / "cert_rssd.csv"
    s = FakeSession("CERT,FED_RSSD\n4977,100\n6560,200\n")
    m = fp.fetch_cert_rssd([4977, 6560, 111], session=s, path=path)
    assert m == {4977: 100, 6560: 200, 111: None}
    s2 = FakeSession("")
    assert fp.fetch_cert_rssd([4977, 111], session=s2, path=path)[4977] == 100
    assert s2.n == 0                                           # cached, no second call
    ev = pd.DataFrame({"predecessor_cert": [111], "predecessor_last_quarter": ["2010Q1"], "mode_applied": ["A"]})
    plan, missing = fp.plan_pulls(m, ev, targets=[4977], first="2009-12-31", last="2010-06-30")
    assert missing == [111] and plan == {100: ["2009-12-31", "2010-03-31", "2010-06-30"]}


def test_plan_mode_b_pulls_only_last_quarter():
    ev = pd.DataFrame({"predecessor_cert": [5], "predecessor_last_quarter": ["2010Q1"], "mode_applied": ["B"]})
    plan, _ = fp.plan_pulls({5: 50}, ev, targets=[], first="2008-03-31", last="2012-12-31")
    assert plan == {50: ["2010-03-31"]}


# ---------------------------------------------------------------- credentials
def test_no_credentials_stops_with_instructions_and_never_prompts(monkeypatch):
    monkeypatch.delenv("FFIEC_USER", raising=False)
    monkeypatch.delenv("FFIEC_TOKEN", raising=False)
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *a: None)
    with pytest.raises(SystemExit) as e:
        fp.get_credentials()
    assert "keyring" in str(e.value)


def test_env_fallback(monkeypatch):
    import keyring
    monkeypatch.setattr(keyring, "get_password", lambda *a: None)
    monkeypatch.setenv("FFIEC_USER", "u")
    monkeypatch.setenv("FFIEC_TOKEN", "t")
    assert fp.get_credentials() == ("u", "t")


def test_item_codes_exist_in_mdrm_listing(tmp_path):
    csv = tmp_path / "m.csv"
    codes = [("RCON", "2200")]
    csv.write_text("header junk\nMnemonic,Item Code\n" + "\n".join(f"{m},{c}" for m, c in codes))
    bad = fp.verify_items(csv)
    assert ("RCFD2200", "not in MDRM") in bad and not any(c == "RCON2200" for c, _ in bad)


# ---------------------------------------------------------------- builder reuses FDIC merger logic
def _items(rssd, periods, dep, ytd_step):
    rows = []
    for p in periods:
        q = pd.Timestamp(p).quarter
        for code, v in [("RCON2200", dep), ("RIAD4508", ytd_step * q * 1000), ("RIAD0093", ytd_step * q * 1000),
                        ("RIADA517", ytd_step * q * 1000), ("RIADA518", ytd_step * q * 1000)]:
            rows.append({"rssd": rssd, "period": p, "item": code, "value": v})
    return rows


def test_builder_applies_fdic_merger_logic(tmp_path):
    per = [d.strftime("%Y-%m-%d") for d in pd.date_range("2007-12-31", "2009-12-31", freq="QE")]
    items = pd.DataFrame(_items(1, per, 1_000_000_000, 5) + _items(2, [p for p in per if p < "2008-09-30"],
                                                                    500_000_000, 5))
    q = fp.to_quarterly(items)                                  # target 4977 (rssd 1), predecessor 15067 (rssd 2)
    qp = tmp_path / "q.csv"
    q.to_csv(qp, index=False)
    cr = tmp_path / "cr.csv"
    pd.DataFrame({"cert": [4977, 15067], "rssd": [1, 2]}).to_csv(cr, index=False)
    hist = tmp_path / "h.csv"
    pd.DataFrame([{"CERT": 15067, "ACQ_CERT": 4977, "OUT_CERT": 15067, "OUT_INSTNAME": "Pred", "CHANGECODE": 223,
                   "CHANGECODE_DESC": "Merger", "EFFDATE": "2008-08-31"}]).to_csv(hist, index=False)
    data, events, checks = bf.build_ffiec(qp, cr, hist, outdir=tmp_path / "out", root=bf.ROOT)
    e = events.iloc[0]
    assert e.mode_applied == "A" and e.pct_of_survivor_deposits == pytest.approx(50.0)
    row = data[(data.cert_number == 4977) & (data.quarter == "2008-03-31")].iloc[0]
    assert row.n_predecessors_included == 1 and row.dep_avg_pf == pytest.approx(1_500_000 * 1.0)  # $ thousands
    assert (tmp_path / "out" / "merger_events_used_v2.csv").exists()
    assert checks["pro forma rate reconstruction max abs diff"] < 1e-9


def test_builder_drops_incomplete_ri_quarters():
    w = pd.DataFrame([{"rssd": 1, "period": "2008-03-31", "item": "RCON2200", "value": 1e9},
                      {"rssd": 1, "period": "2008-03-31", "item": "RIAD4508", "value": 1.0}])
    assert bf.financials_from_items(w, {4977: 1}).empty


def test_shared_rssd_goes_to_the_cert_alive_that_quarter():
    rows = [{"rssd": 1, "period": p, "item": i, "value": v} for p in ("2008-03-31", "2008-06-30")
            for i, v in [("RCON2200", 1e9), ("RIAD4508", 1.0), ("RIAD0093", 1.0), ("RIADA517", 1.0), ("RIADA518", 1.0)]]
    life = {(10, 20080331): 1_000_000.0, (20, 20080630): 1_000_000.0}   # cert 10 retired, cert 20 took over the RSSD
    out = bf.financials_from_items(pd.DataFrame(rows), {10: 1, 20: 1}, life)
    assert sorted(zip(out.CERT, out.REPDTE)) == [(10, 20080331), (20, 20080630)]


def test_wrong_api_rssd_resolved_by_extra_rssd_and_deposit_match():
    ri = [("RIAD4508", 1.0), ("RIAD0093", 1.0), ("RIADA517", 1.0), ("RIADA518", 1.0)]
    rows = [{"rssd": r, "period": "2008-03-31", "item": i, "value": v}
            for r, dep in [(1, 9e9), (2, 1e9)] for i, v in [("RCON2200", dep)] + ri]
    fdic = {(10, 20080331): 9_000_000.0, (20, 20080331): 1_000_000.0}   # API gave cert 10 the RSSD of cert 20
    out = bf.financials_from_items(pd.DataFrame(rows), {10: 2, 20: 2}, fdic, extra={10: [1]})
    got = dict(zip(out.CERT, out.DEP))
    assert got == {10: 9_000_000.0, 20: 1_000_000.0}


def test_total_deposits_include_foreign_offices():
    rows = [{"rssd": 1, "period": "2008-03-31", "item": i, "value": v}
            for i, v in [("RCON2200", 9e9), ("RCFN2200", 1e9), ("RIAD4508", 1.0), ("RIAD0093", 1.0),
                         ("RIADA517", 1.0), ("RIADA518", 1.0)]]
    out = bf.financials_from_items(pd.DataFrame(rows), {4977: 1})
    assert out.DEP.iloc[0] == pytest.approx(10_000_000.0)       # $ thousands: domestic + foreign


# ---------------------------------------------------------------- NIC cross-check
def test_nic_cross_check_flags_differences():
    events = pd.DataFrame({"predecessor_cert": [10, 11, 12], "survivor_cert": [1, 1, 1],
                           "effective_date": ["2010-05-01", "2011-01-15", "2012-03-01"],
                           "mode_applied": ["A", "A", "B"]})
    cert_rssd = {1: 100, 10: 110, 11: 111, 12: 112}
    nic = pd.DataFrame({"pred": pd.array([110, 111, 113], dtype="Int64"),
                        "succ": pd.array([100, 100, 100], dtype="Int64"),
                        "date": pd.to_datetime(["2010-05-03", "2011-06-30", "2013-01-01"])})
    diff, summ = ne.compare(nic, events, cert_rssd)
    st = dict(zip(diff.pred, diff.status))
    assert st == {111: "date_differs", 112: "fdic_only", 113: "nic_only"} and summ["matched"] == 1


def test_nic_reader_aliases(tmp_path):
    f = tmp_path / "n.csv"
    f.write_text("#ID_RSSD_PREDECESSOR,ID_RSSD_SUCCESSOR,DT_TRANS,TRNSFM_CD\n1,2,20100501,1\n")
    assert ne.read_nic(f).succ.iloc[0] == 2


# ---------------------------------------------------------------- reconciliation
def test_reconcile_flags_difference_and_only_quarters():
    cols = ["cert_number", "quarter", "total_deposits", "deposit_interest_expense", "deposit_rate", "rate_pf_clean"]
    a = pd.DataFrame([[1, "2010-03-31", 100, 5, 2.0, 2.0], [1, "2010-06-30", 100, 5, 2.0, 2.0]], columns=cols)
    b = pd.DataFrame([[1, "2010-03-31", 100, 5, 2.0, 2.0], [1, "2010-06-30", 100, 5, 2.0, 2.1],
                      [1, "2026-09-30", 100, 5, 2.0, 2.0]], columns=cols)
    summ, q = rc.reconcile(a, b)
    assert set(q.status) == {"differs", "ffiec_only"}
    assert summ[summ.measure == "rate_pf_clean"].max_abs_diff.iloc[0] == pytest.approx(0.1)


# ---------------------------------------------------------------- isolation check
def test_isolation_check_runs_against_base():
    mb, bad = vi.changed_outside("main")
    assert isinstance(bad, list) and all(not p.startswith("ffiec/") for p in bad)


def test_persistent_http_error_is_recorded_missing_and_run_continues(tmp_path, monkeypatch):
    import requests

    class Flaky:
        def facsimile(self, rssd, period):
            if period == "2008-03-31":
                r = requests.Response()
                r.status_code = 500
                raise requests.HTTPError(response=r)
            return facsimile({"RCON2200": 1})
    monkeypatch.setattr(fp, "MISSING", tmp_path / "missing.csv")
    monkeypatch.setattr(fp.time, "sleep", lambda s: None)
    items, am, n = fp.pull(Flaky(), {7: ["2008-03-31", "2008-06-30"]}, fp.load_items("nonexistent.csv"))
    assert n == 1 and len(items) == 1 and fp.load_missing() == {(7, "2008-03-31")}
    items2, _, n2 = fp.pull(Flaky(), {7: ["2008-03-31", "2008-06-30"]}, items)
    assert n2 == 0                                              # missing filing is not retried


def test_backfill_adds_items_without_touching_existing_and_flags_amendments():
    r_ok, r_amended = facsimile({"RCON2200": 100, "RCONJ473": 7, "RCONJ474": 3}), facsimile({"RCON2200": 999})
    h_ok = fp.response_hash(r_ok)
    items = pd.DataFrame([
        {"rssd": 1, "period": "2014-12-31", "item": "RCON2200", "value": 100.0, "response_hash": h_ok, "pulled_at": "t"},
        {"rssd": 2, "period": "2014-12-31", "item": "RCON2200", "value": 50.0, "response_hash": "old", "pulled_at": "t"},
        {"rssd": 3, "period": "2020-12-31", "item": "RCON2200", "value": 1.0, "response_hash": "x", "pulled_at": "t"}])
    cl = FakeClient({(1, "2014-12-31"): r_ok, (2, "2014-12-31"): r_amended})
    out, nd, amend, calls = fp.backfill(cl, items, ["RCONJ473", "RCONJ474"], "2011-12-31", "2016-12-31")
    assert calls == 2 and (3, "2020-12-31") not in cl.calls                      # outside the window: not fetched
    got = out[out.rssd == 1].set_index("item").value.to_dict()
    assert got == {"RCON2200": 100.0, "RCONJ473": 7.0, "RCONJ474": 3.0}
    assert list(amend.rssd) == [2] and set(out[out.rssd == 2].item) == {"RCON2200"}   # amended filing left untouched
    cl2 = FakeClient({})
    _, _, _, calls2 = fp.backfill(cl2, out, ["RCONJ473", "RCONJ474"], "2011-12-31", "2016-12-31", done=set(nd))
    assert calls2 == 0                                                           # resumes: nothing refetched


# ---------------------------------------------------------------- hybrid denominator A_t
def _hy(rows):
    return bf.hybrid_denominator(pd.DataFrame(rows))


def test_hybrid_denominator_both_regimes_and_missing_rules():
    base = {"RCON3485": 10.0, "RCONB563": 20.0, "RCFN3404": 5.0, "RIAD4172": 1.0}
    rows = [
        {"rssd": 1, "period": "2016-12-31", **base, "RCON6648": 4.0, "RCONJ473": 3.0, "RCONJ474": 1.0},   # TD 8
        {"rssd": 1, "period": "2017-03-31", **base, "RCONHK16": 6.0, "RCONHK17": 4.0},                    # TD 10
        {"rssd": 1, "period": "2017-06-30", **base, "RCONHK16": 6.0},                                      # HK17 missing
        {"rssd": 2, "period": "2017-03-31", "RCON3485": 10.0, "RCONB563": 20.0, "RCONHK16": 2.0, "RCONHK17": 2.0},
        {"rssd": 2, "period": "2017-06-30", "RCON3485": 10.0, "RCONB563": 20.0, "RCONHK16": 2.0, "RCONHK17": 2.0,
         "RIAD4172": 7.0},
    ]
    w = _hy(rows).set_index(["rssd", "period"])
    assert w.loc[(1, "2017-03-31"), "TD_AVG"] == pytest.approx(9.0)          # (8 + 10)/2: no break at the switch
    assert w.loc[(1, "2017-03-31"), "A"] == pytest.approx(10 + 20 + 5 + 9)   # NMD_ib + FOR + TD_avg
    assert pd.isna(w.loc[(1, "2016-12-31"), "A"])                            # no prior quarter-end
    assert pd.isna(w.loc[(1, "2017-06-30"), "A"])                            # a missing piece is never zero-filled
    assert pd.isna(w.loc[(2, "2017-03-31"), "A"]) and pd.isna(w.loc[(2, "2017-06-30"), "A"])
    r2 = _hy([{"rssd": 3, "period": p, "RCON3485": 10.0, "RCONB563": 20.0, "RCONHK16": 2.0, "RCONHK17": 2.0}
              for p in ("2017-03-31", "2017-06-30")]).set_index("period")
    assert r2.loc["2017-06-30", "A"] == pytest.approx(10 + 20 + 0 + 4)       # no foreign offices, no RIAD4172: FOR = 0
    r3 = _hy([{"rssd": 4, "period": p, "RCON3485": 10.0, "RCONB563": 20.0, "RCONHK16": 2.0, "RCONHK17": 2.0,
               "RIAD4172": 7.0} for p in ("2017-03-31", "2017-06-30")]).set_index("period")
    assert pd.isna(r3.loc["2017-06-30", "A"])                                # foreign interest but no RCFN3404: flagged


def test_hybrid_pro_forma_matches_fdic_when_denominator_is_deposits():
    bd = bf.load_fdic_module()
    qs = pd.period_range("2012Q1", "2013Q4", freq="Q")
    fin = pd.DataFrame([{"CERT": c, "REPDTE": int(q.end_time.strftime("%Y%m%d")), "DEP": dep, "EDEPDOMQ": ie,
                         "EDEPFORQ": 0.0} for c, dep, ie, last in [(1, 1000.0, 5.0, None), (2, 400.0, 2.0, "2012Q4")]
                        for q in qs if last is None or q <= pd.Period(last)])
    hist = pd.DataFrame([{"CERT": 2, "ACQ_CERT": 1, "OUT_CERT": 2, "OUT_INSTNAME": "P", "CHANGECODE": 223,
                          "CHANGECODE_DESC": "Merger", "EFFDATE": "2013-02-14"}])
    src = bf.make_source_class(bd, fin, hist)(False, None)
    rows = []
    want = bd.pro_forma(src, 1, rows)
    modes = {(int(r["predecessor_cert"]), int(r["survivor_cert"]), str(r["effective_date"])): r["mode_applied"]
             for r in rows}
    assert modes[(2, 1, "2013-02-14")] == "A"
    got = bf.pro_forma_ib(src, 1, modes)
    pd.testing.assert_frame_equal(got, want)
    got_b = bf.pro_forma_ib(src, 1, {k: "B" for k in modes})                  # forced Mode B: no predecessor folded in
    assert (got_b.n_pred == 0).all() and got_b.DEP.equals(src.series(1).DEP)


def test_one_point_time_deposit_fallback_only_for_first_call_report_in_2012q1():
    leg = {"RCON3485": 10.0, "RCONB563": 20.0, "RCON6648": 4.0, "RCONJ473": 3.0, "RCONJ474": 1.0}   # TD 8
    rows = [{"rssd": 1, "period": "2012-03-31", **leg},                      # thrift: first Call Report 2012Q1
            {"rssd": 2, "period": "2011-12-31", "RCON3485": 1.0},            # filed 2011Q4 but TD missing
            {"rssd": 2, "period": "2012-03-31", **leg},
            {"rssd": 3, "period": "2012-06-30", **leg}]                      # first filing later: no fallback
    w = _hy(rows).set_index(["rssd", "period"])
    assert w.loc[(1, "2012-03-31"), "TD_FALLBACK"] and w.loc[(1, "2012-03-31"), "TD_AVG"] == pytest.approx(8.0)
    assert not w.loc[(2, "2012-03-31"), "TD_FALLBACK"] and pd.isna(w.loc[(2, "2012-03-31"), "A"])
    assert not w.loc[(3, "2012-06-30"), "TD_FALLBACK"] and pd.isna(w.loc[(3, "2012-06-30"), "A"])


def test_reconciling_total_adds_two_point_noninterest_bearing_average():
    leg = {"RCON3485": 10.0, "RCONB563": 20.0, "RCONHK16": 6.0, "RCONHK17": 4.0}
    rows = [{"rssd": 1, "period": "2017-03-31", **leg, "RCON6631": 50.0},
            {"rssd": 1, "period": "2017-06-30", **leg, "RCON6631": 70.0},
            {"rssd": 1, "period": "2017-09-30", **leg, "RCON6631": 70.0, "RCFN2200": 5.0}]   # foreign NIB missing
    w = _hy(rows).set_index("period")
    assert w.loc["2017-06-30", "NIB_AVG"] == pytest.approx(60.0)
    assert w.loc["2017-06-30", "TOT_AVG"] == pytest.approx(w.loc["2017-06-30", "A"] + 60.0)
    assert pd.isna(w.loc["2017-09-30", "TOT_AVG"])                    # foreign offices but no RCFN6631: not filled
