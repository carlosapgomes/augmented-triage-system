from __future__ import annotations

import pytest

from triage_automation.application.services.llm_json_parser import (
    LlmJsonParseError,
    decode_llm_json_object,
)


def test_decode_llm_json_object_accepts_plain_json() -> None:
    decoded = decode_llm_json_object('{"a":1,"b":"x"}')

    assert decoded == {"a": 1, "b": "x"}


def test_decode_llm_json_object_accepts_fenced_json() -> None:
    decoded = decode_llm_json_object("```json\n{\"a\":1}\n```")

    assert decoded == {"a": 1}


def test_decode_llm_json_object_accepts_embedded_json() -> None:
    decoded = decode_llm_json_object("Result:\n{\"a\":1,\"b\":2}\nThanks.")

    assert decoded == {"a": 1, "b": 2}


def test_decode_llm_json_object_raises_for_non_json_payload() -> None:
    with pytest.raises(LlmJsonParseError):
        decode_llm_json_object("not-json")
