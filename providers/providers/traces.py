from __future__ import annotations

import json
import os
import sqlite3
from typing import Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


TRACES_DB_PATH = os.path.expanduser("~/.traces/traces.db")


class _TraceEventRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    content: Optional[str] = None
    timestamp: Optional[int] = None


class TracesProvider(Provider):
    provider_id = "traces"

    def scrape(self) -> list[NormalizedTrace]:
        if not os.path.exists(TRACES_DB_PATH):
            return []

        connection = sqlite3.connect(TRACES_DB_PATH)
        connection.row_factory = sqlite3.Row
        try:
            trace_rows = connection.execute(
                "SELECT id, agent_id, title, timestamp, directory, source_path FROM traces ORDER BY timestamp DESC"
            ).fetchall()
            event_rows = connection.execute(
                "SELECT trace_id, event_json FROM events ORDER BY trace_id, id ASC"
            ).fetchall()
        finally:
            connection.close()

        events_by_trace: dict[str, list[NormalizedEvent]] = {}
        for event_row in event_rows:
            try:
                event_json = _TraceEventRecord.model_validate(json.loads(event_row["event_json"]))
            except (json.JSONDecodeError, ValidationError):
                continue
            if event_json.type not in {"agent_text", "user_message"}:
                continue
            if not event_json.content or not event_json.content.strip():
                continue
            events_by_trace.setdefault(event_row["trace_id"], []).append(
                NormalizedEvent(
                    type=event_json.type,
                    content=event_json.content,
                    timestamp=event_json.timestamp,
                )
            )

        traces: list[NormalizedTrace] = []
        for trace_row in trace_rows:
            try:
                timestamp = int(trace_row["timestamp"]) if trace_row["timestamp"] is not None else None
            except (TypeError, ValueError):
                timestamp = None
            traces.append(
                NormalizedTrace(
                    id=trace_row["id"],
                    agent_id=trace_row["agent_id"] or "traces",
                    title=trace_row["title"] or "",
                    timestamp=timestamp,
                    directory=trace_row["directory"] or "",
                    source_path=trace_row["source_path"] or "",
                    events=events_by_trace.get(trace_row["id"], []),
                )
            )
        return traces
