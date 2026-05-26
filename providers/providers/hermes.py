from __future__ import annotations

import glob
import json
import os
import sqlite3
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


HERMES_ROOT = os.path.expanduser("~/.hermes")


class _HermesMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: Optional[str] = None


class _HermesSessionFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    directory: Optional[str] = None
    createdAt: Optional[int] = None
    messages: list[_HermesMessage] = Field(default_factory=list)


class HermesProvider(Provider):
    provider_id = "hermes"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        sqlite_paths = sorted(glob.glob(os.path.join(HERMES_ROOT, "**", "*.sqlite*"), recursive=True))
        for sqlite_path in sqlite_paths:
            try:
                connection = sqlite3.connect(sqlite_path)
                connection.row_factory = sqlite3.Row
                try:
                    rows = connection.execute("SELECT id, title, created_at, directory FROM sessions").fetchall()
                finally:
                    connection.close()
            except sqlite3.Error:
                continue
            for row in rows:
                try:
                    timestamp = int(row["created_at"]) if row["created_at"] is not None else None
                except (TypeError, ValueError):
                    timestamp = None
                traces.append(
                    NormalizedTrace(
                        id=str(row["id"]),
                        agent_id=self.provider_id,
                        title=row["title"] or "",
                        timestamp=timestamp,
                        directory=row["directory"] or "",
                        source_path=sqlite_path,
                        events=[],
                    )
                )
        for source_path in sorted(
            glob.glob(os.path.join(HERMES_ROOT, "**", "session_*.json"), recursive=True)
        ):
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    payload = _HermesSessionFile.model_validate(json.load(source_file))
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
                    id=payload.id or os.path.splitext(os.path.basename(source_path))[0],
                    agent_id=self.provider_id,
                    title=title,
                    timestamp=payload.createdAt,
                    directory=payload.directory or "",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
