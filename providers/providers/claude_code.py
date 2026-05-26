from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from providers.providers import NormalizedEvent, NormalizedTrace, Provider


CLAUDE_PROJECTS_ROOT = os.path.expanduser("~/.claude/projects")
CLAUDE_LOCAL_AGENT_MODE_ROOT = os.path.expanduser("~/Library/Application Support/Claude/local-agent-mode-sessions")


class _ClaudeMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text_content: Optional[str] = None
    parts: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, value):
        if not isinstance(value, dict):
            return {}
        data = dict(value)
        content = data.get("content")
        if isinstance(content, str):
            data["text_content"] = content
        elif isinstance(content, list):
            data["parts"] = [
                item.get("text")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str) and item.get("text", "").strip()
            ]
        return data


class _ClaudeRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Optional[str] = None
    timestamp: Optional[str] = None
    cwd: Optional[str] = None
    message: Optional[_ClaudeMessage] = None


class ClaudeCodeProvider(Provider):
    provider_id = "claude-code"

    def scrape(self) -> list[NormalizedTrace]:
        traces: list[NormalizedTrace] = []
        source_paths = sorted(glob.glob(os.path.join(CLAUDE_PROJECTS_ROOT, "**", "*.jsonl"), recursive=True))
        source_paths.extend(
            sorted(
                glob.glob(
                    os.path.join(CLAUDE_LOCAL_AGENT_MODE_ROOT, "**", ".claude", "projects", "**", "*.jsonl"),
                    recursive=True,
                )
            )
        )
        for source_path in source_paths:
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
                            record = _ClaudeRecord.model_validate(json.loads(line))
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
                        if timestamp is None and event_timestamp is not None:
                            timestamp = event_timestamp
                        if record.cwd:
                            directory = record.cwd
                        content = ""
                        if record.type in {"user", "assistant"} and record.message:
                            content = (record.message.text_content or "\n".join(record.message.parts)).strip()
                        if content and record.type == "user":
                            if not title:
                                title = content[:120]
                            events.append(NormalizedEvent(type="user_message", content=content, timestamp=event_timestamp))
                        elif content and record.type == "assistant":
                            events.append(NormalizedEvent(type="agent_text", content=content, timestamp=event_timestamp))
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
