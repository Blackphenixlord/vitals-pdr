"""The PDR basic missions must all pass, offline, on any machine."""

from vitals.missions import run_missions
from vitals.missionlog import read_log


def test_basic_missions_all_pass_and_are_logged(tmp_path):
    path = tmp_path / "missions.jsonl"
    report = run_missions(log_path=path)

    for mission in ("B1", "B2", "B3", "B4", "B5", "B6"):
        assert report.mission_status(mission) == "PASS", mission
    assert not report.failed

    entries = read_log(path)
    assert len(entries) == len(report.log.entries)
    assert {e.subsystem for e in entries} >= {"KB", "SENSORS", "SCOPE", "ENGINE",
                                              "EXTRACT", "CASES", "MISSION"}


def test_sensors_are_logged_as_not_connected_never_as_a_reading(tmp_path):
    report = run_missions(log_path=None)
    sensor_lines = [e for e in report.log.entries if e.subsystem == "SENSORS"]
    assert any(e.status == "NOT_CONNECTED" for e in sensor_lines)


def test_advanced_missions_skip_cleanly_without_ollama(monkeypatch):
    import vitals.ollama_client as client

    def unreachable(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(client, "list_models", unreachable)
    report = run_missions(advanced=True)
    assert report.mission_status("A1") == "SKIP"
    assert not report.failed


def test_a_failing_case_fails_its_mission(tmp_path):
    bad = tmp_path / "cases"
    bad.mkdir()
    (bad / "wrong.yaml").write_text(
        "title: wrong on purpose\n"
        "expect_top: sans\n"
        "observations:\n  flank_pain: 8\n  hematuria: true\n  pain_colicky: true\n",
        encoding="utf-8")
    report = run_missions(cases_dir=bad)
    assert report.mission_status("B4") == "FAIL"
    assert report.failed


def test_the_log_never_contains_what_the_crewmember_said():
    report = run_missions()
    text = " ".join(e.detail for e in report.log.entries)
    assert "side pain in waves" not in text
