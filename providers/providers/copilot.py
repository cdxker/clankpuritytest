from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


COPILOT_SESSIONS_ROOT = os.path.expanduser("~/Library/Application Support")


class _CopilotEventBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: Optional[str] = None


class _CopilotRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    content: Optional[str] = None
    event: _CopilotEventBody = _CopilotEventBody()

    @model_validator(mode="after")
    def normalize(self):
        if not self.role and self.event.role:
            self.role = self.event.role
        if not self.content and self.event.content:
            self.content = self.event.content
        return self


class CopilotProvider(Provider):
    provider_id = "copilot"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(os.path.join(COPILOT_SESSIONS_ROOT, "**", "events.jsonl"), recursive=True)
        ):
            if "session-state" not in source_path and "copilot" not in source_path.lower():
                continue
            events: list[NormalizedEvent] = []
            title = ""
            try:
                with open(source_path, "r", encoding="utf-8") as source_file:
                    for raw_line in source_file:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            record = _CopilotRecord.model_validate(json.loads(line))
                        except (json.JSONDecodeError, ValidationError):
                            continue
                        text = (record.content or "").strip()
                        if text and record.role == "user":
                            if not title:
                                title = text[:120]
                            events.append(NormalizedEvent(type="user_message", content=text, timestamp=None))
                        elif text and record.role == "assistant":
                            events.append(NormalizedEvent(type="agent_text", content=text, timestamp=None))
            except OSError:
                continue
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
