import asyncio
import httpx
import json
from typing import Any, AsyncGenerator, Optional

from config import LLM_PROVIDER, OLLAMA_HOST, GEMINI_API_KEY, OPENAI_API_KEY, OPENAI_BASE_URL, REQUEST_TIMEOUT


_RETRYABLE_STATUSES = (429, 500, 502, 503, 504)
_MAX_RETRIES = 5
_BASE_DELAY = 2.0


class UnifiedLLMClient:
    """
    Unified Async LLM Client that dynamically routes requests to either
    Ollama (local) or Google AI Studio Gemini API (cloud, via the OpenAI-compatible endpoint).

    Uses a persistent httpx.AsyncClient for connection pooling. Call `aclose()` when done,
    or use as an async context manager.
    """

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None, api_key: Optional[str] = None):
        self.provider = provider or LLM_PROVIDER
        self.host = (host or OLLAMA_HOST).rstrip("/")
        self.model = model
        self.gemini_api_key = api_key if (api_key and self.provider == "gemini") else GEMINI_API_KEY
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        self.openai_api_key = api_key if (api_key and self.provider == "openai") else OPENAI_API_KEY
        self.openai_base_url = (OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._http: Optional[httpx.AsyncClient] = None

    def _get_http(self, timeout: float = REQUEST_TIMEOUT) -> httpx.AsyncClient:
        """Get or create the shared httpx client with connection pooling."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(timeout, connect=10.0),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._http

    async def aclose(self) -> None:
        """Close provider and pipeline-owned auxiliary HTTP clients."""
        rag_client = getattr(self, "_simulation_rag_client", None)
        if rag_client is not None:
            await rag_client.close()
            self._simulation_rag_client = None
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()

    async def chat_stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        timeout: float = REQUEST_TIMEOUT,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response token-by-token with retry on transient errors.
        """
        target_model = model or self.model
        client = self._get_http(timeout)

        for attempt in range(_MAX_RETRIES + 1):
            try:
                if self.provider == "gemini":
                    async for chunk in self._stream_gemini(client, target_model, messages, timeout):
                        yield chunk
                elif self.provider == "openai":
                    async for chunk in self._stream_openai(client, target_model, messages, timeout):
                        yield chunk
                else:
                    async for chunk in self._stream_ollama(client, target_model, messages, timeout):
                        yield chunk
                return  # Success — exit retry loop
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in _RETRYABLE_STATUSES or attempt == _MAX_RETRIES:
                    raise
            except httpx.RequestError:
                if attempt == _MAX_RETRIES:
                    raise
            await asyncio.sleep(_BASE_DELAY * (2 ** attempt))

    async def _stream_gemini(
        self,
        client: httpx.AsyncClient,
        model: str,
        messages: list[dict],
        timeout: float,
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.gemini_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "stream": True}

        async with client.stream(
            "POST",
            f"{self.gemini_base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
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
                        content = choices[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

    async def _stream_openai(
        self,
        client: httpx.AsyncClient,
        model: str,
        messages: list[dict],
        timeout: float,
    ) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": model, "messages": messages, "stream": True}

        async with client.stream(
            "POST",
            f"{self.openai_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
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
                        content = choices[0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    continue

    async def _stream_ollama(
        self,
        client: httpx.AsyncClient,
        model: str,
        messages: list[dict],
        timeout: float,
    ) -> AsyncGenerator[str, None]:
        payload = {"model": model, "messages": messages, "stream": True}

        async with client.stream(
            "POST",
            f"{self.host}/api/chat",
            json=payload,
            timeout=timeout,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
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
        """POST with exponential backoff retry on transient errors."""
        client = self._get_http(timeout)

        for attempt in range(_MAX_RETRIES + 1):
            try:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=timeout
                )
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
        timeout: float = REQUEST_TIMEOUT,
        response_format: Optional[dict] = None,
    ) -> str:
        target_model = model or self.model

        if self.provider in ("gemini", "openai"):
            if self.provider == "gemini":
                headers = {
                    "Authorization": f"Bearer {self.gemini_api_key}",
                    "Content-Type": "application/json",
                }
                url = f"{self.gemini_base_url}/v1/chat/completions"
            else:
                headers = {
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                }
                url = f"{self.openai_base_url}/chat/completions"

            payload = {
                "model": target_model,
                "messages": messages,
                "stream": False,
            }
            if response_format:
                payload["response_format"] = response_format
            data = await self._post_with_retry(url, payload, headers, timeout)
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

        # Ollama
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
                client = self._get_http(5.0)
                r = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    headers={"x-goog-api-key": self.gemini_api_key},
                    timeout=5.0,
                )
                return r.status_code == 200
            except Exception:
                return False
        elif self.provider == "openai":
            if not self.openai_api_key or self.openai_api_key.startswith("YOUR_"):
                return False
            try:
                client = self._get_http(5.0)
                r = await client.get(
                    f"{self.openai_base_url}/models",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    timeout=5.0,
                )
                return r.status_code == 200
            except Exception:
                return False
        else:
            try:
                client = self._get_http(5.0)
                r = await client.get(f"{self.host}/api/tags", timeout=5.0)
                return r.status_code == 200
            except httpx.ConnectError:
                return False


# Maintain backward compatibility with type annotations in main.py, agent.py and compiler.py
OllamaClient = UnifiedLLMClient
