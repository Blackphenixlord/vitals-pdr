"""Cases, roles and stations on the Jetson.

This version ships the astronaut screen only; the ground crew and doctor
screens are planned. These tests run the real HTTP server with the model faked
out and prove what exists today: every medical answer is saved as a case (ready
for the planned screens), off-topic chat is not, one crewmember can't write to
another's case, only the astronaut role can ask, and each Pi station only opens
its own role. The case store's review rules (used by the planned screens) are
tested directly.
"""

import json
import subprocess
import shutil
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from vitals import load_knowledge_base
from vitals.accounts import Account, LoginDesk, hash_pin
from vitals.cases import CaseError, CaseStore
from vitals.server import Handler, Stations

PINS = {"astronaut": "4321", "ground": "5432", "doctor": "6543", "astronaut2": "7654"}

RENAL = {
    "differential": [{"condition_id": "renal_stone", "confidence": "high",
                      "reasoning": "colicky flank pain with blood in the urine",
                      "supporting": ["blood in urine"], "against": []}],
    "escalate": True, "escalation_reason": "urgent condition",
    "next_findings": ["fever"], "uncertainty": "duration",
}


@pytest.fixture()
def server(tmp_path, monkeypatch):
    payload = json.dumps({"response": json.dumps(RENAL)}).encode()

    class _Resp:
        def read(self): return payload
        def __enter__(self): return self
        def __exit__(self, *a): return False

    import vitals.ollama_client as oc
    real_urlopen = oc.urllib.request.urlopen

    def fake_urlopen(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if ":11434" in url or "/api/generate" in url:
            return _Resp()
        return real_urlopen(req, *a, **k)

    monkeypatch.setattr("vitals.ollama_client.urllib.request.urlopen", fake_urlopen)

    Handler.kb = load_knowledge_base()
    Handler.desk = LoginDesk([
        Account("astro-1", "Alex Rivera", "astronaut", hash_pin(PINS["astronaut"]),
                {"Height": "178 cm", "Allergies": "Penicillin"}),
        Account("astro-2", "Sam Lee", "astronaut", hash_pin(PINS["astronaut2"])),
        Account("ground-1", "Gina Ground", "ground", hash_pin(PINS["ground"])),
        Account("doc-1", "Dr. Diaz", "doctor", hash_pin(PINS["doctor"])),
    ])
    Handler.cases = CaseStore(tmp_path)
    Handler.stations = Stations()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def call(server, path, body=None, cookie=None):
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    data = json.dumps(body).encode() if body is not None else None
    req = Request(server + path, data=data, headers=headers, method="POST" if body is not None else "GET")
    try:
        with urlopen(req) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, json.loads(e.read())


def login(server, who, station=None):
    body = {"pin": PINS[who]}
    if station:
        body["station"] = station
    req = Request(server + "/api/login", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req) as r:
        return r.headers["Set-Cookie"].split(";")[0]


def ask(server, cookie, text, case_id=None):
    status, reply = call(server, "/api/ask", {"complaint": text, "case_id": case_id, "said": text}, cookie)
    assert status == 200, reply
    return reply


def test_cases_survive_a_server_restart(tmp_path):
    store = CaseStore(tmp_path)
    case = store.record_turn(None, crew={"account_id": "a", "name": "A", "profile": {}},
                             owner="a", text="my head hurts", complaint="my head hurts",
                             answer={"differential": []})
    again = CaseStore(tmp_path)
    assert again.get(case["id"])["title"] == "my head hurts"


def test_a_damaged_case_file_does_not_stop_the_server(tmp_path):
    (tmp_path / "cases").mkdir()
    (tmp_path / "cases" / "broken.json").write_text("{not json", encoding="utf-8")
    assert CaseStore(tmp_path).summaries() == []


# --- each role only sees its own data -----------------------------------------

def test_off_topic_messages_do_not_create_cases(server):
    astro = login(server, "astronaut")
    _, reply = call(server, "/api/ask", {"complaint": "hi", "latest": "hi"}, astro)
    assert reply["scope"] == "greeting" and "case_id" not in reply
    assert Handler.cases.summaries() == []


def test_a_medical_answer_is_saved_as_a_case_for_the_planned_screens(server):
    astro = login(server, "astronaut")
    reply = ask(server, astro, "pain in my right side in waves, blood in my urine")
    case_id = reply["case_id"]
    ask(server, astro, "no fever", case_id)          # same chat -> same case
    case = Handler.cases.get(case_id)
    assert len(case["turns"]) == 2
    assert case["turns"][0]["answer"]["differential"][0]["id"] == "renal_stone"


def test_ground_and_doctor_cannot_ask(server):
    for who in ("ground", "doctor"):
        status, _ = call(server, "/api/ask", {"complaint": "blood in my urine"}, login(server, who))
        assert status == 403


def test_one_astronaut_cannot_add_to_anothers_case(server):
    first = ask(server, login(server, "astronaut"), "blood in my urine")["case_id"]
    other = ask(server, login(server, "astronaut2"), "blood in my urine", case_id=first)["case_id"]
    assert other != first


# --- case-store rules the planned screens will use --------------------------


def test_disagreeing_needs_a_reason(tmp_path):
    store = CaseStore(tmp_path)
    case = store.record_turn(None, crew={"name": "A", "profile": {}}, owner="a",
                             text="x", complaint="x", answer={"differential": []})
    store.send_to_doctor(case["id"], [], "", "G")
    with pytest.raises(CaseError):
        store.review(case["id"], "disagree", "  ", "D")


# --- stations (the Pis) ---------------------------------------------------------

def test_a_station_only_accepts_its_own_role(server):
    body = {"pin": PINS["ground"], "station": "doctor"}
    status, reply = call(server, "/api/login", body)
    assert status == 403 and reply["kind"] == "station"
    assert login(server, "doctor", station="doctor")


def test_emergency_access_only_on_the_astronaut_station(server):
    assert call(server, "/api/emergency", {"station": "doctor"})[0] == 403
    assert call(server, "/api/emergency", {"station": "astronaut"})[0] == 200


@pytest.mark.parametrize("page", ["/ground", "/doctor", "/status", "/login?station=doctor"])
def test_every_screen_is_served_and_says_not_a_diagnosis(server, page):
    html = urlopen(server + page).read().decode().lower()
    assert "a doctor has the final say" in html


# --- the Pi installer the Jetson hands out ---------------------------------------

def test_jetson_hands_out_the_installer_with_its_own_address(server):
    script = urlopen(server + "/install/doctor").read().decode()
    host = server.split("://")[1]
    assert script.startswith("#!/usr/bin/env bash\n")
    assert "VITALS_ROLE=doctor\n" in script
    assert f"VITALS_SERVER=http://{host}\n" in script
    assert "\r" not in script


def _working_bash() -> bool:
    """Windows often has a `bash` that is only a WSL stub. Only trust one that runs."""
    if shutil.which("bash") is None:
        return False
    try:
        return subprocess.run(["bash", "-c", "exit 0"], capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


@pytest.mark.skipif(not _working_bash(), reason="no working bash on this machine")
def test_installer_is_valid_bash(server):
    script = urlopen(server + "/install/astronaut").read()
    result = subprocess.run(["bash", "-n"], input=script, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_unknown_installer_role_is_refused(server):
    with pytest.raises(HTTPError) as e:
        urlopen(server + "/install/jetson")
    assert e.value.code == 404
