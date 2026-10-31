import asyncio
from typing import Any
from urllib.parse import urlparse

import httpx

APPROVED_PROVIDER_HOSTS: frozenset[str] = frozenset(
    {
        "api.openai.com",
        "openrouter.ai",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
        "api.deepseek.com",
        "api.together.xyz",
        "api.groq.com",
        "api.mistral.ai",
        "api.fireworks.ai",
    }
)


class SSRFProtectionError(ValueError):
    """Raised when an outbound request attempts to target a non-approved host or non-HTTPS scheme."""


def validate_outbound_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SSRFProtectionError(f"Blocked non-HTTPS outbound request scheme: {parsed.scheme}")
    hostname = (parsed.hostname or "").lower()
    if hostname not in APPROVED_PROVIDER_HOSTS:
        raise SSRFProtectionError(
            f"Blocked outbound request to unapproved host '{hostname}'. "
            "Only official AI provider API domains are allowed."
        )


class SafeConnectorHttpClient:
    """
    HTTPX wrapper with:
    - Strict SSRF host allowlist enforcement
    - Strict timeouts (connect=5s, read=15s)
    - Exponential backoff for HTTP 429 and transient 5xx errors
    - Zero credential logging
    """

    def __init__(self, timeout_seconds: float = 15.0, max_retries: int = 3) -> None:
        self.timeout = httpx.Timeout(timeout_seconds, connect=5.0)
        self.max_retries = max_retries

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        validate_outbound_url(url)

        attempt = 0
        last_exc: Exception | None = None
        async with httpx.AsyncClient(
            timeout=self.timeout, follow_redirects=False
        ) as client:
            while attempt < self.max_retries:
                attempt += 1
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        params=params,
                    )
                    if response.status_code in (429, 502, 503, 504) and attempt < self.max_retries:
                        backoff = 0.5 * (2 ** (attempt - 1))
                        await asyncio.sleep(backoff)
                        continue
                    return response
                except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
                    last_exc = exc
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * (2 ** (attempt - 1)))
                        continue
                    raise
        if last_exc:
            raise last_exc
        raise RuntimeError("Request failed after retries")
