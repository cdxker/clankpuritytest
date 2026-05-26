from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


OPENCLAW_ROOT = os.path.expanduser("~/.openclaw/agents/main/sessions")


class _OpenclawMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: Optional[str] = None


class _OpenclawSessionFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = None
    directory: Optional[str] = None
    updatedAt: Optional[int] = None
    messages: list[_OpenclawMessage] = Field(default_factory=list)


class _OpenclawIndexRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sessionId: Optional[str] = None
    sourcePath: Optional[str] = None
    title: Optional[str] = None
    directory: Optional[str] = None
    updatedAt: Optional[int] = None


class OpenclawProvider(Provider):
    provider_id = "openclaw"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        index_path = os.path.join(OPENCLAW_ROOT, "sessions.json")
        indexed_session_ids: set[str] = set()
        indexed_source_paths: set[str] = set()
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as source_file:
                    payload = [_OpenclawIndexRecord.model_validate(item) for item in json.load(source_file)]
            except (OSError, json.JSONDecodeError, ValidationError, TypeError):
                payload = []
            for record in payload:
                if not record.sessionId:
                    continue
                indexed_session_ids.add(record.sessionId)
                source_path = (
                    record.sourcePath
                    if record.sourcePath and os.path.isabs(record.sourcePath)
                    else os.path.join(OPENCLAW_ROOT, record.sourcePath or f"{record.sessionId}.json")
                )
                indexed_source_paths.add(os.path.abspath(source_path))
                events: list[NormalizedEvent] = []
                title = record.title or ""
                if os.path.exists(source_path):
                    try:
                        with open(source_path, "r", encoding="utf-8") as session_file:
                            session_payload = _OpenclawSessionFile.model_validate(json.load(session_file))
                    except (OSError, json.JSONDecodeError, ValidationError):
                        session_payload = _OpenclawSessionFile()
                    for message in session_payload.messages:
                        text = (message.content or "").strip()
                        if text and message.role == "user":
                            if not title:
                                title = text[:120]
                            events.append(NormalizedEvent(type="user_message", content=text, timestamp=None))
                        elif text and message.role == "assistant":
                            events.append(NormalizedEvent(type="agent_text", content=text, timestamp=None))
                traces.append(
                    NormalizedTrace(
                        id=record.sessionId,
                        agent_id=self.provider_id,
                        title=title,
                        timestamp=record.updatedAt,
                        directory=record.directory or "",
                        source_path=source_path,
                        events=events,
                    )
                )
        for source_path in sorted(glob.glob(os.path.join(OPENCLAW_ROOT, "*.json"))):
            if os.path.basename(source_path) == "sessions.json":
                continue
            if os.path.abspath(source_path) in indexed_source_paths:
                continue
            session_id = os.path.splitext(os.path.basename(source_path))[0]
            if session_id in indexed_session_ids:
                continue
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    payload = _OpenclawSessionFile.model_validate(json.load(source_file))
            except (OSError, json.JSONDecodeError, ValidationError):
                continue
            events: list[NormalizedEvent] = []
            title = payload.title or ""
            for message in payload.messages:
                text = (message.content or "").strip()
                if text and message.role == "user":
                    if not title:
                        title = text[:120]
                    events.append(NormalizedEvent(type="user_message", content=text, timestamp=None))
                elif text and message.role == "assistant":
                    events.append(NormalizedEvent(type="agent_text", content=text, timestamp=None))
            traces.append(
                NormalizedTrace(
                    id=session_id,
                    agent_id=self.provider_id,
                    title=title,
                    timestamp=payload.updatedAt,
                    directory=payload.directory or "",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
