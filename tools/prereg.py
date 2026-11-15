#!/usr/bin/env python3
"""Pre-registration ledger for the forward evaluation of NFL forecasts (session 739408a8-nfl1, task P1).

Subcommands
  freeze    write data/prereg/registry.json (refuses to overwrite an existing registry)
  forecast  write the pre-kickoff forecast ledger for a week (refuses if any kickoff has passed)
  check     recompute every frozen hash and forecast from the official inputs; exit 1 on any failure
  render    write prereg/index.html from the registry, the ledger and the official inputs

Design rules
  * A rule is frozen by hashing its canonical JSON (sorted keys, no spaces). Editing a rule after the
    registration commit changes the hash, and `check` fails.
  * A forecast is a function of the official inputs file only. `check` recomputes it and compares.
  * Every forecast carries recorded_utc. `check` fails unless recorded_utc is strictly before kickoff.
  * A strategy whose formula contains an unfixed coefficient, or that has no measurable market,
    is listed as not_registrable with the reason. It is not scored.
  * Backtest results are never admitted to the leaderboard (rule LB-ADMIT).

Only official inputs are used: nfl.com standings and nfl.com schedule, both saved in
data/prereg/official_inputs_2026-11-15.json with their source URLs.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREREG = ROOT / "data" / "prereg"
INPUTS = PREREG / "official_inputs_2026-11-15.json"
REGISTRY = PREREG / "registry.json"
LEDGER = PREREG / "forecasts_2026_wk11.json"
STRATEGIES = ROOT / "data" / "strategies.json"
LEADERBOARD_BACKTEST = ROOT / "data" / "s9cb" / "leaderboard.json"
PAGE = ROOT / "prereg" / "index.html"

ET = dt.timezone(dt.timedelta(hours=-5))  # US Eastern, standard time in November
SEED = "20261115"
BOOT_SAMPLES = 10000
TRIALS_REGISTERED = 2  # PR-01 and PR-02 are scored; PR-03 is a control and is not counted as a trial

SRC_STANDINGS = "https://www.nfl.com/standings/league/2026/reg"
SRC_SCHEDULE = "https://www.nfl.com/schedules/2026/by-week/week-11"
SRC_INJURY = "https://www.nfl.com/injuries/league/2026/reg10"

# ---- frozen rule text. Changing anything here changes the hash and fails `check`. ----
FROZEN_RULES = [
    {
        "id": "PR-01",
        "name": "No-skill benchmark (constant 0.5)",
        "track": "Single bet (home-win probability)",
        "forecast": "p_home = 0.5 for every game",
        "inputs": [],
        "role": "benchmark against which Brier skill is measured",
    },
    {
        "id": "PR-02",
        "name": "Record-share forecast",
        "track": "Single bet (home-win probability)",
        "forecast": "p_home = PCT_home / (PCT_home + PCT_away), where PCT is the official standings value as printed at the time of the forecast",
        "inputs": [SRC_STANDINGS, SRC_SCHEDULE],
        "role": "candidate forecaster, scored against PR-01",
    },
    {
        "id": "PR-03",
        "name": "Seeded random control",
        "track": "Control (random picks)",
        "forecast": "p_home = u, where u = int(sha256('20261115:' + game_id)[:13], 16) / 16**13",
        "inputs": [SRC_SCHEDULE],
        "role": "control: a forecaster with no information; expected Brier near 1/3",
    },
]

SCORING = {
    "metric": "Brier score on the home-win probability: mean of (p_home - y)^2, y = 1 if the home team won, else 0",
    "unit": "game; each game is one forecast per registered forecaster",
    "exclusions": "ties, postponed and cancelled games are excluded and their count is published",
    "benchmark": "PR-01",
    "skill": "Brier skill score BSS = 1 - BS(forecaster) / BS(PR-01)",
    "uncertainty": "week-cluster bootstrap: resample whole weeks with replacement, %d draws, seed %s" % (BOOT_SAMPLES, SEED),
    "minimum_games": 100,
    "multiplicity": "registered trials = %d; two-sided alpha 0.05 Bonferroni-corrected to 0.025, so a pass needs the 1.25th percentile of the bootstrap BSS distribution to be above 0" % TRIALS_REGISTERED,
    "pass_rule": "PASS only if scored games >= minimum_games AND the corrected lower bound of BSS > 0. Otherwise the result is published as NOT PASSED.",
    "roi": "not computed: no official source publishes NFL prices (flag F09 on the Flagged page). ROI cannot be a gate until a price source is registered.",
}

WINDOW = {
    "sample": "2026 regular-season games from Week 11 onward, each forecast recorded before its own kickoff",
    "weeks_in_scope": "11-18 (Week 11 is the first frozen ledger)",
    "first_kickoff_et": "2026-11-19T20:15 (Colts at Texans, official schedule)",
}

LB_ADMIT = {
    "id": "LB-ADMIT",
    "rule": "Only forward forecasts recorded before kickoff and scored after the final whistle may appear on the leaderboard. Backtest or in-sample results never appear on the leaderboard.",
    "src": [SRC_SCHEDULE],
}


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def parse_iso_et(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=ET).astimezone(dt.timezone.utc)


def unit_draw(game_id):
    h = hashlib.sha256(("%s:%s" % (SEED, game_id)).encode()).hexdigest()
    return int(h[:13], 16) / 16 ** 13


def load_inputs():
    return json.loads(INPUTS.read_text())


def not_registrable_rows():
    """Strategies that cannot be frozen, with the reason taken from data/strategies.json."""
    rows = []
    strategies = json.loads(STRATEGIES.read_text()) if STRATEGIES.exists() else []
    for s in strategies:
        formula = s.get("formula", "")
        if "blank" in formula:
            reason = "formula has an unfixed coefficient (%s)" % formula
        elif s["id"] == "ST-09":
            reason = "a filter on official status, not a forecast; no official prop prices exist to score it"
        else:
            reason = "not checked"
        rows.append({
            "id": s["id"],
            "name": s["name"],
            "status": "not_registrable",
            "reason": reason,
            "src": ["https://github.com/kanlerxz87-cyber/NFL1/blob/main/data/strategies.json", SRC_INJURY],
        })
    rows.append({
        "id": "CTRL-FAV",
        "name": "Favourites-only control",
        "status": "not_registrable",
        "reason": "needs the market favourite; no official source publishes NFL prices (flag F09). A record-based favourite (PR-02) is used instead.",
        "src": [SRC_STANDINGS],
    })
    return rows


def cmd_freeze(args):
    if REGISTRY.exists() and not args.force:
        sys.exit("refusing to overwrite %s (the registry is frozen; use a new file to amend)" % REGISTRY)
    rules = []
    for r in FROZEN_RULES:
        entry = dict(r)
        entry["status"] = "registered"
        entry["rule_sha256"] = canonical_hash({k: r[k] for k in r})
        rules.append(entry)
    reg = {
        "schema": "prereg-registry/1",
        "session": "739408a8-nfl1",
        "registered_utc": utc_now().isoformat().replace("+00:00", "Z"),
        "registration_note": "Rules, window, scoring and gates are fixed here before any forward result exists. The git commit that adds this file is the registration; its hash is the registration identifier.",
        "window": WINDOW,
        "scoring": SCORING,
        "trials_registered": TRIALS_REGISTERED,
        "forecasters": rules,
        "not_registrable": not_registrable_rows(),
        "leaderboard_rules": [LB_ADMIT],
        "inputs_file": str(INPUTS.relative_to(ROOT)),
        "inputs_sha256": hashlib.sha256(INPUTS.read_bytes()).hexdigest(),
    }
    REGISTRY.write_text(json.dumps(reg, indent=2) + "\n")
    print("wrote", REGISTRY.relative_to(ROOT))


def build_forecasts(inputs, recorded):
    standings = {r["team"]: r for r in inputs["standings"]["rows"]}
    out = []
    for g in inputs["schedule"]["games"]:
        a, h = standings[g["away"]], standings[g["home"]]
        kickoff = parse_iso_et(g["kickoff_et"])
        if recorded >= kickoff:
            raise SystemExit("refusing to write forecasts: %s kicks off at %s and it is now %s"
                             % (g["game_id"], kickoff.isoformat(), recorded.isoformat()))
        p02 = h["PCT"] / (h["PCT"] + a["PCT"]) if (h["PCT"] + a["PCT"]) > 0 else 0.5
        out.append({
            "game_id": g["game_id"],
            "away": g["away"],
            "home": g["home"],
            "kickoff_utc": kickoff.isoformat().replace("+00:00", "Z"),
            "recorded_utc": recorded.isoformat().replace("+00:00", "Z"),
            "inputs": {"away_PCT": a["PCT"], "home_PCT": h["PCT"], "away_record": "%d-%d-%d" % (a["W"], a["L"], a["T"]),
                       "home_record": "%d-%d-%d" % (h["W"], h["L"], h["T"])},
            "p_home": {"PR-01": 0.5, "PR-02": round(p02, 6), "PR-03": round(unit_draw(g["game_id"]), 6)},
            "outcome": None,
        })
    return out


def cmd_forecast(args):
    if LEDGER.exists() and not args.force:
        sys.exit("refusing to overwrite %s" % LEDGER)
    inputs = load_inputs()
    recorded = utc_now()
    games = build_forecasts(inputs, recorded)
    led = {
        "schema": "prereg-forecast-ledger/1",
        "week": inputs["schedule"]["week"],
        "recorded_utc": recorded.isoformat().replace("+00:00", "Z"),
        "rule": "forecasts are functions of data/prereg/official_inputs_2026-11-15.json; see registry.json",
        "games": games,
    }
    LEDGER.write_text(json.dumps(led, indent=2) + "\n")
    print("wrote", LEDGER.relative_to(ROOT), "games:", len(games), "recorded:", led["recorded_utc"])


def cmd_check(args):
    failures, notes = [], []
    reg = json.loads(REGISTRY.read_text())
    # 1. each frozen rule still hashes to its registered value
    for r in reg["forecasters"]:
        body = {k: r[k] for k in FROZEN_RULES[[x["id"] for x in FROZEN_RULES].index(r["id"])]}
        if canonical_hash(body) != r["rule_sha256"]:
            failures.append("rule %s no longer matches its registered hash" % r["id"])
    # 2. the official inputs have not changed since registration
    if hashlib.sha256(INPUTS.read_bytes()).hexdigest() != reg["inputs_sha256"]:
        failures.append("official inputs file changed since registration")
    # 3. not-registrable strategies carry a reason and a source
    for s in reg["not_registrable"]:
        if not s.get("reason") or not s.get("src"):
            failures.append("not-registrable row %s lacks a reason or source" % s["id"])
    # 4. the forecast ledger is reproducible from the inputs and was recorded before kickoff
    if LEDGER.exists():
        led = json.loads(LEDGER.read_text())
        inputs = load_inputs()
        rec = dt.datetime.fromisoformat(led["recorded_utc"].replace("Z", "+00:00"))
        try:
            expect = {g["game_id"]: g for g in build_forecasts(inputs, rec)}
        except SystemExit as exc:  # a forecast recorded after kickoff cannot be rebuilt; report it as a failure
            expect = {}
            failures.append("ledger recorded too late: %s" % exc)
        for g in led["games"]:
            e = expect.get(g["game_id"])
            if e is None:
                failures.append("ledger game %s not in inputs" % g["game_id"])
                continue
            for k in ("PR-01", "PR-02", "PR-03"):
                if abs(g["p_home"][k] - e["p_home"][k]) > 1e-9:
                    failures.append("%s %s does not reproduce from inputs" % (g["game_id"], k))
            if dt.datetime.fromisoformat(g["recorded_utc"].replace("Z", "+00:00")) >= parse_iso_et(
                    next(x["kickoff_et"] for x in inputs["schedule"]["games"] if x["game_id"] == g["game_id"])):
                failures.append("%s was recorded at or after kickoff" % g["game_id"])
        notes.append("ledger: %d games, all recorded before their kickoff" % len(led["games"]))
    else:
        failures.append("forecast ledger missing")
    # 5. warning, not a failure: a backtest-labelled leaderboard exists elsewhere in the repo (flag F-7810-09)
    if LEADERBOARD_BACKTEST.exists():
        notes.append("WARNING (open flag F-7810-09): %s holds backtest rows; rule LB-ADMIT forbids them on the leaderboard" % LEADERBOARD_BACKTEST.relative_to(ROOT))
    for n in notes:
        print(n)
    if failures:
        for f in failures:
            print("FAIL:", f)
        return 1
    print("PASS: %d frozen rules, %d not-registrable rows" % (len(reg["forecasters"]), len(reg["not_registrable"])))
    return 0


def esc(x):
    return html.escape(str(x))


def cmd_render(args):
    reg = json.loads(REGISTRY.read_text())
    led = json.loads(LEDGER.read_text())
    inputs = load_inputs()
    h_reg = esc(reg["registered_utc"])
    rules_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td><code>%s</code></td><td>%s</td></tr>" % (
            esc(r["id"]), esc(r["name"]), esc(r["forecast"]), esc(r["rule_sha256"][:16]),
            '<a href="%s">standings + schedule</a>' % esc(SRC_STANDINGS) if r["inputs"] else "none (benchmark)")
        for r in reg["forecasters"])
    nr_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(r["id"]), esc(r["name"]), esc(r["reason"]),
            " ".join('<a href="%s">source</a>' % esc(u) for u in r["src"]))
        for r in reg["not_registrable"])
    fc_rows = "".join(
        "<tr><td>%s</td><td>%s @ %s</td><td>%s</td><td>%s %.3f (%s)</td><td>%s %.3f (%s)</td><td>%.3f</td><td>%.3f</td><td>%s</td><td><a href=\"%s\">standings</a> / <a href=\"%s\">schedule</a></td></tr>" % (
            esc(g["game_id"]), esc(g["away"]), esc(g["home"]),
            esc(next(x["kickoff_et"] for x in inputs["schedule"]["games"] if x["game_id"] == g["game_id"]).replace("T", " ") + " ET"),
            esc(g["away"]), g["inputs"]["away_PCT"], esc(g["inputs"]["away_record"]), esc(g["home"]), g["inputs"]["home_PCT"], esc(g["inputs"]["home_record"]),
            g["p_home"]["PR-02"], g["p_home"]["PR-03"], esc(g["recorded_utc"]),
            esc(SRC_STANDINGS), esc(SRC_SCHEDULE))
        for g in led["games"])
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pre-registration ledger | NFL Decision Lab</title>
<style>body{font-family:system-ui,sans-serif;max-width:1200px;margin:24px auto;padding:0 16px;color:#1b1b1b}
table{border-collapse:collapse;width:100%%;margin:8px 0 24px;font-size:14px}th,td{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f3f5f8}code{font-size:12px}.note{background:#fff8e1;border-left:4px solid #f0b400;padding:8px 12px}</style></head><body>
<p><a href="../index.html">Home</a></p>
<h1>Pre-registration ledger (forward test)</h1>
<p class="note">Rules, window, scoring and gates were frozen at <strong>%(h_reg)s</strong> (UTC) by the commit that adds <code>data/prereg/registry.json</code>. Every forecast below was recorded before its own kickoff and is a function of the official inputs file only. No result is shown because no Week 11 game has been played when this page is built. Generated by <code>tools/prereg.py render</code>.</p>
<h2>Scoring and gates</h2>
<table><tr><th>Item</th><th>Frozen value</th></tr>
<tr><td>Metric</td><td>%(metric)s</td></tr>
<tr><td>Benchmark</td><td>%(benchmark)s</td></tr>
<tr><td>Skill</td><td>%(skill)s</td></tr>
<tr><td>Uncertainty</td><td>%(uncertainty)s</td></tr>
<tr><td>Minimum scored games</td><td>%(minimum_games)s</td></tr>
<tr><td>Multiplicity</td><td>%(multiplicity)s</td></tr>
<tr><td>Pass rule</td><td>%(pass_rule)s</td></tr>
<tr><td>ROI</td><td>%(roi)s</td></tr></table>
<h2>Frozen forecasters</h2>
<table><tr><th>ID</th><th>Name</th><th>Forecast rule</th><th>Rule hash (first 16)</th><th>Official inputs</th></tr>%(rules_rows)s</table>
<h2>Week 11 forecasts (recorded %(led_rec)s UTC)</h2>
<table><tr><th>Game</th><th>Away @ Home</th><th>Kickoff</th><th>Away PCT</th><th>Home PCT</th><th>PR-02 p(home)</th><th>PR-03 p(home)</th><th>Recorded (UTC)</th><th>Sources</th></tr>%(fc_rows)s</table>
<p>The PR-01 forecast is 0.5 for every game and is not repeated here. Percentages are the official published values (W + 0.5 T) / G.</p>
<h2>Not registrable (listed, not scored)</h2>
<table><tr><th>ID</th><th>Name</th><th>Reason</th><th>Sources</th></tr>%(nr_rows)s</table>
<h2>Leaderboard admission</h2>
<p>%(lb)s</p>
</body></html>""" % {
        "h_reg": h_reg, "metric": esc(reg["scoring"]["metric"]), "benchmark": esc(reg["scoring"]["benchmark"]),
        "skill": esc(reg["scoring"]["skill"]), "uncertainty": esc(reg["scoring"]["uncertainty"]),
        "minimum_games": esc(reg["scoring"]["minimum_games"]), "multiplicity": esc(reg["scoring"]["multiplicity"]),
        "pass_rule": esc(reg["scoring"]["pass_rule"]), "roi": esc(reg["scoring"]["roi"]),
        "rules_rows": rules_rows, "led_rec": esc(led["recorded_utc"]), "fc_rows": fc_rows,
        "nr_rows": nr_rows, "lb": esc(LB_ADMIT["rule"]),
    }
    PAGE.parent.mkdir(parents=True, exist_ok=True)
    PAGE.write_text(page)
    print("wrote", PAGE.relative_to(ROOT))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("freeze"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_freeze)
    p = sub.add_parser("forecast"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_forecast)
    p = sub.add_parser("check"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("render"); p.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    rc = args.fn(args)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
