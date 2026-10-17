"""Cases: what one crewmember asked, what VITALS said, and who reviewed it.

THE FLOW (the three-screen plan from the Sep 2026 whiteboard)

    astronaut (AUI)      asks VITALS. Every medical answer is saved to a case.
          |
          v
    ground crew (GCUI)   sees EVERYTHING VITALS said, can correct the
                         astronaut's profile, chooses what the doctor may see,
                         and sends a redacted packet.
          |
          v
    doctor               sees ONLY the packet. Agrees, disagrees, or gives
                         their own read.
          |
          v
    ground crew          checks the doctor's reply and releases it.
          |
          v
    astronaut            sees it in the Doctor notes tab.

WHY THE SERVER HOLDS THIS
    The Jetson is the one machine every screen talks to. The Raspberry Pis are
    only screens - if one reboots, nothing is lost, because nothing lived on
    it. Cases are plain JSON files in the data folder, one per case, so a
    person can open one in a text editor and see exactly what was recorded.

REDACTION IS DONE HERE, NOT IN THE BROWSER
    The doctor's screen is sent the packet and nothing else. Hiding a field in
    the page would still ship it to the doctor's Pi; building the packet on the
    server means a hidden field never leaves the Jetson.

This module knows nothing about medicine. It stores what the pipeline returned.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("VITALS_DATA_DIR", REPO_ROOT / "data"))

# Where a case is in the review loop.
OPEN = "open"                    # astronaut is talking to VITALS; nobody has sent it on
WITH_DOCTOR = "with_doctor"      # ground crew sent the packet; waiting on the doctor
DOCTOR_REPLIED = "doctor_replied"  # doctor answered; ground crew has not released it yet
RELEASED = "released"            # ground crew released the doctor's feedback to the astronaut
STATUSES = (OPEN, WITH_DOCTOR, DOCTOR_REPLIED, RELEASED)

VERDICTS = {
    "agree": "Agrees with VITALS",
    "disagree": "Disagrees with VITALS",
    "own": "Gives their own read",
}

# What the ground crew can withhold from the doctor. Profile fields are added
# per case as "profile:<field>".
REDACTABLE = {
    "name": "Crewmember's name",
    "transcript": "What the crewmember typed",
    "vitals_answer": "What VITALS answered",
    "understood": "What VITALS understood (findings)",
}
# Withheld unless the ground crew chooses to show it. A name is not needed for a
# medical opinion, and minimum-necessary is the safe default.
DEFAULT_HIDDEN = ("name",)


class CaseError(Exception):
    """A request the case store refuses, with a message fit for the screen."""


class CaseStore:
    """All cases, in memory, mirrored to one JSON file each.

    `folder=None` keeps everything in memory only (tests, or a laptop demo
    where nothing should be written). The server is threaded, so every change
    happens under one lock.
    """

    def __init__(self, folder: Optional[Path] = None, clock=time.time):
        self.folder = Path(folder) if folder else None
        self.clock = clock
        self._cases: dict[str, dict[str, Any]] = {}
        self._profiles: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()
        if self.folder:
            (self.folder / "cases").mkdir(parents=True, exist_ok=True)
            self._load()

    # --- disk ----------------------------------------------------------------

    def _load(self) -> None:
        for path in sorted((self.folder / "cases").glob("*.json")):
            try:
                case = json.loads(path.read_text(encoding="utf-8"))
                self._cases[case["id"]] = case
            except (OSError, ValueError, KeyError):
                # A damaged file must not stop the server from starting. Keep it
                # on disk for a human to look at, and carry on without it.
                continue
        profiles = self.folder / "profiles.json"
        if profiles.exists():
            try:
                self._profiles = json.loads(profiles.read_text(encoding="utf-8"))
            except ValueError:
                self._profiles = {}

    def _write(self, path: Path, data: Any) -> None:
        """Write via a temporary file, so a power cut never leaves half a case."""
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, path)

    def _save(self, case: dict[str, Any]) -> None:
        if self.folder:
            self._write(self.folder / "cases" / f"{case['id']}.json", case)

    def _save_profiles(self) -> None:
        if self.folder:
            self._write(self.folder / "profiles.json", self._profiles)

    # --- profiles ------------------------------------------------------------

    def profile_for(self, account_id: Optional[str], default: dict[str, Any]) -> dict[str, Any]:
        """The account's profile, with any ground crew corrections applied."""
        if account_id and account_id in self._profiles:
            return dict(self._profiles[account_id])
        return dict(default or {})

    # --- astronaut -----------------------------------------------------------

    def record_turn(self, case_id: Optional[str], *, crew: dict[str, Any],
                    owner: str, text: str, complaint: str,
                    answer: dict[str, Any]) -> dict[str, Any]:
        """Save one medical question and VITALS' answer. Starts a case if needed.

        `owner` ties the case to whoever asked: the account id, or for emergency
        access the session token (there is no account). Only the owner can add
        to a case - a case id guessed from another screen is refused.
        """
        now = self.clock()
        with self._lock:
            case = self._cases.get(case_id) if case_id else None
            if case is not None and case["owner"] != owner:
                case = None          # not theirs: start a fresh one, never append
            if case is None:
                case = {
                    "id": self._new_id(now),
                    "created": now,
                    "updated": now,
                    "status": OPEN,
                    "owner": owner,
                    "crew": deepcopy(crew),
                    "title": _title(text),
                    "complaint": "",
                    "turns": [],
                    "packet": None,
                    "review": None,
                    "release": None,
                    "new_since_sent": False,
                    "log": [],
                }
                self._cases[case["id"]] = case
                self._audit(case, now, crew.get("name", "?"), "astronaut", "opened the case")

            case["turns"].append({"at": now, "text": text, "answer": deepcopy(answer)})
            case["complaint"] = complaint
            case["updated"] = now
            if case["status"] != OPEN:
                case["new_since_sent"] = True
            self._save(case)
            return deepcopy(case)

    def notes_for(self, owner: str) -> list[dict[str, Any]]:
        """Doctor feedback the ground crew has released to this crewmember."""
        with self._lock:
            mine = [c for c in self._cases.values()
                    if c["owner"] == owner and c["status"] == RELEASED and c["release"]]
            mine.sort(key=lambda c: -c["release"]["at"])
            return [{
                "case_id": c["id"],
                "title": c["title"],
                "asked_at": c["created"],
                "released_at": c["release"]["at"],
                "verdict": c["review"]["verdict"] if c["review"] else None,
                "verdict_words": VERDICTS.get(c["review"]["verdict"], "") if c["review"] else "",
                "message": c["release"]["note"],
            } for c in mine]

    # --- ground crew ---------------------------------------------------------

    def summaries(self) -> list[dict[str, Any]]:
        """Every case, newest activity first, with just enough for a list."""
        with self._lock:
            cases = sorted(self._cases.values(), key=lambda c: -c["updated"])
            return [self._summary(c) for c in cases]

    def get(self, case_id: str) -> dict[str, Any]:
        with self._lock:
            case = self._cases.get(case_id)
            if case is None:
                raise CaseError("No case with that id.")
            full = deepcopy(case)
        full.pop("owner", None)          # a session token must never reach a screen
        full["redactable"] = self._redactable(full)
        return full

    def update_profile(self, case_id: str, profile: dict[str, Any], by: str) -> dict[str, Any]:
        """Ground crew corrects the crewmember's details.

        Saved on the case, and - for a real account - as the account's profile
        from now on, so the astronaut's own Profile tab shows the correction.
        """
        clean = {str(k).strip()[:60]: str(v).strip()[:200]
                 for k, v in (profile or {}).items() if str(k).strip()}
        now = self.clock()
        with self._lock:
            case = self._require(case_id)
            case["crew"]["profile"] = clean
            account_id = case["crew"].get("account_id")
            if account_id:
                self._profiles[account_id] = clean
                self._save_profiles()
            case["updated"] = now
            self._audit(case, now, by, "ground", "edited the crewmember's profile")
            self._save(case)
        return self.get(case_id)

    def send_to_doctor(self, case_id: str, hidden: list[str], note: str, by: str) -> dict[str, Any]:
        """Build the redacted packet. The doctor only ever sees this."""
        now = self.clock()
        with self._lock:
            case = self._require(case_id)
            if not case["turns"]:
                raise CaseError("Nothing to send - VITALS has not answered anything in this case.")
            allowed = set(self._redactable(case))
            hidden = sorted({h for h in hidden or [] if h in allowed})
            case["packet"] = {
                "sent_at": now,
                "sent_by": by,
                "hidden": hidden,
                "content": self._redacted(case, set(hidden), note.strip()[:2000]),
            }
            case["review"] = None
            case["release"] = None
            case["status"] = WITH_DOCTOR
            case["new_since_sent"] = False
            case["updated"] = now
            self._audit(case, now, by, "ground",
                        f"sent to the doctor, withholding: {', '.join(hidden) or 'nothing'}")
            self._save(case)
        return self.get(case_id)

    def release(self, case_id: str, note: str, by: str) -> dict[str, Any]:
        """Ground crew has checked the doctor's reply. The astronaut sees it now."""
        note = (note or "").strip()
        if not note:
            raise CaseError("Write the message the crewmember will see before releasing it.")
        now = self.clock()
        with self._lock:
            case = self._require(case_id)
            if case["status"] not in (DOCTOR_REPLIED, RELEASED) or not case["review"]:
                raise CaseError("The doctor has not replied to this case yet.")
            case["release"] = {"at": now, "by": by, "note": note[:4000]}
            case["status"] = RELEASED
            case["updated"] = now
            self._audit(case, now, by, "ground", "verified the doctor's reply and released it")
            self._save(case)
        return self.get(case_id)

    # --- doctor --------------------------------------------------------------

    def doctor_queue(self) -> list[dict[str, Any]]:
        """Packets waiting on or answered by a doctor. Never the raw case."""
        with self._lock:
            sent = [c for c in self._cases.values() if c["packet"]]
            sent.sort(key=lambda c: (c["status"] != WITH_DOCTOR, -c["packet"]["sent_at"]))
            return [{
                "id": c["id"],
                "status": c["status"],
                "sent_at": c["packet"]["sent_at"],
                "level": c["packet"]["content"].get("level", "none"),
                "headline": c["packet"]["content"].get("headline", ""),
                "reviewed": c["review"] is not None,
            } for c in sent]

    def packet(self, case_id: str) -> dict[str, Any]:
        with self._lock:
            case = self._require(case_id)
            if not case["packet"]:
                raise CaseError("This case has not been sent to a doctor.")
            return {
                "id": case["id"],
                "status": case["status"],
                "sent_at": case["packet"]["sent_at"],
                "content": deepcopy(case["packet"]["content"]),
                "review": deepcopy(case["review"]),
            }

    def review(self, case_id: str, verdict: str, note: str, by: str) -> dict[str, Any]:
        if verdict not in VERDICTS:
            raise CaseError("Choose agree, disagree, or your own read.")
        note = (note or "").strip()
        if verdict != "agree" and not note:
            raise CaseError("Say what you would do instead - the crew needs more than a 'no'.")
        now = self.clock()
        with self._lock:
            case = self._require(case_id)
            if not case["packet"]:
                raise CaseError("This case has not been sent to a doctor.")
            case["review"] = {"at": now, "by": by, "verdict": verdict, "note": note[:4000]}
            case["status"] = DOCTOR_REPLIED
            case["release"] = None
            case["updated"] = now
            self._audit(case, now, by, "doctor", f"replied: {VERDICTS[verdict].lower()}")
            self._save(case)
        return self.packet(case_id)

    # --- status --------------------------------------------------------------

    def counts(self) -> dict[str, int]:
        with self._lock:
            counts = {status: 0 for status in STATUSES}
            for case in self._cases.values():
                counts[case["status"]] += 1
            counts["total"] = len(self._cases)
            return counts

    # --- helpers -------------------------------------------------------------

    def _require(self, case_id: str) -> dict[str, Any]:
        case = self._cases.get(case_id or "")
        if case is None:
            raise CaseError("No case with that id.")
        return case

    def _new_id(self, now: float) -> str:
        stamp = time.strftime("%y%m%d-%H%M", time.localtime(now))
        while True:
            case_id = f"{stamp}-{secrets.token_hex(2)}"
            if case_id not in self._cases:
                return case_id

    @staticmethod
    def _audit(case, now, who, role, action) -> None:
        case["log"].append({"at": now, "by": who, "role": role, "action": action})

    @staticmethod
    def _redactable(case) -> dict[str, str]:
        options = dict(REDACTABLE)
        for key in (case["crew"].get("profile") or {}):
            options[f"profile:{key}"] = f"Profile: {key}"
        return options

    @staticmethod
    def _summary(case) -> dict[str, Any]:
        last = case["turns"][-1]["answer"] if case["turns"] else {}
        return {
            "id": case["id"],
            "title": case["title"],
            "crew_name": case["crew"].get("name", "?"),
            "emergency": bool(case["crew"].get("emergency")),
            "created": case["created"],
            "updated": case["updated"],
            "status": case["status"],
            "level": _level_of(last),
            "headline": _headline(last),
            "turns": len(case["turns"]),
            "new_since_sent": case.get("new_since_sent", False),
        }

    @staticmethod
    def _redacted(case, hidden: set[str], note: str) -> dict[str, Any]:
        """The doctor's packet. Built from the latest answer, minus what is hidden."""
        crew = case["crew"]
        last = case["turns"][-1]["answer"] if case["turns"] else {}
        profile = {k: v for k, v in (crew.get("profile") or {}).items()
                   if f"profile:{k}" not in hidden}

        content: dict[str, Any] = {
            "crew_name": None if "name" in hidden else crew.get("name"),
            "emergency_access": bool(crew.get("emergency")),
            "profile": profile,
            "note_from_ground": note,
            "level": _level_of(last),
            "headline": _headline(last),
            "withheld": [label for key, label in CaseStore._redactable(case).items() if key in hidden],
            "asked_at": case["created"],
        }
        content["transcript"] = None if "transcript" in hidden else [
            {"at": t["at"], "text": t["text"]} for t in case["turns"]
        ]
        content["vitals_answer"] = None if "vitals_answer" in hidden else {
            "escalate": last.get("escalate", False),
            "escalation_reason": last.get("escalation_reason", ""),
            "uncertainty": last.get("uncertainty", ""),
            "differential": [
                {k: d.get(k) for k in ("name", "urgency", "confidence", "reasoning",
                                       "supporting", "against", "recommend", "sources")}
                for d in last.get("differential", [])
            ],
            "model": last.get("model", ""),
        }
        content["understood"] = None if "understood" in hidden else [
            {"label": f.get("label"), "value": f.get("value")} for f in last.get("known", [])
        ]
        return content


def _title(text: str, limit: int = 70) -> str:
    """The first line, cut at a word - "goes to my groin, a" reads like a bug."""
    line = (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""
    if not line:
        return "Untitled"
    if len(line) <= limit:
        return line
    return line[:limit].rsplit(" ", 1)[0].rstrip(",.;: ") + "…"


def _level_of(answer: dict[str, Any]) -> str:
    """The same rule the astronaut screen uses: the alarm's level, else the top urgency."""
    if not answer:
        return "none"
    if answer.get("escalate"):
        level = (answer.get("escalation") or {}).get("level", "urgent")
        return "emergency" if level == "emergency" else "urgent"
    differential = answer.get("differential") or []
    return differential[0].get("urgency", "routine") if differential else "none"


def _headline(answer: dict[str, Any]) -> str:
    """One line for a list: the condition the alarm is about, or the top one."""
    if not answer:
        return ""
    flagged = (answer.get("escalation") or {}).get("conditions") or []
    if flagged:
        return flagged[0].get("name", "")
    differential = answer.get("differential") or []
    return differential[0].get("name", "") if differential else "Nothing in the knowledge base fits"


__all__ = ["CaseStore", "CaseError", "DATA_DIR", "VERDICTS", "REDACTABLE", "DEFAULT_HIDDEN",
           "OPEN", "WITH_DOCTOR", "DOCTOR_REPLIED", "RELEASED", "STATUSES"]
