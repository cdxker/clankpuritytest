from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict


NormalizedEventType = Literal["agent_text", "user_message"]


class NormalizedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: NormalizedEventType
    content: str
    timestamp: Optional[int]


class NormalizedTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    title: str
    timestamp: Optional[int]
    directory: str
    source_path: str
    events: list[NormalizedEvent]


class Provider(ABC):
    provider_id: str

    @abstractmethod
    def scrape(self) -> list[NormalizedTrace]:
        raise NotImplementedError
