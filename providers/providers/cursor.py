from __future__ import annotations

import glob
import json
import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


CURSOR_PROJECTS_ROOT = os.path.expanduser("~/.cursor/projects")


class _CursorTextPart(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = None


class _CursorMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: list[_CursorTextPart] = Field(default_factory=list)


class _CursorRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: Optional[str] = None
    message: Optional[_CursorMessage] = None


class CursorProvider(Provider):
    provider_id = "cursor"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        for source_path in sorted(
            glob.glob(
                os.path.join(CURSOR_PROJECTS_ROOT, "**", "agent-transcripts", "**", "*.jsonl"),
                recursive=True,
            )
        ):
            events: list[NormalizedEvent] = []
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
                            record = _CursorRecord.model_validate(json.loads(line))
                        except (json.JSONDecodeError, ValidationError):
                            continue
                        content = "\n".join(
                            item.text
                            for item in (record.message.content if record.message else [])
                            if item.text and item.text.strip()
                        ).strip()
                        if content and record.role == "user":
                            if not title:
                                title = content[:120]
                            events.append(NormalizedEvent(type="user_message", content=content, timestamp=None))
                        elif content and record.role == "assistant":
                            events.append(NormalizedEvent(type="agent_text", content=content, timestamp=None))
                directory = source_path.split("/agent-transcripts/")[0]
                traces.append(
                    NormalizedTrace(
                        id=os.path.splitext(os.path.basename(source_path))[0],
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
