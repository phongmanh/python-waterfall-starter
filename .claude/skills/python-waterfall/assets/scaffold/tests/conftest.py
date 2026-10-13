"""Shared pytest configuration.

The first section is the requirement-traceability plugin used by the waterfall process:

* ``@pytest.mark.req("AC-003.2")`` links a test to the requirement IDs it verifies.
  Malformed IDs fail collection, so typos never silently drop out of the RTM.
* Tests under ``tests/integration`` and ``tests/e2e`` get the matching marker
  automatically, so ``pytest -m "not e2e"`` works without decorating every test.
* ``pytest --rtm`` prints requirement → tests → outcome after the run, and
  ``--rtm-json=PATH`` writes the same data for the P4 test report.

Put project fixtures below the plugin section.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.terminal import TerminalReporter

# --- Requirement traceability (waterfall) ------------------------------------

REQ_ID = re.compile(r"^(?:(?:FR|NFR|DEF|CR)-\d{3}|AC-\d{3}\.\d+)$")
UNTRACED = "(untraced)"


class RequirementTrace:
    """Collects requirement IDs per test and the outcome of each test."""

    def __init__(self) -> None:
        self.tests_by_req: dict[str, list[str]] = defaultdict(list)
        self.outcomes: dict[str, str] = {}

    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        errors: list[str] = []
        for item in items:
            # nodeid paths are relative to the rootdir, so the project's own folder
            # name can't trigger a marker.
            parts = Path(item.nodeid.split("::", 1)[0]).parts
            for level in ("integration", "e2e"):
                if level in parts:
                    item.add_marker(level)
            ids = [i for mark in item.iter_markers("req") for i in mark.args]
            for req_id in ids:
                if isinstance(req_id, str) and REQ_ID.match(req_id):
                    self.tests_by_req[req_id].append(item.nodeid)
                else:
                    errors.append(f"{item.nodeid}: invalid requirement ID {req_id!r}")
            if not ids:
                self.tests_by_req[UNTRACED].append(item.nodeid)
        if errors:
            raise pytest.UsageError("\n".join(errors))

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.failed:
            failed_as = "failed" if report.when == "call" else "error"
            self.outcomes.setdefault(report.nodeid, failed_as)
        elif report.when == "call" or report.skipped:
            self.outcomes.setdefault(report.nodeid, report.outcome)

    def rows(self) -> dict[str, list[dict[str, str]]]:
        return {
            req_id: [
                {"test": node, "outcome": self.outcomes.get(node, "not run")}
                for node in nodes
            ]
            for req_id, nodes in sorted(self.tests_by_req.items())
        }

    def pytest_terminal_summary(
        self, terminalreporter: TerminalReporter, config: pytest.Config
    ) -> None:
        rows = self.rows()
        if path := config.getoption("--rtm-json"):
            Path(path).write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        if not config.getoption("--rtm"):
            return
        terminalreporter.section("requirements traceability")
        for req_id, tests in rows.items():
            ok = all(t["outcome"] == "passed" for t in tests)
            verdict = "PASS" if ok and req_id != UNTRACED else "CHECK"
            terminalreporter.write_line(
                f"{req_id:<12} {verdict:<6} {len(tests)} test(s)"
            )
            for t in tests:
                terminalreporter.write_line(f"    {t['outcome']:<8} {t['test']}")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("waterfall")
    group.addoption(
        "--rtm", action="store_true", help="print requirement → tests after the run"
    )
    group.addoption(
        "--rtm-json", metavar="PATH", help="write requirement → tests as JSON"
    )


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(RequirementTrace(), "waterfall-rtm")


# --- Project fixtures --------------------------------------------------------
