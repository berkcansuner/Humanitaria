"""Guards for the nightly ingest workflow, which holds the cron token as a secret.

The token must never reach code from a pull request, so the workflow may only run
on its schedule or by hand, with no repository permissions.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "nightly-ingest.yml"


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    # PyYAML (YAML 1.1) reads the bare key `on` as boolean True.
    return workflow.get("on", workflow.get(True))


def test_only_schedule_and_manual_triggers(workflow):
    assert set(_triggers(workflow)) == {"schedule", "workflow_dispatch"}


def test_runs_twice_daily_off_the_top_of_the_hour(workflow):
    # GitHub may drop scheduled runs at :00 under load (the first 03:00 run never started).
    crons = [s["cron"] for s in _triggers(workflow)["schedule"]]
    assert crons == ["17 3 * * *", "47 14 * * *"]
    assert all(c.split()[0] != "0" for c in crons)


def test_no_repository_permissions(workflow):
    assert workflow["permissions"] == {}


def test_token_comes_from_secret_and_is_never_echoed():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "INGEST_TRIGGER_TOKEN: ${{ secrets.INGEST_TRIGGER_TOKEN }}" in text
    assert "set -x" not in text
    for line in text.splitlines():
        if "echo" in line:
            assert "$INGEST_TRIGGER_TOKEN" not in line
