from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


OPENCODE_SESSIONS_ROOT = os.path.expanduser("~/.local/share/opencode/storage/session")


class _OpencodeTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _OpencodeTime(BaseModel):
    model_config = ConfigDict(extra="ignore")

    created: Optional[int] = None


class _OpencodeMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    parts: list[_OpencodeTextPart] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, dict):
            return {}
        data = dict(value)
        content = data.get("content")
        if isinstance(content, str):
            data["parts"] = [{"text": content}]
        elif isinstance(content, list):
            data["parts"] = content
        return data


class _OpencodeSession(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    directory: Optional[str] = None
    time: _OpencodeTime = Field(default_factory=_OpencodeTime)
    messages: list[_OpencodeMessage] = Field(default_factory=list)


class OpencodeProvider(Provider):
    provider_id = "opencode"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(OPENCODE_SESSIONS_ROOT, "**", "*.json"), recursive=True)
        ):
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    payload = _OpencodeSession.model_validate(json.load(source_file))
            except (OSError, json.JSONDecodeError, ValidationError):
                continue
            events: list[NormalizedEvent] = []
            title = payload.title or ""
            for message in payload.messages:
                text = "\n".join(item.text for item in message.parts if item.text and item.text.strip()).strip()
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
                    timestamp=payload.time.created,
                    directory=payload.directory or "",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
