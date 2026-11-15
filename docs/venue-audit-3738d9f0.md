# Week 11 venue audit — session `3738d9f0-nfl1`

**Checked:** 2026-11-15 (UTC) · **audit record timestamp:** `2026-11-15T12:29:01Z`  
**Scope:** Official NFL Week 11 schedule and all 13 linked Game Center pages. This audit adds a dated source capture; it does not update existing model, schedule, site, or landing-page datasets.

## Sources and method

- [NFL 2026 Week 11 schedule](https://www.nfl.com/schedules/2026/by-week/week-11) — all 13 matchups, displayed dates/times/broadcast networks, and the six-team bye list.
- Each row below links to its own official NFL Game Center. The location and stadium fields are transcribed from that page's **Game Info** section, in the wording displayed. Abbreviations, venue names, and city labels are not normalized or filled in from inference.
- The live schedule and Game Center pages were read using Arena's `fetch_page` tool. The tool does not expose a response-level timestamp or raw HTML download. The recorded audit timestamp is when the row transcription was logged; the source-observation bounds and this limitation are stated in [`sources_venues_2026-11-15.json`](../data/official/2026-11-15/sources_venues_2026-11-15.json). Raw page bodies were not retained.
- Machine check: [`verify_week11_venues_3738d9f0.py`](../tools/verify_week11_venues_3738d9f0.py) validates the offline row structure, provenance links, timestamp consistency, schedule/venue matchup coverage, and evidence hashes. It does **not** fetch or independently re-read live pages; manual source-to-row transcription was performed for all 13 links.

## Row-level Game Center transcription

| Week 11 game | Location as displayed | Stadium label as displayed | Review | Official row source |
| --- | --- | --- | --- | --- |
| IND@HOU | HOUSTON, TX | RELIANT STADIUM | **Needs review:** the official schedule page's hotel-search link encodes `NRG Stadium`; preserve the Game Center label and do not infer a canonical replacement. | [Colts at Texans — Game Center](https://www.nfl.com/games/colts-at-texans-2026-reg-11) |
| MIA@BUF | ORCHARD PARK, NY | HIGHMARK STADIUM | — | [Dolphins at Bills — Game Center](https://www.nfl.com/games/dolphins-at-bills-2026-reg-11) |
| BAL@CAR | CHARLOTTE, NC | BANK OF AMERICA STADIUM | — | [Ravens at Panthers — Game Center](https://www.nfl.com/games/ravens-at-panthers-2026-reg-11) |
| NO@CHI | CHICAGO, IL | SOLDIER FIELD | — | [Saints at Bears — Game Center](https://www.nfl.com/games/saints-at-bears-2026-reg-11) |
| TEN@DAL | ARLINGTON, TX | AT&T STADIUM | — | [Titans at Cowboys — Game Center](https://www.nfl.com/games/titans-at-cowboys-2026-reg-11) |
| TB@DET | DETROIT, MI | FORD FIELD | — | [Buccaneers at Lions — Game Center](https://www.nfl.com/games/buccaneers-at-lions-2026-reg-11) |
| AZ@KC | KANSAS CITY, MO | ARROWHEAD STADIUM | **Needs review:** the official schedule page's hotel-search link encodes `GEHA Field at Arrowhead Stadium`; preserve the Game Center label and do not infer a canonical replacement. | [Cardinals at Chiefs — Game Center](https://www.nfl.com/games/cardinals-at-chiefs-2026-reg-11) |
| PIT@PHI | PHILADELPHIA, PA | LINCOLN FINANCIAL FIELD | — | [Steelers at Eagles — Game Center](https://www.nfl.com/games/steelers-at-eagles-2026-reg-11) |
| NYJ@LAC | INGLEWOOD, CA | SOFI STADIUM | — | [Jets at Chargers — Game Center](https://www.nfl.com/games/jets-at-chargers-2026-reg-11) |
| JAX@NYG | EAST RUTHERFORD, NJ | METLIFE STADIUM | — | [Jaguars at Giants — Game Center](https://www.nfl.com/games/jaguars-at-giants-2026-reg-11) |
| LV@DEN | DENVER, CO | EMPOWER FIELD AT MILE HIGH | — | [Raiders at Broncos — Game Center](https://www.nfl.com/games/raiders-at-broncos-2026-reg-11) |
| MIN@SF | MEXICO CITY | ESTADIO BANORTE | — | [Vikings at 49ers — Game Center](https://www.nfl.com/games/vikings-at-49ers-2026-reg-11) |
| CIN@WAS | LANDOVER, MD | NORTHWEST STADIUM | **Needs review:** the official schedule page's hotel-search link encodes `FedEx Field`; preserve the Game Center label and do not infer a canonical replacement. | [Bengals at Commanders — Game Center](https://www.nfl.com/games/bengals-at-commanders-2026-reg-11) |

The review notes describe strings found in the official schedule page's outbound hotel-search link, not a separate stadium field on that page. The captured Game Center values are confirmed **as displayed**; the conflicting source-page strings leave the current canonical venue naming unresolved for IND@HOU, AZ@KC, and CIN@WAS. No stadium label was silently corrected. These are published review flags, not blockers.

## Schedule capture and verification result

The linked NFL schedule page showed 13 games and six bye teams. Its text labels the Rams as `LAR` in the bye list while the adjacent logo asset uses `LA`; the source convention is preserved in metadata rather than normalized. Fresh row-level schedule fields are in [`week11_schedule_2026-11-15.tsv`](../data/official/2026-11-15/week11_schedule_2026-11-15.tsv); Game Center venue fields are in [`week11_game_centres.tsv`](../data/official/2026-11-15/week11_game_centres.tsv).

Command:

```text
python3 tools/verify_week11_venues_3738d9f0.py
```

Result: **PASS** — 13 schedule rows, 13 venue rows, 13/13 matchups paired, 26 unique clubs, all rows have official NFL source links and consistent audit timestamps, and three venue-name review flags were preserved. Full per-check results and SHA-256 hashes are in [`week11_venue_verification_3738d9f0.json`](../data/official/2026-11-15/week11_venue_verification_3738d9f0.json). The PASS applies only to the offline structure/provenance checks; it does not imply the flagged canonical naming differences are resolved.
