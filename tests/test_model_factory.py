from pathlib import Path

import pytest

from impressions.core import create_model_client as public_create_model_client
from impressions.core.config import ConfigError, load_project_config
from impressions.core.model_factory import create_model_client
from impressions.core.openai_client import OpenAIModelClient


CONFIG = """\
version = 1

[paths]
tasks = "tasks"
reports = "reports"

[model]
provider = "openai"
model = "gpt-5"
timeout = 15

[credentials]
api_key_env = "TEST_OPENAI_API_KEY"
"""


def configured_project(tmp_path: Path):
    (tmp_path / "impressions.toml").write_text(CONFIG, encoding="utf-8")
    return load_project_config(tmp_path)


def test_create_model_client_uses_configured_openai_provider(tmp_path):
    client = create_model_client(
        configured_project(tmp_path), {"TEST_OPENAI_API_KEY": "test-key"}
    )

    assert isinstance(client, OpenAIModelClient)
    assert client.model == "gpt-5"


def test_create_model_client_uses_configured_timeout(tmp_path):
    client = create_model_client(
        configured_project(tmp_path), {"TEST_OPENAI_API_KEY": "test-key"}
    )

    assert client._client.timeout == 15.0


def test_create_model_client_rejects_missing_api_key(tmp_path):
    with pytest.raises(ConfigError, match="TEST_OPENAI_API_KEY"):
        create_model_client(configured_project(tmp_path), {})


def test_create_model_client_exports_from_core_package():
    assert public_create_model_client is create_model_client
