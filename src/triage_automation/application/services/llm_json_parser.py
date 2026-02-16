"""Utilities to robustly decode JSON objects returned by LLMs."""

from __future__ import annotations

import json
import re
from typing import cast

_FENCED_JSON_PATTERN = re.compile(
    r"```(?:json)?\s*(\{[\s\S]*\})\s*```",
    flags=re.IGNORECASE,
)


class LlmJsonParseError(ValueError):
    """Raised when no valid JSON object can be decoded from model output."""


def decode_llm_json_object(raw_response: str) -> dict[str, object]:
    """Decode first valid JSON object from raw model text.

    Parsing strategy:
    1. Direct JSON decode.
    2. Decode JSON inside fenced code block.
    3. Decode first JSON object found within surrounding text.
    """

    direct = _decode_json_object(raw_response.strip())
    if direct is not None:
        return direct

    fenced = _extract_fenced_json(raw_response)
    if fenced is not None:
        fenced_decoded = _decode_json_object(fenced)
        if fenced_decoded is not None:
            return fenced_decoded

    embedded = _extract_first_embedded_json_object(raw_response)
    if embedded is not None:
        return embedded

    raise LlmJsonParseError("No valid JSON object found in LLM response")


def _decode_json_object(text: str) -> dict[str, object] | None:
    if not text:
        return None
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    return cast("dict[str, object]", decoded)


def _extract_fenced_json(raw_response: str) -> str | None:
    match = _FENCED_JSON_PATTERN.search(raw_response)
    if match is None:
        return None
    return match.group(1).strip()


def _extract_first_embedded_json_object(raw_response: str) -> dict[str, object] | None:
    decoder = json.JSONDecoder()
    for index, value in enumerate(raw_response):
        if value != "{":
            continue
        fragment = raw_response[index:]
        try:
            decoded, _ = decoder.raw_decode(fragment)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return cast("dict[str, object]", decoded)
    return None
