#!/usr/bin/env python3
"""Check the Game Book source register and its generated Referee page.

Run from the repository root: python3 referee/tools/check_gamebooks.py
Standard library only; no official source is fetched by this check.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

try:  # script invocation
    from build_gamebooks import load_register, validate_register
except ImportError:  # package import from tests
    from referee.tools.build_gamebooks import load_register, validate_register

ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = ROOT / "gamebooks.html"


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self.table: dict | None = None
        self.row: dict | None = None
        self.cell: dict | None = None
        self.in_thead = False

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "table":
            self.table = {"headers": [], "rows": []}
        elif tag == "thead":
            self.in_thead = True
        elif tag == "tbody":
            self.in_thead = False
        elif tag == "tr" and self.table is not None:
            self.row = {"cells": [], "links": []}
        elif tag in {"td", "th"} and self.row is not None:
            self.cell = {"text": [], "links": []}
        elif tag == "a" and self.cell is not None and values.get("href"):
            self.cell["links"].append(values["href"])

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.cell is not None and self.row is not None:
            text = " ".join(" ".join(self.cell["text"]).split())
            cell = {"text": text, "links": list(self.cell["links"])}
            self.row["cells"].append(cell)
            if tag == "th" and self.in_thead and self.table is not None:
                self.table["headers"].append(text)
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            self.row["links"] = [link for cell in self.row["cells"] for link in cell["links"]]
            self.table["rows"].append(self.row)
            self.row = None
        elif tag == "tbody":
            self.in_thead = False
        elif tag == "thead":
            self.in_thead = False
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def check_page(page_html: str, register: dict) -> list[str]:
    problems: list[str] = []
    parser = TableParser()
    parser.feed(page_html)
    required = {"Date", "Matchup", "Game Center venue", "Game Book PDF", "Actual starters",
                "Official inactives", "Snap counts", "Status at observation", "Source"}
    target = next((table for table in parser.tables if required.issubset(set(table["headers"]))), None)
    if target is None:
        return ["generated page does not contain the expected sourced fixture table"]
    data_rows = target["rows"][1:]
    if len(data_rows) != len(register["rows"]):
        problems.append(f"expected {len(register['rows'])} fixture rows, found {len(data_rows)}")

    headers = target["headers"]
    indexes = {name: headers.index(name) for name in required}
    player_fields = (("Actual starters", "actual starters"),
                     ("Official inactives", "official inactives"),
                     ("Snap counts", "snap counts"))
    for i, (table_row, fixture) in enumerate(zip(data_rows, register["rows"]), start=1):
        cells = table_row["cells"]
        if len(cells) != len(headers):
            problems.append(f"table row {i} has {len(cells)} cells; expected {len(headers)}")
            continue

        if cells[indexes["Date"]]["text"] != fixture["date"]:
            problems.append(f"table row {i} date does not match {fixture['game_id']}")
        if fixture["game_id"] not in cells[indexes["Matchup"]]["text"]:
            problems.append(f"table row {i} does not identify fixture {fixture['game_id']}")
        venue_cell = cells[indexes["Game Center venue"]]["text"]
        if fixture["venue"] not in venue_cell or fixture["location"] not in venue_cell:
            problems.append(f"table row {i} venue/location does not match {fixture['game_id']}")

        source_links = set(cells[indexes["Source"]]["links"])
        expected_sources = {fixture["game_center_url"], register["schedule_url"]}
        if not expected_sources.issubset(source_links):
            problems.append(f"table row {i} must link its own official Game Center and the Week 10 schedule")
        for url in source_links:
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname != "www.nfl.com":
                problems.append(f"table row {i} has a non-official or non-HTTPS source link: {url}")

        pdf_cell = cells[indexes["Game Book PDF"]]
        status_cell = cells[indexes["Status at observation"]]["text"]
        if fixture["state_at_observation"] == "final":
            if fixture["gamebook_pdf_url"] not in pdf_cell["links"]:
                problems.append(f"table row {i} must link its observed official Game Book PDF")
            if "Final at observation" not in status_cell or "PDF not parsed" not in status_cell:
                problems.append(f"table row {i} must disclose final status and unparsed PDF content")
        else:
            if pdf_cell["links"] or "Pending final game" not in pdf_cell["text"]:
                problems.append(f"table row {i} must show the scheduled fixture as pending, not missing")
            if "Scheduled at observation" not in status_cell:
                problems.append(f"table row {i} must preserve its scheduled-at-observation status")

        for header, label in player_fields:
            if cells[indexes[header]]["text"]:
                problems.append(f"table row {i} must leave unverified {label} blank")

    for row in register["rows"]:
        for url in (row["game_center_url"], row.get("gamebook_pdf_url")):
            if url and url not in page_html:
                problems.append(f"generated page omits a registered official URL: {url}")
        if row["game_id"] not in page_html:
            problems.append(f"generated page omits fixture ID {row['game_id']}")

    if "flagged.html#R-18" not in page_html:
        problems.append("generated page must link its unverified content limitation to Flag R-18")
    if re.search(r"\b(?:None|null|nan)\b", " ".join(
            cell["text"] for row in target["rows"] for cell in row["cells"]), re.I):
        problems.append("generated fixture table contains a serialized missing-value token")
    return problems


def check() -> list[str]:
    register = load_register()
    problems = validate_register(register)
    if not PAGE_PATH.is_file():
        return problems + ["generated page is missing; run referee/tools/build_site.py"]
    problems.extend(check_page(PAGE_PATH.read_text(encoding="utf-8"), register))
    return problems


def main() -> int:
    problems = check()
    if problems:
        print("FAIL: Game Book source index")
        for problem in problems:
            print(" -", problem)
        return 1
    register = load_register()
    print("PASS:", len(register["rows"]), "fixtures;",
          register["summary"]["official_gamebook_links_observed"], "PDF links observed;",
          register["summary"]["gamebook_pdfs_parsed"], "PDF contents parsed; player-value cells blank")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
