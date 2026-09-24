"""LLM-assisted suggestions via the OpenAI chat API (plain httpx, no SDK).

Kept dependency-free on purpose: the rest of the backend runs on
httpx/pydantic already. Without OPENAI_API_KEY configured every call
fails closed with a clear error instead of pretending to work.
"""

import json
from typing import Any

import httpx

API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
BATCH_SIZE = 20


def build_prompt(instructions: str, labels: list[str], texts: list[str]) -> list[dict]:
    allowed = ", ".join(f'"{l}"' for l in labels)
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    return [
        {
            "role": "system",
            "content": (
                "You label text for machine-learning datasets. "
                'Reply with JSON only: {"labels": [{"id": <number>, "label": <string>}, ...]}. '
                f"Every label must be exactly one of: {allowed}."
            ),
        },
        {
            "role": "user",
            "content": f"Guidelines: {instructions}\n\nTexts:\n{numbered}",
        },
    ]


def complete(
    api_key: str, model: str, instructions: str, labels: list[str], texts: list[str]
) -> list[dict]:
    """Call the chat API for one batch. Returns [{id, label}]."""
    resp = httpx.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": build_prompt(instructions, labels, texts),
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=60,
    )
    if resp.status_code == 401:
        raise ValueError("OpenAI rejected the API key (401). Check OPENAI_API_KEY.")
    if resp.status_code == 429:
        raise ValueError(
            "OpenAI rate limit hit (429). Try fewer items or wait a minute."
        )
    if resp.status_code >= 400:
        raise ValueError(f"OpenAI error {resp.status_code}: {resp.text[:200]}")
    try:
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        return data.get("labels", [])
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Could not parse model reply: {exc}")


def suggest_batch(
    api_key: str,
    model: str,
    instructions: str,
    labels: list[str],
    texts: list[str],
) -> dict[int, str]:
    """Suggest labels for many texts. Returns {index: label} for valid replies only."""
    out: dict[int, str] = {}
    allowed = set(labels)
    for start in range(0, len(texts), BATCH_SIZE):
        chunk = texts[start : start + BATCH_SIZE]
        for entry in complete(api_key, model, instructions, labels, chunk):
            try:
                idx = int(entry["id"]) - 1 + start
                label = str(entry["label"])
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= idx - start < len(chunk) and label in allowed:
                out[idx] = label
    return out


def result_to_suggestion(label: Any) -> dict:
    return {"label": label}
