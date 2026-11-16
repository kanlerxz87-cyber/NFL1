#!/usr/bin/env python3
"""E4 NWS hourly snapshot for Week-11 venues (invoked by .github/workflows/nws-snapshot-cc5a9cdd.yml).

For each venue in data/session-cc5a9cdd/venue_week11.json:
  1. stadium coordinates via Nominatim (query INPUT only - never published as a weather value),
  2. NWS api.weather.gov /points -> office/gridId/gridX/gridY + forecastHourly URL (official),
  3. NWS forecast/hourly -> periods overlapping kickoff +/- 2h (official values, per-row source link).

Writes data/session-cc5a9cdd/nws_hourly_w11.json. Always exits 0: any failure is recorded
as a per-venue flag instead of an exception, so the workflow never reports red.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

VENUE_FILE = "data/session-cc5a9cdd/venue_week11.json"
OUT_FILE = "data/session-cc5a9cdd/nws_hourly_w11.json"
UA = {"User-Agent": "kanlerxz87-cyber/NFL1 venue-weather-audit (github.com/kanlerxz87-cyber/NFL1)"}
NY = ZoneInfo("America/New_York")


def get_json(url, params=None, tries=3):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    last = 0
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            if exc.code in (400, 404):
                return exc.code, None
            last = exc.code
        except Exception as exc:  # noqa: BLE001 - record, retry, never crash the run
            last = str(exc)
        time.sleep(2 + 2 * attempt)
    return 0, {"error": str(last)}


def find_coords(stadium, location):
    for query in (f"{stadium}, {location}", stadium):
        time.sleep(1.2)
        status, data = get_json(
            "https://nominatim.openstreetmap.org/search",
            {"q": query, "format": "jsonv2", "limit": 1},
        )
        if status == 200 and data:
            hit = data[0]
            return {
                "lat": float(hit["lat"]),
                "lon": float(hit["lon"]),
                "display_name": hit["display_name"],
                "query_used": query,
                "nominatim_link": "https://nominatim.openstreetmap.org/search?q="
                + urllib.parse.quote(query)
                + "&format=jsonv2",
            }
    return None


def parse_kickoff_utc(gameday, kickoff_et):
    local = datetime.strptime(f"{gameday} {kickoff_et}", "%Y-%m-%d %I:%M %p")
    return local.replace(tzinfo=NY).astimezone(timezone.utc)


def hourly_periods_for_window(hourly_json, kickoff_utc):
    flags = []
    window_lo = kickoff_utc - timedelta(hours=2)
    window_hi = kickoff_utc + timedelta(hours=2)
    periods = []
    for period in hourly_json.get("properties", {}).get("periods", []):
        start = datetime.fromisoformat(period["startTime"])
        end = datetime.fromisoformat(period["endTime"])
        if start < window_hi and end > window_lo:
            pop = (period.get("probabilityOfPrecipitation") or {}).get("value")
            periods.append(
                {
                    "start_time": period["startTime"],
                    "temperature_f": period.get("temperature"),
                    "wind_speed": period.get("windSpeed"),
                    "wind_direction": period.get("windDirection"),
                    "pop_pct": pop,  # None = not printed by NWS, kept blank (never 0-guessed)
                    "short_forecast": period.get("shortForecast"),
                    "relative_humidity_pct": (period.get("relativeHumidity") or {}).get("value"),
                }
            )
    if not periods:
        flags.append("kickoff_outside_hourly_horizon")
        allp = hourly_json.get("properties", {}).get("periods", [])
        if allp:
            nearest = min(
                allp,
                key=lambda p: abs(
                    (datetime.fromisoformat(p["startTime"]) - kickoff_utc).total_seconds()
                ),
            )
            pop = (nearest.get("probabilityOfPrecipitation") or {}).get("value")
            periods = [
                {
                    "start_time": nearest["startTime"],
                    "temperature_f": nearest.get("temperature"),
                    "wind_speed": nearest.get("windSpeed"),
                    "wind_direction": nearest.get("windDirection"),
                    "pop_pct": pop,
                    "short_forecast": nearest.get("shortForecast"),
                    "relative_humidity_pct": (nearest.get("relativeHumidity") or {}).get("value"),
                }
            ]
    return periods, flags


def process_venue(entry):
    out_row = {
        "game_id": entry["game_id"],
        "venue_game": f"{entry['away']}@{entry['home']}",
        "stadium_as_printed": entry["stadium_as_printed"],
        "location_as_printed": entry["location_as_printed"],
        "gameday": entry["gameday"],
        "kickoff_et_printed": entry["kickoff_et"],
        "flags": [],
        "coords": None,
        "nws_points": None,
        "hourly": None,
    }
    flags = out_row["flags"]
    try:
        kickoff_utc = parse_kickoff_utc(entry["gameday"], entry["kickoff_et"])
        out_row["kickoff_utc"] = kickoff_utc.isoformat()
    except Exception as exc:  # noqa: BLE001
        flags.append("kickoff_parse_failed")
        out_row["kickoff_parse_error"] = str(exc)
        return out_row

    coords = find_coords(entry["stadium_as_printed"], entry["location_as_printed"])
    if not coords:
        flags.append("coords_unresolved")
        return out_row
    out_row["coords"] = coords

    status, points = get_json(
        f"https://api.weather.gov/points/{coords['lat']:.4f},{coords['lon']:.4f}"
    )
    if status == 404:
        flags.append("outside_nws_coverage")  # e.g. Mexico City - stays blank + flagged
        out_row["nws_points"] = {"url": points if isinstance(points, dict) else None, "status": 404}
        return out_row
    if status != 200 or not points:
        flags.append("nws_points_unreachable")
        out_row["nws_points"] = {"status": status}
        return out_row

    props = points.get("properties", {})
    out_row["nws_points"] = {
        "url": points.get("id"),
        "status": 200,
        "cwa": props.get("cwa"),
        "grid_id": props.get("gridId"),
        "grid_x": props.get("gridX"),
        "grid_y": props.get("gridY"),
        "forecast_hourly_url": props.get("forecastHourly"),
        "forecast_zone": props.get("forecastZone"),
        "time_zone": props.get("timeZone"),
    }
    time.sleep(0.7)
    status, hourly = get_json(props["forecastHourly"])
    if status != 200 or not hourly:
        flags.append("nws_hourly_unreachable")
        out_row["hourly"] = {"status": status}
        return out_row

    hprops = hourly.get("properties", {})
    periods, hflags = hourly_periods_for_window(hourly, kickoff_utc)
    flags.extend(hflags)
    out_row["hourly"] = {
        "status": 200,
        "source_url": props["forecastHourly"],
        "generated_at": hprops.get("generatedAt"),
        "update_time": hprops.get("updateTime"),
        "valid_times": hprops.get("validTimes"),
        "window_kickoff_utc": [
            (kickoff_utc - timedelta(hours=2)).isoformat(),
            (kickoff_utc + timedelta(hours=2)).isoformat(),
        ],
        "periods": periods,
    }
    return out_row


def main():
    venues = json.load(open(VENUE_FILE))
    rows = []
    for game_id in sorted(venues, key=lambda k: (venues[k]["gameday"], venues[k]["kickoff_et"])):
        rows.append(process_venue(venues[game_id]))
        time.sleep(0.5)
    out = {
        "what": "Week-11 NWS hourly overlay (E4/IN-29 part 2): hourly wind/temperature/precipitation around kickoff per venue",
        "hourly_source": "NOAA/NWS api.weather.gov gridpoints forecast/hourly (official, linked per row)",
        "coords_source": "nominatim.openstreetmap.org used only as query input to NWS /points; published values are all NWS",
        "method": "kickoff parsed from the official nfl.com schedule transcript (venue_week11.json); window = kickoff +/- 2h",
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(rows),
        "flagged_count": sum(1 for r in rows if r["flags"]),
        "rows": rows,
    }
    with open(OUT_FILE, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {OUT_FILE}: {len(rows)} venues, {out['flagged_count']} flagged")


if __name__ == "__main__":
    main()  # never raises: per-venue failures become flags
