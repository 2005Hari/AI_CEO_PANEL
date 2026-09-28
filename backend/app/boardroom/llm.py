"""Thin LLM helpers: JSON-tolerant completion on top of the NVIDIA service."""
import json
import re
from typing import Any, Dict, List, Optional

from app.services.nvidia import nvidia_service


class BoardroomParseError(Exception):
    """The model answered, but not with usable JSON."""


async def chat(messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 2048) -> str:
    return await nvidia_service.chat_completion(messages, temperature=temperature, max_tokens=max_tokens)


def extract_json(text: str) -> Optional[Any]:
    """Parse a JSON object from model output, tolerating fences and stray prose."""
    if not text:
        return None
    clean = text.strip()
    fence = re.match(r"^```[a-zA-Z]*\s*\n(.*?)\n?```\s*$", clean, re.DOTALL)
    if fence:
        clean = fence.group(1).strip()
    try:
        return json.loads(clean)
    except ValueError:
        pass
    start, end = clean.find("{"), clean.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(clean[start:end + 1])
        except ValueError:
            return None
    return None


async def complete_json(
    system: str,
    user: str,
    *,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    fallback_text_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Ask for a JSON object; retry once; optionally fall back to raw text under a key."""
    messages = [
        {"role": "system", "content": system + "\n\nRespond with ONE raw JSON object only: no markdown fences, no commentary."},
        {"role": "user", "content": user},
    ]
    last = ""
    for attempt in range(2):
        last = await chat(messages, temperature=temperature if attempt == 0 else 0.0, max_tokens=max_tokens)
        parsed = extract_json(last)
        if isinstance(parsed, dict):
            return parsed
    if fallback_text_key and last.strip():
        return {fallback_text_key: last.strip()}
    raise BoardroomParseError("Model did not return valid JSON")


async def complete_text(system: str, user: str, *, max_tokens: int = 3000, temperature: float = 0.4) -> str:
    return (await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
    )).strip()
