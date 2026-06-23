import asyncio
import httpx
import json
from typing import Any, AsyncGenerator, Optional

from config import LLM_PROVIDER, OLLAMA_HOST, GEMINI_API_KEY


_RETRYABLE_STATUSES = (429, 500, 502, 503, 504)
_MAX_RETRIES = 5
_BASE_DELAY = 2.0


class UnifiedLLMClient:
    """
    Unified Async LLM Client that dynamically routes requests to either
    Ollama (local) or Google AI Studio Gemini API (cloud, via the OpenAI-compatible endpoint).
    """

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or LLM_PROVIDER
        self.host = (host or OLLAMA_HOST).rstrip("/")
        self.model = model
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"

    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        timeout: float = 120.0,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response token-by-token from either local Ollama or cloud Gemini API.
        """
        target_model = model or self.model

        if self.provider == "gemini":
            # Streaming via OpenAI Compatibility endpoint on Google Generative Language v1beta
            headers = {
                "Authorization": f"Bearer {self.gemini_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.gemini_base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        data_str = line[len("data:"):].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        else:
            # Standard local Ollama streaming API
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": True,
            }

            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.host}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if data.get("done", False):
                            break

    async def _post_with_retry(
        self,
        url: str,
        payload: dict,
        headers: Optional[dict],
        timeout: float,
    ) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in _RETRYABLE_STATUSES or attempt == _MAX_RETRIES:
                    raise
            except httpx.RequestError:
                if attempt == _MAX_RETRIES:
                    raise
            await asyncio.sleep(_BASE_DELAY * (2 ** attempt))

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        timeout: float = 120.0,
        response_format: Optional[dict] = None,
    ) -> str:
        target_model = model or self.model

        if self.provider == "gemini":
            headers = {
                "Authorization": f"Bearer {self.gemini_api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
            }
            if response_format:
                payload["response_format"] = response_format
            data = await self._post_with_retry(
                f"{self.gemini_base_url}/v1/chat/completions",
                payload,
                headers,
                timeout,
            )
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
        }
        if response_format:
            if response_format.get("type") == "json_schema":
                payload["format"] = response_format["json_schema"]["schema"]
            elif response_format.get("type") == "json_object":
                payload["format"] = "json"

        data = await self._post_with_retry(
            f"{self.host}/api/chat",
            payload,
            None,
            timeout,
        )
        return data.get("message", {}).get("content", "")

    async def is_available(self) -> bool:
        """Check if LLM backend provider is alive and responding."""
        if self.provider == "gemini":
            if not self.gemini_api_key or self.gemini_api_key.startswith("YOUR_"):
                return False
            try:
                # Query Google API models list to verify key validation and connection
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_api_key}"
                    )
                    return r.status_code == 200
            except Exception:
                return False
        else:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{self.host}/api/tags")
                    return r.status_code == 200
            except httpx.ConnectError:
                return False


# Maintain backward compatibility with type annotations in main.py, agent.py and compiler.py
OllamaClient = UnifiedLLMClient
