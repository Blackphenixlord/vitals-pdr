"""The mission log is the PDR evidence format: subsystem, element, status, timestamp."""

import json
import re

import pytest

from vitals.missionlog import MissionLog, format_table, read_log, summary

REQUIRED = {"timestamp", "subsystem", "element", "status"}


def test_every_line_has_the_four_required_fields(tmp_path):
    path = tmp_path / "log.jsonl"
    log = MissionLog(path, clock=lambda: 1_792_000_000)
    log.record("ENGINE", "case:demo_renal_colic", "PASS", "top = renal_stone")
    log.record("SENSORS", "sensors.py", "NOT_CONNECTED", "no sensors connected")

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        entry = json.loads(line)
        assert REQUIRED <= set(entry)
        assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", entry["timestamp"])


def test_unknown_subsystem_or_status_is_refused():
    log = MissionLog(None)
    with pytest.raises(ValueError):
        log.record("WARP_DRIVE", "x", "OK")
    with pytest.raises(ValueError):
        log.record("ENGINE", "x", "GREAT")


def test_log_is_appended_not_overwritten(tmp_path):
    path = tmp_path / "log.jsonl"
    MissionLog(path).record("SERVER", "a", "OK")
    MissionLog(path).record("SERVER", "b", "OK")
    assert [e.element for e in read_log(path)] == ["a", "b"]


def test_a_damaged_line_does_not_lose_the_rest(tmp_path):
    path = tmp_path / "log.jsonl"
    MissionLog(path).record("KB", "kb/", "OK")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    MissionLog(path).record("KB", "kb/", "OK")
    assert len(read_log(path)) == 2


def test_table_shows_the_required_columns():
    log = MissionLog(None)
    log.record("CASES", "case:1", "OK", "saved")
    table = format_table(log.entries)
    for column in ("TIMESTAMP", "SUBSYSTEM", "ELEMENT", "STATUS"):
        assert column in table
    assert summary(log.entries) == {"OK": 1}
