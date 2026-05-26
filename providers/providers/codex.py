from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


CODEX_SESSIONS_ROOT = os.path.expanduser("~/.codex/sessions")


class _CodexPayloadContentPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _CodexMessagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    role: Optional[str] = None
    message: Optional[str] = None
    content: list[_CodexPayloadContentPart] = Field(default_factory=list)


class _CodexSessionMetaPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    cwd: Optional[str] = None
    timestamp: Optional[str] = None


class _CodexRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    timestamp: Optional[str] = None
    payload: Optional[dict] = None


class CodexProvider(Provider):
    provider_id = "codex"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(CODEX_SESSIONS_ROOT, "**", "*.jsonl"), recursive=True)
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
                            record = _CodexRecord.model_validate(json.loads(line))
                        except (json.JSONDecodeError, ValidationError):
                            continue
                        iso_timestamp = record.timestamp
                        event_timestamp = None
                        if iso_timestamp:
                            try:
                                event_timestamp = int(
                                    datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00")).timestamp() * 1000
                                )
                            except ValueError:
                                event_timestamp = None
                        if record.type == "session_meta" and record.payload:
                            try:
                                payload = _CodexSessionMetaPayload.model_validate(record.payload)
                            except ValidationError:
                                payload = None
                            if payload:
                                trace_id = payload.id or trace_id
                                directory = payload.cwd or directory
                                if payload.timestamp and timestamp is None:
                                    try:
                                        timestamp = int(
                                            datetime.fromisoformat(
                                                payload.timestamp.replace("Z", "+00:00")
                                            ).timestamp()
                                            * 1000
                                        )
                                    except ValueError:
                                        pass
                        elif record.type == "event_msg" and record.payload:
                            try:
                                payload = _CodexMessagePayload.model_validate(record.payload)
                            except ValidationError:
                                payload = None
                            content = payload.message.strip() if payload and payload.type == "agent_message" and payload.message else ""
                            if content:
                                events.append(NormalizedEvent(type="agent_text", content=content, timestamp=event_timestamp))
                        elif record.type == "response_item" and record.payload:
                            try:
                                payload = _CodexMessagePayload.model_validate(record.payload)
                            except ValidationError:
                                payload = None
                            parts = [item.text for item in (payload.content if payload else []) if item.text and item.text.strip()]
                            content = "\n".join(parts).strip()
                            if content and payload and payload.type == "message" and payload.role == "user":
                                if not title:
                                    title = content[:120]
                                events.append(NormalizedEvent(type="user_message", content=content, timestamp=event_timestamp))
                            elif content and payload and payload.type == "message" and payload.role == "assistant":
                                events.append(NormalizedEvent(type="agent_text", content=content, timestamp=event_timestamp))
                            if timestamp is None and event_timestamp is not None:
                                timestamp = event_timestamp
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
