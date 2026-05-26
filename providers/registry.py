from __future__ import annotations

from providers.providers.amp import AmpProvider
from providers.providers.claude_code import ClaudeCodeProvider
from providers.providers.cline import ClineProvider
from providers.providers.codex import CodexProvider
from providers.providers.copilot import CopilotProvider
from providers.providers.cursor import CursorProvider
from providers.providers.droid import DroidProvider
from providers.providers.gemini_cli import GeminiCliProvider
from providers.providers.hermes import HermesProvider
from providers.providers.openclaw import OpenclawProvider
from providers.providers.opencode import OpencodeProvider
from providers.providers.pi import PiProvider
from providers.providers.traces import TracesProvider
from providers.providers import Provider


PROVIDERS: dict[str, Provider] = {
    "amp": AmpProvider(),
    "claude-code": ClaudeCodeProvider(),
    "cline": ClineProvider(),
    "codex": CodexProvider(),
    "copilot": CopilotProvider(),
    "cursor": CursorProvider(),
    "droid": DroidProvider(),
    "gemini-cli": GeminiCliProvider(),
    "hermes": HermesProvider(),
    "openclaw": OpenclawProvider(),
    "opencode": OpencodeProvider(),
    "pi": PiProvider(),
    "traces": TracesProvider(),
}
