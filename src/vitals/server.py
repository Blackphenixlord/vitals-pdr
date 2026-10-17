"""The browser interface.

Stdlib only - http.server, no Flask, no npm, no build step. That is a
requirement, not laziness: this has to run on a Jetson and two Raspberry Pis
that may have no working internet, and every dependency is one more thing that
can fail on the vehicle.

    python -m vitals serve      ->  http://127.0.0.1:8000

WHERE THIS RUNS
    On the Jetson, as the ONE server for the whole system. The three Raspberry
    Pis are screens only - each opens one page from here in kiosk mode:
        Pi 1 -> /login?station=astronaut     (AUI)
        Pi 2 -> /login?station=ground        (GCUI)
        Pi 3 -> /login?station=doctor        (Doctor UI)
    The Jetson's own screen can show /status. Cases live on the Jetson
    (cases.py), so a Pi can be unplugged without losing anything.
    deploy/README.md has the install steps.

ROUTES
    GET  /              PIN login (?station=<role> locks a screen to one role)
    GET  /astronaut     astronaut screen (AUI) - THE working screen in this version
    GET  /ground        PLANNED: ground crew screen - shows what it will do (planned.html)
    GET  /doctor        PLANNED: doctor screen - shows what it will do (planned.html)
    GET  /status        PLANNED: the Jetson's own status screen (planned.html)
    GET  /install/<role>  deploy/install.sh with this server's address filled in, for
                          curl -fsSL http://<jetson>:8000/install/astronaut | sudo bash
    GET  /api/health    is the KB loaded, is ollama up, what models exist
    GET  /api/examples  the prompt bank, so the UI can offer real complaints
    GET  /api/me        who is logged in (401 if nobody)
    POST /api/login     {"pin": "1234", "name": "optional", "station": "optional role"}
                        -> sets the session cookie
    POST /api/emergency skip the PIN: astronaut screen as an unnamed crewmember
    POST /api/logout
    POST /api/ask       {"complaint": "...", "model": "...",
                         "corrections": {"back_pain": false},
                         "latest": "newest message", "said": "this line",
                         "case_id": "from the last reply"} -> the full answer
                        (medical answers are saved to a case; the reply carries case_id)
                        (needs an astronaut session; corrections and latest
                        are optional). `scope` in the reply is "medical", or
                        greeting/thanks/help/off_topic with a plain `message`.

LOGIN
    Pages are just code and are served to anyone; the DATA is what is
    protected. Every API call that touches a person or asks the model checks
    the session cookie here, on the server. Hiding a button in the browser is
    not security - anyone can call the API directly.

THE SERVER OWNS NO MEDICAL LOGIC WHATSOEVER. It is a thin shell around exactly
the same pipeline the CLI uses, so the UI can never drift from what
`vitals ask` does. If they ever disagree, that is a bug in this file.
"""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from . import sensors
from .accounts import ROLES, LoginDesk, LoginRefused, load_accounts
from .cases import DATA_DIR, CaseError, CaseStore
from .engine import diagnose
from .missionlog import MissionLog
from .extract import KeywordExtractor
from .knowledge_base import KnowledgeBaseError, load_knowledge_base
from .ollama_client import DEFAULT_MODEL, OLLAMA_HOST, OllamaUnavailable, list_models
from .reason import ask, not_medical_answer
from .retrieval import retrieve
from .scope import classify

UI_DIR = Path(__file__).parent / "ui"
INSTALLER = Path(__file__).resolve().parents[2] / "deploy" / "install.sh"

RETRIEVAL_LIMIT = 6

SESSION_COOKIE = "vitals_session"

# Which screen each role opens after login.
ROLE_PAGES = {"astronaut": "/astronaut", "ground": "/ground", "doctor": "/doctor"}

# Who may ask the model.
ASK_ROLES = {"astronaut"}

PAGES = {
    "/": "login.html",
    "/index.html": "login.html",
    "/login": "login.html",
    "/astronaut": "astronaut.html",
    # Planned screens: one page that says what each will do. See planned.html.
    "/ground": "planned.html",
    "/doctor": "planned.html",
    "/status": "planned.html",
}

ROLE_WORDS = {"astronaut": "astronaut", "ground": "ground crew", "doctor": "doctor"}

# A screen that has not been heard from for this long is shown as offline.
STATION_STALE_SECONDS = 60

STARTED = time.time()


def run_pipeline(knowledge_base, complaint: str, model: str,
                 corrections: dict[str, bool] | None = None,
                 latest: str | None = None) -> dict[str, Any]:
    """The exact same sequence as `cmd_ask`. One pipeline, two front ends.

    `corrections` is the crewmember fixing a finding the extractor got wrong
    ("I said NO back pain"). It is applied after extraction, so it always wins.

    `latest` is just the newest message, when the screen sends one. The screen
    sends the whole chat as `complaint`, so a "thanks" or "what's the weather"
    typed mid-chat would otherwise ride along on an earlier symptom and re-run
    the model. If the newest message is not medical, it gets the plain reply
    and nothing else runs. ask() still checks the whole complaint as well.
    """
    started = time.time()

    latest_scope = classify(latest, knowledge_base) if latest else None
    if latest_scope is not None and not latest_scope.is_medical:
        observations: dict[str, Any] = {}
        retrieved = []
        answer = not_medical_answer(latest_scope, model)
    else:
        observations = KeywordExtractor().extract(complaint, knowledge_base)
        observations.update(sensors.as_observations(sensors.read_all()))
        observations.update(clean_corrections(knowledge_base, corrections))

        retrieved = retrieve(knowledge_base, complaint, observations, limit=RETRIEVAL_LIMIT)
        answer = ask(knowledge_base, complaint, retrieved, observations=observations, model=model)
    readable = _readable_text(knowledge_base)

    return {
        "ok": True,
        "scope": answer.scope,
        "message": answer.message,
        "elapsed": round(time.time() - started, 1),
        "model": answer.model,
        "sensor_status": answer.sensor_status,
        "escalate": answer.escalate,
        "escalation_reason": readable(answer.escalation_reason),
        "escalation": _escalation_summary(knowledge_base, answer),
        "uncertainty": readable(answer.uncertainty),
        "next_questions": answer.next_questions,
        "dropped": answer.dropped,
        "known": _known_findings(knowledge_base, observations),
        "differential": [
            {
                "id": candidate.condition_id,
                "name": candidate.name,
                "urgency": candidate.urgency,
                "confidence": candidate.confidence,
                "reasoning": readable(candidate.reasoning),
                "supporting": [readable(text) for text in candidate.supporting],
                "against": [readable(text) for text in candidate.against],
                "recommend": candidate.recommend,
                "sources": candidate.sources,
            }
            for candidate in answer.differential
        ],
        "trace": {
            "findings": dict(sorted(observations.items())),
            "retrieved": [
                {
                    "id": item.id,
                    "name": item.condition.name,
                    "score": round(item.score, 1),
                    "why": item.why,
                }
                for item in retrieved
            ],
            "crosscheck": _crosscheck(knowledge_base, observations, answer),
        },
    }



def _escalation_summary(knowledge_base, answer) -> dict[str, Any]:
    """The alarm, as data the screen can act on.

    `level` is the most serious urgency among the conditions the escalation is
    about (at least "urgent" whenever it escalates), and `conditions` lists
    those conditions with their advice and sources from the KB. The screen
    leads with these - it must never show shoulder advice under a DCS alarm
    just because the model ranked shoulder first.
    """
    if not answer.escalate:
        return {"level": "none", "conditions": []}

    conditions = []
    for condition_id in answer.escalated_ids:
        condition = knowledge_base.conditions.get(condition_id)
        if condition is None:
            continue
        conditions.append({
            "id": condition_id,
            "name": condition.name,
            "urgency": condition.urgency,
            "recommend": condition.recommend,
            "sources": condition.sources,
        })

    # Most serious first.
    order = {"emergency": 0, "urgent": 1, "monitor": 2, "routine": 3}
    conditions.sort(key=lambda c: order.get(c["urgency"], 4))

    level = "urgent"
    if conditions and conditions[0]["urgency"] == "emergency":
        level = "emergency"
    return {"level": level, "conditions": conditions}


def _readable_text(knowledge_base):
    """Swap raw condition ids the model wrote ("msk_shoulder_overuse") for names.

    Acceptance criteria 2.1: the crew never sees a KB id. The model is told to
    use ids, so it sometimes leaks them into its own sentences.
    """
    names = {condition_id: condition.name
             for condition_id, condition in knowledge_base.conditions.items()}
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b") if names else None

    def readable(text: str) -> str:
        if not text or pattern is None:
            return text
        return pattern.sub(lambda match: names[match.group(1)], text)

    return readable


def clean_corrections(knowledge_base, corrections) -> dict[str, bool]:
    """Keep only present/absent corrections to real findings. Anything else is ignored.

    The browser sends these, so they are untrusted: an unknown finding id or a
    value other than true/false never reaches the pipeline. Scale findings
    (0-10) are allowed too, because the extractor records those as plain
    present/absent when no number was given ("my back hurts" -> back_pain: True).
    """
    cleaned = {}
    for finding_id, value in (corrections or {}).items():
        definition = knowledge_base.findings.get(finding_id)
        if definition is None or definition.type not in ("bool", "scale"):
            continue
        if isinstance(value, bool):
            cleaned[finding_id] = value
    return cleaned


def _known_findings(knowledge_base, observations: dict) -> list[dict[str, str]]:
    """What the system believes it knows, in the KB's own words, for the screen.

    Same data as trace.findings, but with the human label instead of the raw
    id, so the crew screen never has to show `hematuria: True`.
    """
    known = []
    for finding_id, value in sorted(observations.items()):
        definition = knowledge_base.findings.get(finding_id)
        label = definition.label if definition else finding_id
        if isinstance(value, bool):
            shown = "yes" if value else "no"
        elif definition and definition.type == "scale":
            shown = f"{value} / 10"
        elif definition and definition.unit:
            shown = f"{value} {definition.unit}"
        else:
            shown = str(value)
        # The "Wrong?" button flips yes/no, so only plain yes/no items get one.
        correctable = isinstance(value, bool) and definition is not None \
            and definition.type in ("bool", "scale")
        known.append({"id": finding_id, "label": label, "value": shown,
                      "correctable": correctable})
    return known


def _crosscheck(knowledge_base, observations: dict, answer) -> dict[str, str]:
    """How the deterministic engine voted on the same observations."""
    result = diagnose(knowledge_base, observations)
    engine_top = result.top.id if result.top else None

    if engine_top is None:
        return {
            "state": "insufficient",
            "text": "engine had too little to go on (it only sees extracted findings)",
        }

    engine_name = knowledge_base.conditions[engine_top].name

    if answer.top is None:
        return {
            "state": "insufficient",
            "text": f"engine says {engine_name}, model returned nothing",
        }
    if engine_top == answer.top.condition_id:
        return {"state": "agree", "text": f"agrees: {engine_name}"}

    return {
        "state": "disagree",
        "text": f"engine says {engine_name}, model says {answer.top.name}",
    }


class Stations:
    """Which screens are talking to this server right now.

    Keyed by the screen's network address, so the status page can show
    "astronaut Pi at 192.168.1.21 - seen 3 s ago". Holds no names and nothing
    medical: the status page is open to anyone on the network.
    """

    def __init__(self, clock=time.time):
        self.clock = clock
        self._seen: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def saw(self, address: str, *, page: str | None = None, role: str | None = None) -> None:
        with self._lock:
            entry = self._seen.setdefault(address, {"address": address, "page": None, "role": None})
            if page:
                entry["page"] = page
            if role:
                entry["role"] = role
            entry["last"] = self.clock()

    def snapshot(self) -> list[dict[str, Any]]:
        now = self.clock()
        with self._lock:
            rows = [dict(entry) for entry in self._seen.values()]
        for row in rows:
            row["seconds_ago"] = int(now - row.pop("last"))
            row["online"] = row["seconds_ago"] <= STATION_STALE_SECONDS
        return sorted(rows, key=lambda r: r["seconds_ago"])


def local_addresses() -> list[str]:
    """This machine's LAN addresses, so the status screen can tell the Pis where to point."""
    found: set[str] = set()
    try:
        # No packet is sent; this only asks the OS which interface it would use.
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))
        found.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass
    return sorted(a for a in found if not a.startswith("127."))


class Handler(BaseHTTPRequestHandler):
    """Routing and JSON encoding. Nothing else belongs in here."""

    kb = None
    model = DEFAULT_MODEL
    desk: LoginDesk = None
    cases: CaseStore = CaseStore(None)     # memory only unless serve() gives it a folder
    stations: Stations = Stations()
    log: MissionLog = MissionLog(None)     # memory only unless serve() gives it a file

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    # --- responses ---

    def _send(self, code: int, body: bytes, content_type: str,
              headers: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, payload: dict, headers: dict | None = None) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"),
                   "application/json; charset=utf-8", headers)

    # --- request helpers ---

    def _body(self) -> dict:
        """The JSON request body. Raises ValueError if it is not JSON."""
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(body, dict):
            raise ValueError("body must be a JSON object")
        return body

    def _token(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie[SESSION_COOKIE].value if SESSION_COOKIE in cookie else None

    def _session(self):
        session = self.desk.session_for(self._token())
        if session is not None:
            self.stations.saw(self.client_address[0], role=session.role)
        return session

    def _require(self, *roles):
        """The session, if its role is allowed here. Otherwise send the refusal and return None."""
        session = self._session()
        if session is None:
            self._json(401, {"ok": False, "error": "Log in first.", "kind": "auth"})
            return None
        if session.role not in roles:
            self._json(403, {"ok": False, "kind": "auth",
                             "error": f"The {ROLE_WORDS.get(session.role, session.role)} role cannot do that."})
            return None
        return session

    def _profile(self, session) -> dict[str, Any]:
        """The account profile, with any ground crew corrections."""
        return self.cases.profile_for(session.account_id, session.profile)

    def _owner(self, session) -> str:
        """Who a case belongs to. Emergency access has no account, so it is the session."""
        return session.account_id or f"emergency:{session.token}"

    @staticmethod
    def _cookie(token: str, max_age: int | None = None) -> dict:
        """HttpOnly: page scripts cannot read it. SameSite=Strict: other sites cannot send it."""
        parts = [f"{SESSION_COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Strict"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        return {"Set-Cookie": "; ".join(parts)}

    # --- routes ---

    def do_GET(self):
        url = urlsplit(self.path)

        if url.path in PAGES:
            self.stations.saw(self.client_address[0], page=url.path)
            return self._send(200, (UI_DIR / PAGES[url.path]).read_bytes(),
                              "text/html; charset=utf-8")

        if url.path.startswith("/install/"):
            return self._installer(url.path.rsplit("/", 1)[-1])

        routes = {
            "/api/examples": lambda: self._json(200, {"prompts": self._example_prompts()}),
            "/api/health": lambda: self._json(200, self._health()),
            "/api/me": self._me,
        }
        route = routes.get(url.path)
        if route is None:
            return self._json(404, {"error": "not found"})
        return route()

    def do_POST(self):
        routes = {
            "/api/login": self._login,
            "/api/emergency": self._emergency,
            "/api/logout": self._logout,
            "/api/ask": self._ask,
        }
        route = routes.get(urlsplit(self.path).path)
        if route is None:
            return self._json(404, {"error": "not found"})
        try:
            payload = self._body()
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"ok": False, "error": "bad JSON"})
        try:
            return route(payload)
        except CaseError as exc:
            return self._json(400, {"ok": False, "error": str(exc), "kind": "case"})

    # --- route bodies: login ---

    def _login(self, payload: dict):
        pin = str(payload.get("pin", ""))
        station = str(payload.get("station") or "").strip().lower() or None
        try:
            session = self.desk.log_in(pin, client=self.client_address[0],
                                       name=str(payload.get("name", "")) or None)
        except LoginRefused as exc:
            code = 429 if exc.retry_after else 401
            self.log.record("ACCOUNTS", "login", "WARN",
                            f"refused from {self.client_address[0]}"
                            f"{' - locked out' if exc.retry_after else ''}")
            return self._json(code, {"ok": False, "error": str(exc),
                                     "retry_after": exc.retry_after})

        # A screen set up for one role (a Pi in kiosk mode) only opens that role.
        # The doctor's Pi must never open the full, unredacted ground crew view.
        if station in ROLES and session.role != station:
            self.desk.log_out(session.token)
            return self._json(403, {
                "ok": False, "kind": "station",
                "error": (f"This is the {ROLE_WORDS[station]} screen. "
                          f"Use the {ROLE_WORDS[session.role]} screen to log in."),
            })

        self.stations.saw(self.client_address[0], role=session.role)
        self.log.record("ACCOUNTS", "login", "OK",
                        f"{session.name} ({session.role}) from {self.client_address[0]}")
        return self._json(200, {"ok": True, **self._public(session),
                                "page": ROLE_PAGES.get(session.role)},
                          self._cookie(session.token))

    def _public(self, session) -> dict:
        public = session.public()
        public["profile"] = self._profile(session)
        return public

    def _emergency(self, payload: dict):
        station = str(payload.get("station") or "").strip().lower() or None
        if station and station != "astronaut":
            return self._json(403, {"ok": False, "kind": "station",
                                    "error": "Emergency access is only on the astronaut screen."})
        session = self.desk.start_emergency_session()
        self.log.record("ACCOUNTS", "emergency", "WARN",
                        f"PIN skipped - emergency astronaut session from {self.client_address[0]}")
        return self._json(200, {"ok": True, **session.public(), "page": ROLE_PAGES["astronaut"]},
                          self._cookie(session.token))

    def _logout(self, payload: dict):
        self.desk.log_out(self._token())
        return self._json(200, {"ok": True}, self._cookie("", max_age=0))

    def _me(self):
        session = self._session()
        if session is None:
            return self._json(401, {"ok": False, "error": "not logged in", "kind": "auth"})
        return self._json(200, {"ok": True, **self._public(session)})

    # --- route bodies: astronaut ---

    def _ask(self, payload: dict):
        session = self._session()
        if session is None:
            return self._json(401, {"ok": False, "error": "Log in first.", "kind": "auth"})
        if session.role not in ASK_ROLES:
            return self._json(403, {"ok": False, "kind": "auth",
                                    "error": f"The {ROLE_WORDS.get(session.role, session.role)} role cannot ask VITALS."})

        complaint = str(payload.get("complaint", "")).strip()
        if not complaint:
            return self._json(400, {"ok": False, "error": "no complaint given"})

        model = str(payload.get("model") or self.model)
        corrections = payload.get("corrections")
        if not isinstance(corrections, dict):
            corrections = {}
        latest = payload.get("latest")
        latest = str(latest).strip() if latest else None
        try:
            reply = run_pipeline(self.kb, complaint, model, corrections, latest)
        except OllamaUnavailable as exc:
            self.log.record("REASON", f"model:{model}", "FAIL",
                            str(exc).splitlines()[0] if str(exc) else "ollama unavailable")
            return self._json(503, {"ok": False, "error": str(exc), "kind": "ollama"})
        except KnowledgeBaseError as exc:
            self.log.record("KB", "kb/", "FAIL", str(exc))
            return self._json(500, {"ok": False, "error": str(exc), "kind": "kb"})

        # What the system did - never what the crewmember said (see missionlog.py).
        level = (reply.get("escalation") or {}).get("level", "none")
        self.log.record(
            "REASON", f"model:{reply.get('model', model)}", "OK",
            f"scope={reply.get('scope')} escalate={reply.get('escalate')} level={level} "
            f"conditions={len(reply.get('differential') or [])} "
            f"dropped={len(reply.get('dropped') or [])} {reply.get('elapsed')}s")

        # Only medical answers become part of a case. "hi" is not a case.
        if reply.get("scope") == "medical":
            said = str(payload.get("said") or latest or complaint.splitlines()[-1]).strip()
            case = self.cases.record_turn(
                payload.get("case_id") or None,
                crew={"account_id": session.account_id, "name": session.name,
                      "emergency": session.emergency, "profile": self._profile(session)},
                owner=self._owner(session),
                text=said, complaint=complaint, answer=reply,
            )
            reply["case_id"] = case["id"]
            self.log.record("CASES", f"case:{case['id']}", "OK",
                            f"astronaut turn {len(case['turns'])} saved, status={case['status']}")
        return self._json(200, reply)

    # --- route bodies: installer for the Pis ---

    def _installer(self, role: str):
        """deploy/install.sh with this server's own address already filled in.

        So setting up a Pi is one line:
            curl -fsSL http://<jetson>:8000/install/astronaut | sudo bash
        The address is the one the Pi itself used to reach us (the Host header),
        so it is right by construction - no typing an IP twice.
        """
        if role not in ROLES:
            return self._send(404, b"echo 'Unknown screen. Use /install/astronaut, /install/ground or /install/doctor.'; exit 1\n",
                              "text/plain; charset=utf-8")
        if not INSTALLER.exists():
            return self._send(404, b"echo 'This server has no deploy/install.sh. Copy it from the repo.'; exit 1\n",
                              "text/plain; charset=utf-8")
        host = re.sub(r"[^A-Za-z0-9.:\[\]-]", "", self.headers.get("Host", ""))
        host = host or f"{local_addresses()[0] if local_addresses() else '127.0.0.1'}:{self.server.server_address[1]}"
        script = INSTALLER.read_text(encoding="utf-8")
        shebang, _, rest = script.partition("\n")
        preset = (f"# Handed out by the VITALS server at {host} for the {role} screen.\n"
                  f"VITALS_ROLE={role}\nVITALS_SERVER=http://{host}\n"
                  "export VITALS_ROLE VITALS_SERVER\n")
        body = (shebang + "\n" + preset + rest).replace("\r\n", "\n")
        return self._send(200, body.encode("utf-8"), "text/x-shellscript; charset=utf-8")

    # --- route bodies: open data ---

    @staticmethod
    def _example_prompts() -> list[dict]:
        try:
            from .bench import load_prompts
            prompts = load_prompts()
        except Exception:
            return []
        return [
            {"id": p["id"], "category": p.get("category", ""), "text": p["text"]}
            for p in prompts
        ]

    def _health(self) -> dict:
        try:
            models = list_models(OLLAMA_HOST)
            ollama = {
                "up": True,
                "models": models,
                "has_default": any(
                    name.split(":")[0] == self.model.split(":")[0] for name in models
                ),
            }
        except OllamaUnavailable as exc:
            ollama = {"up": False, "models": [], "error": str(exc)}

        return {
            "kb": {
                "conditions": len(self.kb.conditions),
                "findings": len(self.kb.findings),
            },
            "ollama": ollama,
            "model": self.model,
            "sensors": sensors.status(),
        }


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    kb_path=None,
    model: str = DEFAULT_MODEL,
    open_browser: bool = False,
    data_dir=None,
) -> None:
    Handler.kb = load_knowledge_base(kb_path)
    Handler.model = model
    Handler.desk = LoginDesk(load_accounts())
    Handler.cases = CaseStore(data_dir or DATA_DIR)
    Handler.stations = Stations()
    Handler.log = MissionLog(Path(Handler.cases.folder or DATA_DIR) / "logs" / "server.jsonl")
    Handler.log.record("SERVER", f"{host}:{port}", "OK", f"started, model {model}")
    Handler.log.record("KB", "kb/", "OK", f"{len(Handler.kb.conditions)} conditions loaded")
    Handler.log.record("SENSORS", "sensors.py",
                       "NOT_CONNECTED" if not sensors.REGISTERED else "OK", sensors.status())

    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}"

    print("\n  VITALS interface running")
    print(f"  {url}")
    if host in ("0.0.0.0", "::"):
        for address in local_addresses():
            print(f"  on the network: http://{address}:{port}   (point the Pis here)")
    print(f"  model: {model}   |   sensors: {sensors.status()}")
    print(f"  cases saved in: {Handler.cases.folder}")
    print(f"  mission log:    {Handler.log.path}   (python -m vitals log)")
    from .accounts import ACCOUNTS_FILE, accounts_path
    if accounts_path() != ACCOUNTS_FILE:
        print("  accounts: DEMO accounts (accounts.example.json) - add real ones with")
        print("            python -m vitals add-account")
    print("  Ctrl-C to stop\n")

    if open_browser:
        import webbrowser
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
    finally:
        httpd.server_close()
