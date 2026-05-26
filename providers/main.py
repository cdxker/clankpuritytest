from __future__ import annotations

from providers.providers import NormalizedTrace
from providers.registry import PROVIDERS


def scrape_providers(provider_ids: list[str] | None = None) -> list[NormalizedTrace]:
    selected_provider_ids = provider_ids or list(PROVIDERS.keys())
    traces_by_key: dict[tuple[str, str], NormalizedTrace] = {}

    for provider_id in selected_provider_ids:
        provider = PROVIDERS[provider_id]
        for trace in provider.scrape():
            traces_by_key[(trace.agent_id, trace.id)] = trace

    return sorted(
        traces_by_key.values(),
        key=lambda trace: trace.timestamp or 0,
        reverse=True,
    )
