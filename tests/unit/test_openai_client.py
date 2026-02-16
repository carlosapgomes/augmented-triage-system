from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from triage_automation.infrastructure.llm.openai_client import (
    OpenAiChatCompletionsClient,
    OpenAiHttpResponse,
)


@dataclass
class RecordingTransport:
    body: bytes | None = None
    request_count: int = 0

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: float,
    ) -> OpenAiHttpResponse:
        _ = method, url, headers, timeout_seconds
        self.request_count += 1
        self.body = body
        return OpenAiHttpResponse(
            status_code=200,
            body_bytes=json.dumps(
                {"choices": [{"message": {"content": "{\"ok\":true}"}}]}
            ).encode("utf-8"),
        )


@pytest.mark.asyncio
async def test_chat_completions_enforces_json_object_response_format() -> None:
    transport = RecordingTransport()
    client = OpenAiChatCompletionsClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        transport=transport,
    )

    await client.complete(system_prompt="sys", user_prompt="usr")

    assert transport.request_count == 1
    assert transport.body is not None
    payload = json.loads(transport.body.decode("utf-8"))
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_chat_completions_applies_temperature_for_non_gpt5_model() -> None:
    transport = RecordingTransport()
    client = OpenAiChatCompletionsClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        temperature=0.0,
        transport=transport,
    )

    await client.complete(system_prompt="sys", user_prompt="usr")

    assert transport.body is not None
    payload = json.loads(transport.body.decode("utf-8"))
    assert payload["temperature"] == 0.0


@pytest.mark.asyncio
async def test_chat_completions_omits_temperature_for_gpt5_models() -> None:
    transport = RecordingTransport()
    client = OpenAiChatCompletionsClient(
        api_key="sk-test",
        model="gpt-5-mini",
        temperature=0.0,
        transport=transport,
    )

    await client.complete(system_prompt="sys", user_prompt="usr")

    assert transport.body is not None
    payload = json.loads(transport.body.decode("utf-8"))
    assert "temperature" not in payload


@pytest.mark.asyncio
async def test_chat_completions_uses_json_schema_response_format_when_provided() -> None:
    transport = RecordingTransport()
    client = OpenAiChatCompletionsClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        response_schema_name="llm1_response",
        response_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        transport=transport,
    )

    await client.complete(system_prompt="sys", user_prompt="usr")

    assert transport.body is not None
    payload = json.loads(transport.body.decode("utf-8"))
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "llm1_response"
    assert payload["response_format"]["json_schema"]["strict"] is True


@pytest.mark.asyncio
async def test_chat_completions_normalizes_required_for_strict_json_schema() -> None:
    transport = RecordingTransport()
    client = OpenAiChatCompletionsClient(
        api_key="sk-test",
        model="gpt-4o-mini",
        response_schema_name="llm1_response",
        response_schema={
            "type": "object",
            "properties": {
                "patient": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": ["integer", "null"]},
                    },
                    "required": ["name"],
                }
            },
            "required": ["patient"],
        },
        transport=transport,
    )

    await client.complete(system_prompt="sys", user_prompt="usr")

    assert transport.body is not None
    payload = json.loads(transport.body.decode("utf-8"))
    schema = payload["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["patient"]
    assert schema["properties"]["patient"]["required"] == ["name", "age"]
