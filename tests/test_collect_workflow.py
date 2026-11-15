"""Regression checks for the scheduled data-refresh workflow's page build path."""
from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/collect-data.yml"


class CollectWorkflowTests(unittest.TestCase):
    def test_refresh_uses_the_canonical_site_builder_once(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(text.count("python tools/build_site_all.py\n"), 1)
        self.assertNotIn("python pipeline/gen_site.py", text)
        self.assertNotIn("python tools/build_dashboard.py", text)

    def test_integrity_gates_run_after_the_canonical_site_build(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        build = text.index("python tools/build_site_all.py")
        for gate in (
            "python tools/check_freshness.py",
            "python tools/check_generators.py",
            "python tools/check_committed_site.py",
        ):
            with self.subTest(gate=gate):
                self.assertGreater(text.index(gate), build)

    def test_refresh_stages_all_tracked_build_outputs(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("git add -u", text)
        self.assertIn("git add data/model pipeline data/evidence data/audit", text)


if __name__ == "__main__":
    unittest.main()
