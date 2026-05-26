from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


AMP_THREADS_ROOT = os.path.expanduser("~/.local/share/amp/threads")


class _AmpTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _AmpMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sentAt: Optional[int] = None


class _AmpMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: list[_AmpTextPart] = Field(default_factory=list)
    meta: _AmpMeta = Field(default_factory=_AmpMeta)


class _AmpThread(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    title: Optional[str] = None
    directory: Optional[str] = None
    created: Optional[int] = None
    messages: list[_AmpMessage] = Field(default_factory=list)


class AmpProvider(Provider):
    provider_id = "amp"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(glob.glob(os.path.join(AMP_THREADS_ROOT, "*.json"))):
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    payload = _AmpThread.model_validate(json.load(source_file))
            except (OSError, json.JSONDecodeError, ValidationError):
                continue
            events: list[NormalizedEvent] = []
            title = payload.title or ""
            for message in payload.messages:
                text = "\n".join(item.text for item in message.content if item.text and item.text.strip()).strip()
                if text and message.role == "user":
                    if not title:
                        title = text[:120]
                    events.append(NormalizedEvent(type="user_message", content=text, timestamp=message.meta.sentAt))
                elif text and message.role == "assistant":
                    events.append(NormalizedEvent(type="agent_text", content=text, timestamp=message.meta.sentAt))
            traces.append(
                NormalizedTrace(
                    id=payload.id or os.path.splitext(os.path.basename(source_path))[0],
                    agent_id=self.provider_id,
                    title=title,
                    timestamp=payload.created,
                    directory=payload.directory or "",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
