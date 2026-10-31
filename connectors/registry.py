"""Registry of all official AI provider connectors."""

from connectors.anthropic import AnthropicConnector
from connectors.base.interface import BaseConnector
from connectors.deepseek import DeepSeekConnector
from connectors.fireworks import FireworksConnector
from connectors.google import GoogleGeminiConnector
from connectors.groq import GroqConnector
from connectors.mistral import MistralConnector
from connectors.morph import MorphConnector
from connectors.openai import OpenAIConnector
from connectors.opencode import OpenCodeConnector
from connectors.openrouter import OpenRouterConnector
from connectors.refuseless import RefuselessConnector
from connectors.together import TogetherConnector

CONNECTOR_REGISTRY: dict[str, BaseConnector] = {
    "openai": OpenAIConnector(),
    "openrouter": OpenRouterConnector(),
    "anthropic": AnthropicConnector(),
    "google": GoogleGeminiConnector(),
    "deepseek": DeepSeekConnector(),
    "together": TogetherConnector(),
    "groq": GroqConnector(),
    "mistral": MistralConnector(),
    "fireworks": FireworksConnector(),
    "morph": MorphConnector(),
    "refuseless": RefuselessConnector(),
    "opencode": OpenCodeConnector(),
}


def get_connector(provider_id: str) -> BaseConnector:
    connector = CONNECTOR_REGISTRY.get(provider_id.lower())
    if not connector:
        raise KeyError(f"Unsupported provider '{provider_id}'")
    return connector


def list_connectors() -> list[BaseConnector]:
    return sorted(CONNECTOR_REGISTRY.values(), key=lambda c: (c.category_priority, c.provider_name))
