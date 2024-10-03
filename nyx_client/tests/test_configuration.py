from unittest.mock import patch

import pytest

from nyx_client.configuration import BaseNyxConfig, CohereNyxConfig, ConfigProvider, ConfigType, OpenAINyxConfig


@pytest.fixture(autouse=True)
def mock_dotenv_values():
    mock_values = {
        "DID_USER_DID": "mock_user_did",
        "DID_AGENT_DID": "mock_agent_did",
        "DID_AGENT_KEY_NAME": "mock_agent_key",
        "DID_AGENT_NAME": "mock_agent_name",
        "DID_AGENT_SECRET": "mock_agent_secret",
        "HOST_VERIFY_SSL": "true",
        "NYX_URL": "https://mock.nyx.url",
        "NYX_USERNAME": "mock_username",
        "NYX_EMAIL": "mock@email.com",
        "NYX_PASSWORD": "mock_password",
        "OPENAI_API_KEY": "mock_openai_key",
    }
    with patch("nyx_client.configuration.dotenv_values", return_value=mock_values):
        yield


def test_create_base_config():
    config = ConfigProvider.create_config(
        config_type=ConfigType.BASE, env_file=None, override_token="test_token", validate=True
    )
    assert isinstance(config, BaseNyxConfig)


def test_create_openai_config():
    config = ConfigProvider.create_config(
        config_type=ConfigType.OPENAI, api_key="valid_openai_key", env_file=None, override_token="", validate=True
    )
    assert config.api_key == "valid_openai_key"
    assert isinstance(config, OpenAINyxConfig)


def test_create_cohere_config():
    config = ConfigProvider.create_config(
        config_type=ConfigType.COHERE, api_key="valid_cohere_key", env_file=None, override_token="", validate=True
    )
    assert config.api_key == "valid_cohere_key"
    assert isinstance(config, CohereNyxConfig)


def test_create_openai_config_missing_api_key():
    with patch("nyx_client.configuration.os.getenv", return_value=""):
        with pytest.raises(OSError, match="Missing Required env var: OPENAI_API_KEY"):
            ConfigProvider.create_config(
                config_type=ConfigType.OPENAI, api_key=None, env_file=None, override_token="", validate=True
            )


def test_create_cohere_config_missing_api_key():
    with patch("nyx_client.configuration.os.getenv", return_value=""):
        with pytest.raises(OSError, match="Missing Required env var: COHERE_API_KEY"):
            ConfigProvider.create_config(
                config_type=ConfigType.COHERE, api_key=None, env_file=None, override_token="", validate=True
            )


def test_create_unknown_config():
    with pytest.raises(ValueError, match="Unknown config type: unknown"):
        ConfigProvider.create_config(
            config_type="unknown",  # Invalid config type
            env_file=None,
            override_token="",
            validate=True,
        )
