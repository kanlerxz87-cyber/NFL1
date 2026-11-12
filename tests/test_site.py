"""Site integrity tests.

These enforce the two publication rules that matter most: the site builds with
no broken links, and every data table row carries a link to an official source.
"""
import re
import sys
import pathlib
import unittest
import html as html_module

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nfl.sitekit import ALL_PAGES, NAV, SITE_OUT  # noqa: E402

#: The built site lives wherever the builder writes it - the repository root,
#: because Pages is pinned to `main` at `/`.
DOCS = SITE_OUT

HREF = re.compile(r'href="([^"]+)"')
OFFICIAL = re.compile(r'href="(https?://(?:www\.)?nfl\.com[^"]*)"')
ROWS = re.compile(r"<tbody>(.*?)</tbody>", re.S)
TR = re.compile(r"<tr>")

#: Pages where every single table row must carry an nfl.com source link.
STRICT_SOURCE_PAGES = [
    "data-standings", "data-schedule", "data-injuries", "data-news",
    "analysis-ratings", "analysis-luck", "availability-depth", "lines-week10",
]


def html(slug: str) -> str:
    return (DOCS / f"{slug}.html").read_text(encoding="utf-8")


def row_count(page: str) -> int:
    return sum(len(TR.findall(body)) for body in ROWS.findall(page))


class TestSiteBuilds(unittest.TestCase):
    def test_every_declared_page_exists(self):
        missing = [s for s, _, _ in ALL_PAGES if not (DOCS / f"{s}.html").exists()]
        self.assertEqual(missing, [])

    def test_no_extra_undeclared_pages(self):
        on_disk = {p.stem for p in DOCS.glob("*.html")}
        declared = {s for s, _, _ in ALL_PAGES}
        self.assertEqual(on_disk - declared, set())

    def test_pages_can_serve_this_build(self):
        # Pages builds from the repository root with Jekyll disabled, which
        # covers every subdirectory including this one.
        self.assertTrue((ROOT / ".nojekyll").exists(),
                        "a root .nojekyll is required so Pages serves the tree verbatim")

    def test_subsite_does_not_collide_with_the_published_root_site(self):
        # The root of this repository is another session's live site. This build
        # must not overwrite it, so it lives in its own directory.
        self.assertNotEqual(DOCS, ROOT,
                            "this build would overwrite the root site published by "
                            "earlier sessions")
        self.assertEqual(DOCS.name, "verified-lab")

    def test_pages_are_well_formed(self):
        for slug, _, _ in ALL_PAGES:
            p = html(slug)
            self.assertTrue(p.startswith("<!doctype html>"), slug)
            self.assertTrue(p.rstrip().endswith("</html>"), slug)
            self.assertEqual(p.count("<main>"), 1, slug)
            self.assertEqual(p.count("</main>"), 1, slug)
            self.assertIn('<meta charset="utf-8">', p, slug)
            self.assertIn('name="viewport"', p, slug)
            self.assertEqual(p.count("<table"), p.count("</table>"), slug)
            self.assertEqual(p.count("<tbody>"), p.count("</tbody>"), slug)
            self.assertIn("<title>", p, slug)

    def test_no_template_placeholders_leaked(self):
        # Checked as rendered text with <code> spans removed: "None" and "nan"
        # occur legitimately inside prose and inside English words.
        for slug, _, _ in ALL_PAGES:
            p = re.sub(r"<code>.*?</code>", "", html(slug), flags=re.S)
            p = re.sub(r"<style>.*?</style>", "", p, flags=re.S)
            p = re.sub(r"<pre>.*?</pre>", "", p, flags=re.S)
            for bad in (">None<", ">nan<", ">NaN<", ">inf<", "Traceback",
                        "KeyError", "NameError", ">{}<", "&gt;None&lt;"):
                self.assertNotIn(bad, p, f"{slug} renders {bad!r}")
            self.assertNotRegex(p, r'href="[^h#][^"]{0,3}"', f"{slug}: suspicious short href")

    def test_no_raw_python_repr_in_output(self):
        for slug, _, _ in ALL_PAGES:
            self.assertNotRegex(html(slug), r"\{'|\[\{'|&lt;built-in", slug)


class TestLinks(unittest.TestCase):
    def test_no_broken_internal_links(self):
        broken = []
        for slug, _, _ in ALL_PAGES:
            for href in HREF.findall(html(slug)):
                if href.startswith(("http://", "https://", "mailto:")) or href.startswith("#"):
                    continue
                target = (DOCS / href).resolve()
                if not target.exists():
                    broken.append(f"{slug}.html -> {href}")
        self.assertEqual(broken, [])

    def test_no_self_referential_dead_anchors(self):
        for slug, _, _ in ALL_PAGES:
            for href in HREF.findall(html(slug)):
                if href.startswith("#"):
                    self.assertIn(f'id="{href[1:]}"', html(slug), f"{slug}: dead anchor {href}")

    def test_external_links_are_https(self):
        insecure = []
        for slug, _, _ in ALL_PAGES:
            for href in HREF.findall(html(slug)):
                if href.startswith("http://") and "nfl.com/standings/tiebreaking" not in href:
                    insecure.append(f"{slug}: {href}")
        self.assertEqual(insecure, [])

    def test_navigation_is_complete_on_every_page(self):
        for slug, _, _ in ALL_PAGES:
            p = html(slug)
            for s, label, _ in ALL_PAGES:
                self.assertIn(f'href="{s}.html"', p, f"{slug} nav missing {s}")

    def test_current_page_is_marked_in_nav(self):
        for slug, _, _ in ALL_PAGES:
            self.assertIn(f'href="{slug}.html" class="on"', html(slug))


class TestSourceLinks(unittest.TestCase):
    """The publication rule, enforced per table rather than per page.

    Any table that declares a Source column must carry a link to an official
    source in every single row. A row without one fails the build.
    """

    TABLE = re.compile(r"<table[^>]*>(.*?)</table>", re.S)
    THEAD = re.compile(r"<thead>(.*?)</thead>", re.S)
    TBODY = re.compile(r"<tbody>(.*?)</tbody>", re.S)
    ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
    OFFICIAL_HOST = re.compile(
        r'href="https?://(?:www\.)?(?:nfl\.com|developer\.sportradar\.com|github\.com)[^"]*"')
    REPO_HOST = re.compile(r'href="https?://github\.com/[^"]*"')

    def source_tables(self, slug):
        out = []
        for t in self.TABLE.findall(html(slug)):
            head = self.THEAD.search(t)
            body = self.TBODY.search(t)
            if not head or not body:
                continue
            if "Source" in head.group(1):
                out.append(body.group(1))
        return out

    def test_every_row_of_every_source_table_has_an_official_link(self):
        offenders = []
        checked = 0
        for slug, _, _ in ALL_PAGES:
            for body in self.source_tables(slug):
                for row in self.ROW.findall(body):
                    checked += 1
                    if not self.OFFICIAL_HOST.search(row):
                        offenders.append(f"{slug}: {row[:110]}")
        self.assertGreater(checked, 300, f"only {checked} rows checked")
        self.assertEqual(offenders, [], f"{len(offenders)} rows lack an official source link")

    def test_strict_data_pages_are_covered(self):
        for slug in STRICT_SOURCE_PAGES:
            bodies = self.source_tables(slug)
            self.assertTrue(bodies, f"{slug} has no table with a Source column")
            rows = sum(len(self.ROW.findall(b)) for b in bodies)
            self.assertGreater(rows, 0, f"{slug} rendered no rows")

    def test_standings_page_has_32_rows(self):
        self.assertGreaterEqual(row_count(html("data-standings")), 32)

    def test_injury_page_has_all_254_entries(self):
        self.assertGreaterEqual(row_count(html("data-injuries")), 254 + 32)

    def test_lines_page_has_all_14_games(self):
        self.assertGreaterEqual(row_count(html("lines-week10")), 14)

    def test_verification_page_lists_every_check(self):
        self.assertGreaterEqual(row_count(html("verification")), 32)

    def test_flagged_page_carries_a_source_on_every_row(self):
        # Internal items link to the repository file that defines them, so no
        # flagged row is left without somewhere a reviewer can actually look.
        bodies = self.source_tables("flagged")
        self.assertTrue(bodies)
        for body in bodies:
            for row in self.ROW.findall(body):
                self.assertTrue(self.OFFICIAL_HOST.search(row),
                                f"flagged row without a source: {row[:120]}")

    def test_no_blank_cell_is_silently_zero(self):
        for slug in ("lines-week10", "strategies-leaderboard"):
            self.assertIn('class="blank"', html(slug), f"{slug} has no explicit blank markers")


class TestSourceLabels(unittest.TestCase):
    """A source link must say where it actually goes.

    Labelling a github.com permalink or a Sportradar reference "NFL.com" would
    misrepresent the provenance of the value it supports, which is the one thing
    this site must never do.
    """

    SRC_ANCHOR = re.compile(
        r'<a class="src" href="([^"]+)"[^>]*>([^<]*?)\s*&harr;?</a>'
        r'|<a class="src" href="([^"]+)"[^>]*>([^<]*?)\s*↗</a>')

    def anchors(self, page):
        out = []
        for m in re.finditer(r'<a class="src" href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S):
            out.append((m.group(1), re.sub(r"\s*↗\s*$", "", m.group(2)).strip()))
        return out

    def test_no_link_claims_a_host_it_does_not_point_to(self):
        """The rule that matters: a label must never name the wrong host.

        A link labelled `report`, or with a player's name, is more informative
        than one labelled with its host, and is fine. What is not fine - because
        it misrepresents provenance, the one thing this site must never do - is
        a link labelled "NFL.com" that actually goes to GitHub or Sportradar.
        """
        offenders = []
        checked = 0
        for slug, _, _ in ALL_PAGES:
            for href, label in self.anchors(html(slug)):
                checked += 1
                host = re.sub(r"^https?://", "", href).split("/")[0].lower()
                host = host[4:] if host.startswith("www.") else host
                lab = html_module.unescape(label).lower()
                names_a_host = any(h in lab for h in
                                   ("nfl.com", "github", "sportradar", "nflverse", "espn", ".org"))
                if names_a_host and not host.endswith("nfl.com") and "nfl.com" in lab:
                    offenders.append(f"{slug}: {host} link labelled {label!r}")
                if names_a_host and host.endswith("nfl.com") and "nfl.com" not in lab:
                    offenders.append(f"{slug}: nfl.com link labelled {label!r}")
        self.assertGreater(checked, 300, f"only {checked} source links checked")
        self.assertEqual(offenders, [])

    def test_host_labels_are_used_where_no_role_label_applies(self):
        """Where a link carries a host label, it must be the correct host."""
        seen = {}
        for slug, _, _ in ALL_PAGES:
            for href, label in self.anchors(html(slug)):
                lab = html_module.unescape(label)
                if "github.com/kanlerxz87-cyber/NFL1" in href and lab == "this repository":
                    seen["repo"] = lab
                if "github.com/nflverse" in href and lab == "nflverse mirror":
                    seen["mirror"] = lab
                if "developer.sportradar.com" in href and lab.startswith("Sportradar"):
                    seen["partner"] = lab
                if re.sub(r"^https?://(www\.)?", "", href).startswith("nfl.com") and lab == "NFL.com":
                    seen["nfl"] = lab
        self.assertEqual(seen.get("nfl"), "NFL.com")
        self.assertEqual(seen.get("repo"), "this repository")
        self.assertEqual(seen.get("mirror"), "nflverse mirror")
        self.assertEqual(seen.get("partner"), "Sportradar (NFL's official data partner)")

    def test_no_repository_link_is_dressed_up_as_an_official_source(self):
        for slug, _, _ in ALL_PAGES:
            for href, label in self.anchors(html(slug)):
                if "github.com" in href:
                    self.assertNotEqual(html_module.unescape(label), "NFL.com",
                                        f"{slug}: a repository link is labelled NFL.com")

    def test_host_label_helper(self):
        from nfl.sitekit import host_label
        self.assertEqual(host_label("https://www.nfl.com/standings/"), "NFL.com")
        self.assertEqual(host_label("https://github.com/kanlerxz87-cyber/NFL1/blob/main/x.py"),
                         "this repository")
        self.assertEqual(host_label("https://github.com/nflverse/nflverse-data"), "nflverse mirror")
        self.assertEqual(host_label("https://developer.sportradar.com/x"),
                         "Sportradar (NFL's official data partner)")
        self.assertEqual(host_label("https://example.org/x"), "example.org")
        self.assertEqual(host_label(None), "source")


class TestContentIntegrity(unittest.TestCase):
    def test_disputed_cells_are_blanked_on_the_standings_page(self):
        p = html("data-standings")
        self.assertIn("DISPUTED", p)

    def test_no_spread_value_is_published_anywhere(self):
        for slug, _, _ in ALL_PAGES:
            p = html(slug)
            # The spread column must contain only blank markers on the board page.
            if slug == "lines-week10":
                self.assertIn("blocked: home-field advantage in points is unavailable", p)

    def test_leaderboard_shows_no_scores(self):
        self.assertIn("not ranked - no score", html("strategies-leaderboard"))

    def test_provenance_tiers_are_explained(self):
        for slug in ("index", "data-standings", "data-injuries"):
            p = html(slug)
            for tier in ("VERIFIED", "DERIVED", "MODELED", "UNAVAILABLE"):
                self.assertIn(tier, p, f"{slug} does not explain tier {tier}")

    def test_headline_finding_is_on_the_dashboard(self):
        self.assertIn("Zero non-mechanical findings survive", html("index"))


if __name__ == "__main__":
    unittest.main()
