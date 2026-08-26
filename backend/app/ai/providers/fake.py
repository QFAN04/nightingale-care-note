"""Deterministic offline provider used by tests and local development."""

from dataclasses import dataclass, field


@dataclass
class FakeScribeProvider:
    raw_response: str
    calls: list[dict[str, str]] = field(default_factory=list)

    async def generate(self, *, system_prompt: str, transcript: str) -> str:
        self.calls.append(
            {"system_prompt": system_prompt, "transcript": transcript}
        )
        return self.raw_response
