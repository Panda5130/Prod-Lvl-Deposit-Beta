"""Fixed list of FFIEC Call Report item codes used by the pilot.

Every code was checked against the current FFIEC/Federal Reserve MDRM data dictionary
(https://www.federalreserve.gov/apps/mdrm/pdf/MDRM.zip -> MDRM_CSV.csv) on 2026-11-12: name and
Start/End Date. None came from memory. Re-run the existence check with
    python ffiec/data_build/ffiec_pull.py --verify-items <path to MDRM_CSV.csv>
Item key = MDRM mnemonic + item code.

kind "ytd"   : Schedule RI flows, reported year-to-date; converted to quarterly in ffiec_pull.to_quarterly.
kind "level" : balances and quarterly averages.
"""

ITEMS = {
    # code: (kind, group, MDRM name (abridged))
    # Totals that tie to BankFind DEP
    "RCFD2200": ("level", "total", "Total deposits (consolidated, FFIEC 031 filers)"),
    "RCON2200": ("level", "total", "Total deposits (domestic offices)"),
    "RCFN2200": ("level", "total", "Total deposits (foreign offices)"),
    # RI deposit interest expense, domestic (ties to EDEPDOMQ). Time-deposit split changed in 2017.
    "RIAD4508": ("ytd", "ri_dom", "Interest on transaction accounts"),
    "RIAD0093": ("ytd", "ri_dom", "Interest on savings deposits (including MMDAs)"),
    "RIADA517": ("ytd", "ri_dom_old", "Interest on time deposits of $100,000 or more (to 2016)"),
    "RIADA518": ("ytd", "ri_dom_old", "Interest on time deposits of less than $100,000 (to 2016)"),
    "RIADHK03": ("ytd", "ri_dom_new", "Interest on time deposits of $250,000 or less (2017 on)"),
    "RIADHK04": ("ytd", "ri_dom_new", "Interest on time deposits of more than $250,000 (2017 on)"),
    # RI foreign offices (ties to EDEPFORQ)
    "RIAD4172": ("ytd", "ri_for", "Interest on deposits in foreign offices"),
    # RC-K quarterly averages
    "RCON3485": ("level", "rck_avg", "Quarterly average: transaction accounts (domestic)"),
    "RCONB563": ("level", "rck_avg", "Quarterly average: savings deposits incl. MMDAs"),
    "RCONA529": ("level", "rck_avg", "Quarterly average: time deposits < $100,000 (to 2016)"),
    "RCONA514": ("level", "rck_avg", "Quarterly average: time deposits >= $100,000 (to 2016)"),
    "RCFN3404": ("level", "rck_avg", "Quarterly average: interest-bearing deposits in foreign offices"),
    # RC-E balances (time-deposit balances by size; 2017 on uses the $250k split)
    "RCON2215": ("level", "rce_bal", "Total transaction accounts"),
    "RCON6648": ("level", "rce_bal", "Time deposits < $100,000 (to 2016)"),
    "RCON2604": ("level", "rce_bal", "Time deposits >= $100,000 (to 2016)"),
    "RCONHK16": ("level", "rce_bal", "Time deposits <= $250,000 (2017 on)"),
    "RCONHK17": ("level", "rce_bal", "Time deposits > $250,000 (2017 on)"),
}
# Open items: no MDRM code was found for RC-K time-deposit quarterly averages from 2017 on, nor for the RC-K
# noninterest-bearing deposit average. The materiality script reports those quarters as coverage gaps.
RCK_DOM_AVG = {"old": ["RCON3485", "RCONB563", "RCONA529", "RCONA514"], "new": None}
RI_DOM_CODES = {"old": ["RIAD4508", "RIAD0093", "RIADA517", "RIADA518"],
                "new": ["RIAD4508", "RIAD0093", "RIADHK03", "RIADHK04"]}
RI_FOR_CODES = ["RIAD4172"]
NEW_REGIME_START = "2017-03-31"


def ri_dom_codes(period):
    return RI_DOM_CODES["new" if str(period) >= NEW_REGIME_START else "old"]
