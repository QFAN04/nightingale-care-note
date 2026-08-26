import asyncio
import json

import httpx
import pytest

from app.ai.providers.deepseek import DeepSeekScribeProvider, ProviderResponseError
from app.ai.providers.fake import FakeScribeProvider


def test_fake_provider_is_deterministic_and_records_calls() -> None:
    raw_response = '{"summary":"Stable response"}'
    provider = FakeScribeProvider(raw_response=raw_response)

    result = asyncio.run(
        provider.generate(
            system_prompt="Return JSON only.",
            transcript="Patient describes chest pressure.",
        )
    )

    assert result == raw_response
    assert provider.calls == [
        {
            "system_prompt": "Return JSON only.",
            "transcript": "Patient describes chest pressure.",
        }
    ]


def test_deepseek_provider_sends_json_mode_request() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers["authorization"]
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"summary":"Supported"}'}}
                ]
            },
        )

    client = httpx.AsyncClient(
        base_url="https://api.deepseek.com",
        transport=httpx.MockTransport(handler),
    )
    provider = DeepSeekScribeProvider(
        api_key="local-test-key",
        model="deepseek-v4-pro",
        client=client,
    )

    try:
        result = asyncio.run(
            provider.generate(
                system_prompt="Return a JSON object.",
                transcript="Redacted transcript",
            )
        )
    finally:
        asyncio.run(client.aclose())

    assert result == '{"summary":"Supported"}'
    assert captured["authorization"] == "Bearer local-test-key"
    assert captured["path"] == "/chat/completions"
    assert captured["payload"] == {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": "Return a JSON object."},
            {"role": "user", "content": "Redacted transcript"},
        ],
        "response_format": {"type": "json_object"},
        "stream": False,
        "max_tokens": 2048,
    }


def test_deepseek_provider_rejects_empty_content() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": ""}}]})

    client = httpx.AsyncClient(
        base_url="https://api.deepseek.com",
        transport=httpx.MockTransport(handler),
    )
    provider = DeepSeekScribeProvider(api_key="local-test-key", client=client)

    try:
        with pytest.raises(ProviderResponseError, match="empty content"):
            asyncio.run(
                provider.generate(system_prompt="Return JSON.", transcript="Text")
            )
    finally:
        asyncio.run(client.aclose())
