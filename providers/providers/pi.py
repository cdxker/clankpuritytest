from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


PI_SESSIONS_ROOT = os.path.expanduser("~/.pi/agent/sessions")


class _PiTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _PiMessageBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: list[_PiTextPart] = Field(default_factory=list)


class _PiRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    id: Optional[str] = None
    timestamp: Optional[str] = None
    cwd: Optional[str] = None
    message: Optional[_PiMessageBody] = None


class PiProvider(Provider):
    provider_id = "pi"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(PI_SESSIONS_ROOT, "**", "*.jsonl"), recursive=True)
        ):
            events: list[NormalizedEvent] = []
            trace_id = os.path.splitext(os.path.basename(source_path))[0]
            title = ""
            timestamp = None
            directory = ""
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    for raw_line in source_file:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            record = _PiRecord.model_validate(json.loads(line))
                        except (json.JSONDecodeError, ValidationError):
                            continue
                        event_timestamp = None
                        if record.timestamp:
                            try:
                                event_timestamp = int(
                                    datetime.fromisoformat(record.timestamp.replace("Z", "+00:00")).timestamp() * 1000
                                )
                            except ValueError:
                                event_timestamp = None
                        if record.type == "session":
                            trace_id = record.id or trace_id
                            directory = record.cwd or directory
                            if event_timestamp is not None:
                                timestamp = event_timestamp
                        elif record.type == "message" and record.message:
                            text = "\n".join(
                                item.text for item in record.message.content if item.text and item.text.strip()
                            ).strip()
                            if text and record.message.role == "user":
                                if not title:
                                    title = text[:120]
                                events.append(NormalizedEvent(type="user_message", content=text, timestamp=event_timestamp))
                            elif text and record.message.role == "assistant":
                                events.append(NormalizedEvent(type="agent_text", content=text, timestamp=event_timestamp))
                traces.append(
                    NormalizedTrace(
                        id=trace_id,
                        agent_id=self.provider_id,
                        title=title,
                        timestamp=timestamp,
                        directory=directory,
                        source_path=source_path,
                        events=events,
                    )
                )
            except OSError:
                continue
        return traces
