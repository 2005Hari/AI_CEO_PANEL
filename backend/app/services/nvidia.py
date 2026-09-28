# backend/app/services/nvidia.py
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from app.core.config import settings

class NVIDIAInferenceService:
    def __init__(self):
        self.api_key = settings.NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model_name = settings.NVIDIA_MODEL
        self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        model: Optional[str] = None
    ) -> str:
        """
        Sends a chat completion request to the NVIDIA OpenAI-compatible API endpoint
        with automatic retries and exponential backoff for rate limits (HTTP 429) or transient errors.
        """
        # Reload key dynamically in case it was set after initialization
        api_key = settings.NVIDIA_API_KEY or self.api_key
        if not api_key:
            raise ValueError(
                "NVIDIA_API_KEY is not configured. Please set the NVIDIA_API_KEY "
                "environment variable in your backend/.env file."
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model or self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            # Some NVIDIA-hosted models (e.g. the Nemotron family) are reasoning
            # models that otherwise narrate their full chain-of-thought as plain
            # text in `content` before any real answer, which both breaks our
            # JSON-parsing prompts and can exhaust max_tokens before an answer is
            # even reached. Verified harmless no-op on non-reasoning models.
            "chat_template_kwargs": {"enable_thinking": False},
        }

        retries = 3
        backoff = 2.0  # seconds

        client = self.client
        for attempt in range(retries):
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=90.0
                )

                # Handle Rate Limits (HTTP 429)
                if response.status_code == 429:
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                    else:
                        raise HTTPException(
                            status_code=429,
                            detail="NVIDIA API rate limit exceeded. Please try again later."
                        )

                # Handle Server Errors
                if response.status_code >= 500:
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue

                # Other client errors (401, 403, 404, etc.) are permanent — fail immediately, no retry
                if 400 <= response.status_code < 500:
                    raise RuntimeError(
                        f"NVIDIA API request failed with status {response.status_code}: {response.text}"
                    )

                response.raise_for_status()
                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                else:
                    raise ValueError(f"Unexpected API response structure: {data}")

            except httpx.HTTPStatusError as e:
                if attempt < retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise RuntimeError(f"NVIDIA API request failed with status {e.response.status_code}: {e.response.text}")
            
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                if attempt < retries - 1:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise RuntimeError(f"NVIDIA API connection error: {str(e)}")

        raise RuntimeError("Failed to retrieve completion from NVIDIA API after retries.")

# Global instance of the service
nvidia_service = NVIDIAInferenceService()
