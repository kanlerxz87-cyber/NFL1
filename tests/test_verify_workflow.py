"""Regression test for the verify workflow's NumPy/Pandas install ordering.

Run with: python3 -m unittest tests.test_verify_workflow -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verify.yml"
STEP_RE = re.compile(
    r"(?ms)^      - name: (?P<name>[^\n]+)\n"
    r"(?P<body>.*?)(?=^      - name: |\Z)"
)


class TestVerifyWorkflowDependencyOrder(unittest.TestCase):
    def test_numpy_and_pandas_install_precedes_dependent_steps(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        steps = list(STEP_RE.finditer(text))
        by_name: dict[str, list[re.Match[str]]] = {}
        for step in steps:
            by_name.setdefault(step.group("name").strip(), []).append(step)

        install_steps = by_name.get("Install analysis and site-build dependencies", [])
        self.assertEqual(len(install_steps), 1, "expected one early dependency-install step")
        install = install_steps[0]
        install_command = re.search(r"(?m)^\s*run:\s*(.+)$", install.group("body"))
        self.assertIsNotNone(install_command, "dependency step must run a pip install command")
        command = install_command.group(1) if install_command else ""
        self.assertRegex(command, r"\bpip\s+install\b")
        self.assertRegex(command, r"\bnumpy\b")
        self.assertRegex(command, r"\bpandas\b")

        for name in (
            "Recompute derived values",
            "Rebuild every published page from the JSON data layer",
        ):
            dependent_steps = by_name.get(name, [])
            self.assertEqual(len(dependent_steps), 1, f"expected one {name!r} step")
            self.assertLess(
                install.start(),
                dependent_steps[0].start(),
                f"NumPy and Pandas must be installed before {name}",
            )


if __name__ == "__main__":
    unittest.main()
