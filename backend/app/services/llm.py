"""Thin client for any OpenAI-compatible chat completions endpoint."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import Settings
from app.schemas import Message


class LLMError(RuntimeError):
    pass


def _payload(settings: Settings, messages: list[Message], stream: bool) -> dict[str, Any]:
    return {
        "model": settings.llm_model,
        "stream": stream,
        "messages": [
            {"role": "system", "content": settings.system_prompt},
            *({"role": m.role, "content": m.content} for m in messages),
        ],
    }


def _headers(settings: Settings) -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.llm_api_key}"}


async def complete(settings: Settings, messages: list[Message]) -> str:
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        try:
            res = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                headers=_headers(settings),
                json=_payload(settings, messages, stream=False),
            )
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM endpoint unreachable: {exc}") from exc
        if res.status_code >= 400:
            raise LLMError(f"LLM returned {res.status_code}: {res.text[:300]}")
        try:
            return res.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise LLMError("Malformed LLM response") from exc


async def stream(settings: Settings, messages: list[Message]) -> AsyncIterator[str]:
    """Yield text deltas. Raises LLMError before the first token on failure."""
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                headers=_headers(settings),
                json=_payload(settings, messages, stream=True),
            ) as res:
                if res.status_code >= 400:
                    body = (await res.aread()).decode(errors="replace")
                    raise LLMError(f"LLM returned {res.status_code}: {body[:300]}")
                async for line in res.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        return
                    try:
                        delta = json.loads(data)["choices"][0]["delta"]
                    except (KeyError, IndexError, ValueError):
                        continue
                    if text := delta.get("content"):
                        yield text
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM endpoint unreachable: {exc}") from exc
