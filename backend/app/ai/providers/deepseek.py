"""DeepSeek Chat Completions adapter for JSON-mode scribe output."""

from typing import Any

import httpx


class ProviderResponseError(RuntimeError):
    """Raised when a provider response cannot be safely consumed."""


class DeepSeekScribeProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        max_tokens: int = 2048,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._max_tokens = max_tokens
        self._timeout_seconds = timeout_seconds
        self._client = client

    async def generate(self, *, system_prompt: str, transcript: str) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "max_tokens": self._max_tokens,
        }

        if self._client is not None:
            response = await self._client.post(
                "/chat/completions",
                headers=self._headers,
                json=payload,
            )
        else:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers=self._headers,
                    json=payload,
                )

        response.raise_for_status()
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderResponseError("DeepSeek returned an invalid response shape") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("DeepSeek returned empty content")
        return content

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
