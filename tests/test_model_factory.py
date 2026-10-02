from pathlib import Path

import pytest

import impressions.core.model_factory as model_factory
from impressions.core import create_model_client as public_create_model_client
from impressions.core.config import load_project_config
from impressions.core.model_client import EchoModelClient, ModelClient, ModelRequest
from impressions.core.model_factory import create_model_client


CONFIG_TEMPLATE = """\
version = 1

[paths]
tasks = "tasks"
reports = "reports"

[model]
provider = "{provider}"
model = "test-model"
timeout = 15

[credentials]
api_key_env = "TEST_API_KEY"
"""


def configured_project(tmp_path: Path, provider: str = "openai"):
    (tmp_path / "impressions.toml").write_text(
        CONFIG_TEMPLATE.format(provider=provider), encoding="utf-8"
    )
    return load_project_config(tmp_path)


class FakeProviderClient:
    """Stand-in for provider SDK clients; records constructor arguments."""

    def __init__(self, api_key: str, model: str, timeout: float | None = None):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout


@pytest.fixture(autouse=True)
def patch_provider_sdk_clients(monkeypatch):
    monkeypatch.setattr(model_factory, "OpenAIModelClient", FakeProviderClient)
    monkeypatch.setattr(model_factory, "AnthropicModelClient", FakeProviderClient)
    monkeypatch.setattr(model_factory, "GeminiModelClient", FakeProviderClient)
    monkeypatch.setattr(model_factory, "MetaModelClient", FakeProviderClient)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini", "meta"])
def test_create_model_client_dispatches_configured_provider(tmp_path, provider):
    client = create_model_client(
        configured_project(tmp_path, provider=provider), {"TEST_API_KEY": "test-key"}
    )

    assert isinstance(client, FakeProviderClient)
    assert client.api_key == "test-key"
    assert client.model == "test-model"
    assert client.timeout == 15.0


def test_create_model_client_returns_echo_fallback_without_api_key(tmp_path):
    client = create_model_client(configured_project(tmp_path), {})

    assert isinstance(client, EchoModelClient)


@pytest.mark.parametrize("provider", ["openai", "anthropic", "gemini", "meta"])
def test_create_model_client_returns_echo_fallback_for_blank_api_key(
    tmp_path, provider
):
    client = create_model_client(
        configured_project(tmp_path, provider=provider), {"TEST_API_KEY": "   "}
    )

    assert isinstance(client, EchoModelClient)


def test_echo_fallback_client_implements_model_client_protocol(tmp_path):
    client: ModelClient = create_model_client(configured_project(tmp_path), {})

    response = client.generate(ModelRequest(prompt="Say hello."))

    assert response.text == "Say hello."
    assert response.model == "echo"


def test_create_model_client_exports_from_core_package():
    assert public_create_model_client is create_model_client
