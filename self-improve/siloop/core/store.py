"""EventLog — pure I/O over the append-only log and the derived snapshot (DESIGN §3/§8).

No domain rules live here. The public surface is `read()` / `append()` /
`write_snapshot()`; `fold` (a pure function) is what turns events into the snapshot, and
the use-case layer wires them together. `append` takes a cross-platform advisory file
lock so two concurrent `loop log` calls cannot interleave (DESIGN §8); the JSONL append
is the commit point, the snapshot is a best-effort cache recoverable by `rebuild`.
"""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from typing import Dict, Iterator, List

from .models import Event, Pattern, event_from_dict, event_to_dict, pattern_to_dict

try:  # optional cross-platform lock
    from filelock import FileLock  # type: ignore

    @contextmanager
    def _locked(path: str) -> Iterator[None]:
        lock = FileLock(path + ".lock")
        with lock:
            yield
except ImportError:  # pragma: no cover - lock is a no-op without filelock
    @contextmanager
    def _locked(path: str) -> Iterator[None]:
        yield


class EventLog:
    def __init__(self, events_path: str, patterns_path: str) -> None:
        self.events_path = events_path
        self.patterns_path = patterns_path

    def read(self) -> List[Event]:
        if not os.path.exists(self.events_path):
            return []
        events = []
        with open(self.events_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    events.append(event_from_dict(json.loads(line)))
        return events

    def append(self, event: Event) -> None:
        with _locked(self.events_path):
            os.makedirs(os.path.dirname(os.path.abspath(self.events_path)), exist_ok=True)
            with open(self.events_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event_to_dict(event), ensure_ascii=False) + "\n")

    def write_snapshot(self, rollup: Dict[str, Pattern]) -> None:
        data = {key: pattern_to_dict(p) for key, p in sorted(rollup.items())}
        os.makedirs(os.path.dirname(os.path.abspath(self.patterns_path)), exist_ok=True)
        # atomic replace so a reader never sees a half-written snapshot
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(self.patterns_path)))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            os.replace(tmp, self.patterns_path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def read_snapshot(self) -> dict:
        if not os.path.exists(self.patterns_path):
            return {}
        with open(self.patterns_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
