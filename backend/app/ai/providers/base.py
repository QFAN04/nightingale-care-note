"""Provider boundary for turning a redacted transcript into raw JSON."""

from typing import Protocol


class ScribeProvider(Protocol):
    """A replaceable provider that returns untrusted, unvalidated JSON text."""

    async def generate(self, *, system_prompt: str, transcript: str) -> str:
        """Generate raw JSON text from an already-redacted transcript."""
        ...
