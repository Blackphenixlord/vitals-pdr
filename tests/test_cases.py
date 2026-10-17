"""The Jetson as the hub: astronaut -> ground crew -> doctor -> ground -> astronaut.

These run the real HTTP server with the model faked out, so they prove the
three screens can actually hand a case along - and that each role is held to
its own data by the SERVER, not by which buttons a page happens to show.
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


# --- the whole loop ----------------------------------------------------------

def test_full_loop_astronaut_ground_doctor_ground_astronaut(server):
    astro = login(server, "astronaut")
    reply = ask(server, astro, "pain in my right side in waves, blood in my urine")
    case_id = reply["case_id"]
    ask(server, astro, "no fever", case_id)          # same chat -> same case

    ground = login(server, "ground")
    _, listing = call(server, "/api/ground/cases", cookie=ground)
    assert [c["id"] for c in listing["cases"]] == [case_id]
    assert listing["cases"][0]["level"] in ("urgent", "emergency")
    assert listing["cases"][0]["status"] == "open"

    _, full = call(server, f"/api/ground/case?id={case_id}", cookie=ground)
    case = full["case"]
    assert len(case["turns"]) == 2
    assert case["turns"][0]["answer"]["differential"][0]["id"] == "renal_stone"
    assert "owner" not in case
    assert "profile:Allergies" in case["redactable"]

    status, sent = call(server, "/api/ground/send",
                        {"id": case_id, "hidden": ["name", "profile:Allergies"],
                         "note": "Please advise"}, ground)
    assert status == 200 and sent["case"]["status"] == "with_doctor"

    doctor = login(server, "doctor")
    _, queue = call(server, "/api/doctor/cases", cookie=doctor)
    assert queue["cases"][0]["id"] == case_id
    _, packet = call(server, f"/api/doctor/case?id={case_id}", cookie=doctor)
    content = packet["case"]["content"]
    assert content["crew_name"] is None
    assert "Allergies" not in content["profile"]
    assert content["profile"]["Height"] == "178 cm"
    assert "Alex Rivera" not in json.dumps(packet)
    assert "Penicillin" not in json.dumps(packet)
    assert content["note_from_ground"] == "Please advise"

    # the astronaut sees nothing yet
    _, notes = call(server, "/api/my/notes", cookie=astro)
    assert notes["notes"] == []

    status, _ = call(server, "/api/doctor/review",
                     {"id": case_id, "verdict": "disagree", "note": "Ultrasound first."}, doctor)
    assert status == 200
    _, notes = call(server, "/api/my/notes", cookie=astro)
    assert notes["notes"] == []                      # not until ground releases it

    status, released = call(server, "/api/ground/release",
                            {"id": case_id, "note": "Doctor says: ultrasound first."}, ground)
    assert status == 200 and released["case"]["status"] == "released"

    _, notes = call(server, "/api/my/notes", cookie=astro)
    assert notes["notes"][0]["message"] == "Doctor says: ultrasound first."
    assert notes["notes"][0]["verdict"] == "disagree"


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
    ground = login(server, "ground")
    _, listing = call(server, "/api/ground/cases", cookie=ground)
    assert listing["cases"] == []


def test_a_doctor_cannot_read_the_full_case(server):
    astro = login(server, "astronaut")
    case_id = ask(server, astro, "blood in my urine")["case_id"]
    doctor = login(server, "doctor")
    status, _ = call(server, f"/api/ground/case?id={case_id}", cookie=doctor)
    assert status == 403
    status, body = call(server, f"/api/doctor/case?id={case_id}", cookie=doctor)
    assert status == 404                 # not sent yet - the doctor gets nothing


def test_an_astronaut_cannot_use_ground_or_doctor_routes(server):
    astro = login(server, "astronaut")
    for path in ("/api/ground/cases", "/api/doctor/cases"):
        assert call(server, path, cookie=astro)[0] == 403
    assert call(server, "/api/doctor/review", {"id": "x", "verdict": "agree"}, astro)[0] == 403


def test_ground_and_doctor_cannot_ask(server):
    for who in ("ground", "doctor"):
        status, _ = call(server, "/api/ask", {"complaint": "blood in my urine"}, login(server, who))
        assert status == 403


def test_one_astronaut_cannot_add_to_anothers_case(server):
    first = ask(server, login(server, "astronaut"), "blood in my urine")["case_id"]
    other = ask(server, login(server, "astronaut2"), "blood in my urine", case_id=first)["case_id"]
    assert other != first


def test_notes_only_go_to_the_crewmember_who_asked(server):
    astro, other = login(server, "astronaut"), login(server, "astronaut2")
    ground, doctor = login(server, "ground"), login(server, "doctor")
    case_id = ask(server, astro, "blood in my urine")["case_id"]
    call(server, "/api/ground/send", {"id": case_id, "hidden": []}, ground)
    call(server, "/api/doctor/review", {"id": case_id, "verdict": "agree", "note": ""}, doctor)
    call(server, "/api/ground/release", {"id": case_id, "note": "Doctor agrees."}, ground)
    assert len(call(server, "/api/my/notes", cookie=astro)[1]["notes"]) == 1
    assert call(server, "/api/my/notes", cookie=other)[1]["notes"] == []


def test_ground_profile_edit_reaches_the_astronauts_profile(server):
    astro = login(server, "astronaut")
    case_id = ask(server, astro, "blood in my urine")["case_id"]
    ground = login(server, "ground")
    status, _ = call(server, "/api/ground/profile",
                     {"id": case_id, "profile": {"Height": "179 cm", "Allergies": "None"}}, ground)
    assert status == 200
    _, me = call(server, "/api/me", cookie=astro)
    assert me["profile"] == {"Height": "179 cm", "Allergies": "None"}


# --- rules of the loop ----------------------------------------------------------

def test_release_before_the_doctor_replies_is_refused(server):
    case_id = ask(server, login(server, "astronaut"), "blood in my urine")["case_id"]
    ground = login(server, "ground")
    call(server, "/api/ground/send", {"id": case_id, "hidden": []}, ground)
    status, body = call(server, "/api/ground/release", {"id": case_id, "note": "x"}, ground)
    assert status == 400 and body["kind"] == "case"


def test_disagreeing_needs_a_reason(tmp_path):
    store = CaseStore(tmp_path)
    case = store.record_turn(None, crew={"name": "A", "profile": {}}, owner="a",
                             text="x", complaint="x", answer={"differential": []})
    store.send_to_doctor(case["id"], [], "", "G")
    with pytest.raises(CaseError):
        store.review(case["id"], "disagree", "  ", "D")


def test_a_new_message_after_sending_is_flagged_for_ground(server):
    astro = login(server, "astronaut")
    case_id = ask(server, astro, "blood in my urine")["case_id"]
    ground = login(server, "ground")
    call(server, "/api/ground/send", {"id": case_id, "hidden": []}, ground)
    ask(server, astro, "now I have a fever 38.9", case_id)
    _, listing = call(server, "/api/ground/cases", cookie=ground)
    assert listing["cases"][0]["new_since_sent"] is True


# --- stations (the Pis) ---------------------------------------------------------

def test_a_station_only_accepts_its_own_role(server):
    body = {"pin": PINS["ground"], "station": "doctor"}
    status, reply = call(server, "/api/login", body)
    assert status == 403 and reply["kind"] == "station"
    assert login(server, "doctor", station="doctor")


def test_emergency_access_only_on_the_astronaut_station(server):
    assert call(server, "/api/emergency", {"station": "doctor"})[0] == 403
    assert call(server, "/api/emergency", {"station": "astronaut"})[0] == 200


def test_status_page_has_no_names_or_medical_data(server):
    astro = login(server, "astronaut")
    ask(server, astro, "blood in my urine")
    status, s = call(server, "/api/status")
    assert status == 200
    assert s["cases"]["total"] == 1
    assert any(x["role"] == "astronaut" for x in s["stations"])
    text = json.dumps(s)
    assert "Alex Rivera" not in text and "urine" not in text


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
