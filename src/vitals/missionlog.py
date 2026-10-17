"""The mission log: one line per thing that happened, in the HUNCH log format.

The HUNCH 2026-27 requirement list says log entries "must record subsystem,
element, current status, and timestamp". Every entry here has exactly those
four fields, plus an optional plain-English detail:

    {"timestamp": "2026-10-17T22:14:03Z", "subsystem": "ENGINE",
     "element": "case:demo_renal_colic", "status": "PASS",
     "detail": "top = renal_stone, escalate = True (expected both)"}

SUBSYSTEMS are the boxes on the functional diagram (pdr/07_functional_diagrams.md):
KB, EXTRACT, SCOPE, RETRIEVAL, REASON, ENGINE, SENSORS, CASES, ACCOUNTS, SERVER.
ELEMENT is the specific thing inside that box - a file, a case, a route.
STATUS is one word from STATUSES.

The file is JSON Lines - one JSON object per line - so it can be appended to
safely by a running server, read by `vitals log`, opened in a text editor, or
loaded into a spreadsheet for the test-results statistics at CDR.

PRIVACY: the log records WHAT the system did, never what a crewmember said.
No complaint text, no PINs, no profile details. Names of logged-in staff are
fine (that is an audit trail); the medical content stays in the case files.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

SUBSYSTEMS = (
    "KB", "EXTRACT", "SCOPE", "RETRIEVAL", "REASON", "ENGINE",
    "SENSORS", "CASES", "ACCOUNTS", "SERVER", "MISSION",
)

# OK/FAIL are for things that happen; PASS/FAIL for checks with an expected
# answer; SKIP when a check could not run (e.g. no model on this machine);
# NOT_CONNECTED for hardware that is honestly absent; INFO for plain events.
STATUSES = ("OK", "PASS", "FAIL", "WARN", "SKIP", "NOT_CONNECTED", "INFO")



def utc_timestamp(seconds: Optional[float] = None) -> str:
    """ISO 8601, UTC, to the second. Mission time is UTC - so is this."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds if seconds is not None
                                                             else time.time()))


@dataclass(frozen=True)
class Entry:
    timestamp: str
    subsystem: str
    element: str
    status: str
    detail: str = ""

    def as_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class MissionLog:
    """Append-only log. `path=None` keeps entries in memory only (tests)."""

    def __init__(self, path: Optional[Path] = None, clock=time.time):
        self.path = Path(path) if path else None
        self.clock = clock
        self.entries: list[Entry] = []
        self._lock = threading.Lock()
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, subsystem: str, element: str, status: str, detail: str = "") -> Entry:
        if subsystem not in SUBSYSTEMS:
            raise ValueError(f"unknown subsystem {subsystem!r}; use one of {SUBSYSTEMS}")
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}; use one of {STATUSES}")
        entry = Entry(utc_timestamp(self.clock()), subsystem, str(element), status,
                      " ".join(str(detail).split())[:500])
        with self._lock:
            self.entries.append(entry)
            if self.path:
                # One write per line, opened in append mode: a crash loses at
                # most the line being written, never the file.
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(entry.as_line() + "\n")
        return entry


def read_log(path: Path) -> list[Entry]:
    """Every entry in a log file. A damaged line is skipped, not fatal."""
    entries: list[Entry] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            entries.append(Entry(**{k: data.get(k, "") for k in
                                    ("timestamp", "subsystem", "element", "status", "detail")}))
        except (ValueError, TypeError):
            continue
    return entries


def format_table(entries: Iterable[Entry]) -> str:
    """The four required columns, readable in a terminal or pasted onto the board."""
    entries = list(entries)
    rows = [("TIMESTAMP (UTC)", "SUBSYSTEM", "ELEMENT", "STATUS", "DETAIL")]
    rows += [(e.timestamp, e.subsystem, e.element, e.status, e.detail) for e in entries]
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    out = []
    for r in rows:
        out.append("  ".join(r[i].ljust(widths[i]) for i in range(4)) + "  " + r[4])
    return "\n".join(out)


def summary(entries: Iterable[Entry]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        counts[e.status] = counts.get(e.status, 0) + 1
    return counts
