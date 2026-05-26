from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


GEMINI_ROOT = os.path.expanduser("~/.gemini")


class _GeminiTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _GeminiMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    parts: list[_GeminiTextPart] = Field(default_factory=list)

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


class _GeminiPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = None
    directory: Optional[str] = None
    timestamp: Optional[int] = None
    messages: list[_GeminiMessage] = Field(default_factory=list)


class GeminiCliProvider(Provider):
    provider_id = "gemini-cli"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(GEMINI_ROOT, "**", "*.json*"), recursive=True)
        ):
            if not os.path.isfile(source_path):
                continue
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    raw_payload = json.load(source_file)
                    payload = _GeminiPayload.model_validate(
                        {"messages": raw_payload} if isinstance(raw_payload, list) else raw_payload
                    )
            except (OSError, json.JSONDecodeError, ValidationError):
                continue
            events: list[NormalizedEvent] = []
            title = payload.title or ""
            for record in payload.messages:
                text = "\n".join(item.text for item in record.parts if item.text and item.text.strip()).strip()
                if text and record.role == "user":
                    if not title:
                        title = text[:120]
                    events.append(NormalizedEvent(type="user_message", content=text, timestamp=None))
                elif text and record.role == "assistant":
                    events.append(NormalizedEvent(type="agent_text", content=text, timestamp=None))
            traces.append(
                NormalizedTrace(
                    id=os.path.splitext(os.path.basename(source_path))[0],
                    agent_id=self.provider_id,
                    title=title,
                    timestamp=payload.timestamp,
                    directory=payload.directory or "",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
