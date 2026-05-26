from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


CLINE_TASKS_ROOT = os.path.expanduser("~/.cline/data/tasks")


class _ClineTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _ClineMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: list[_ClineTextPart] = Field(default_factory=list)


class _ClineRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    text_content: Optional[str] = None
    message: _ClineMessage = Field(default_factory=_ClineMessage)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, dict):
            return {}
        data = dict(value)
        if isinstance(data.get("message"), dict):
            return data
        content = data.get("content")
        if isinstance(content, str):
            data["text_content"] = content
        elif isinstance(content, list):
            data["message"] = {"content": content}
        return data


class ClineProvider(Provider):
    provider_id = "cline"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(CLINE_TASKS_ROOT, "*", "api_conversation_history.json"))
        ):
            events: list[NormalizedEvent] = []
            title = ""
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    payload = json.load(source_file)
            except (OSError, json.JSONDecodeError):
                continue
            raw_records = payload if isinstance(payload, list) else [payload]
            for raw_record in raw_records:
                try:
                    record = _ClineRecord.model_validate(raw_record)
                except ValidationError:
                    continue
                content = record.text_content or "\n".join(
                    item.text for item in record.message.content if item.text and item.text.strip()
                ).strip()
                if content and record.role == "user":
                    if not title:
                        title = content[:120]
                    events.append(NormalizedEvent(type="user_message", content=content, timestamp=None))
                elif content and record.role == "assistant":
                    events.append(NormalizedEvent(type="agent_text", content=content, timestamp=None))
            traces.append(
                NormalizedTrace(
                    id=os.path.basename(os.path.dirname(source_path)),
                    agent_id=self.provider_id,
                    title=title,
                    timestamp=None,
                    directory="",
                    source_path=source_path,
                    events=events,
                )
            )
        return traces
