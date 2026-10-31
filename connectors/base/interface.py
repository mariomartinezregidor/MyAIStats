from abc import ABC, abstractmethod
from datetime import datetime

from connectors.base.http_client import SafeConnectorHttpClient
from connectors.base.types import (
    ConnectionTestResult,
    ConnectorCredentials,
    NormalizedBalanceSnapshot,
    NormalizedCostRecord,
    NormalizedModelPrice,
    NormalizedUsageRecord,
    ProviderCapabilities,
)


class BaseConnector(ABC):
    provider_id: str
    provider_name: str
    category_priority: int
    api_base_url: str
    docs_url: str
    auth_instructions: str

    def __init__(self, http_client: SafeConnectorHttpClient | None = None) -> None:
        self.http = http_client or SafeConnectorHttpClient()

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Returns verified capabilities supported by this provider's official API."""

    @abstractmethod
    async def test_connection(self, creds: ConnectorCredentials) -> ConnectionTestResult:
        """Tests the API key against an official lightweight endpoint."""

    async def fetch_usage(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedUsageRecord]:
        """Fetches normalized token usage records if supported by official API."""
        return []

    async def fetch_costs(
        self,
        creds: ConnectorCredentials,
        start_time: datetime,
        end_time: datetime,
    ) -> list[NormalizedCostRecord]:
        """Fetches official actual billed costs if supported by official API."""
        return []

    async def fetch_balance(
        self,
        creds: ConnectorCredentials,
    ) -> NormalizedBalanceSnapshot:
        """Fetches confirmed account balance/credits or returns is_supported=False."""
        caps = self.get_capabilities()
        return NormalizedBalanceSnapshot(
            available_balance=None,
            is_supported=caps.supports_balance,
            status_note="Balance endpoint is not exposed by this provider's official API.",
        )

    async def fetch_model_pricing(
        self,
        creds: ConnectorCredentials | None = None,
    ) -> list[NormalizedModelPrice]:
        """Fetches official model pricing catalog (from live API or verified official catalog)."""
        return []
