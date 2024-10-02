import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models import BaseChatModel

from nyx_client.configuration import BaseNyxConfig
from nyx_client.extensions.langchain import NyxLangChain


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


@pytest.fixture
def mock_config():
    return BaseNyxConfig(env_file=None, override_token="test_token", validate=False)


@pytest.fixture
def mock_llm():
    return MagicMock(spec=BaseChatModel)


@pytest.fixture
def mock_host_client():
    with patch("nyx_client.client.HostClient") as mock:
        yield mock


@pytest.fixture
def nyx_langchain(mock_config, mock_llm, mock_host_client):
    with patch("nyx_client.extensions.langchain.NyxClient._setup"):
        with patch("nyx_client.client.requests.post"):
            with patch("nyx_client.client.requests.get"):
                client = NyxLangChain(config=mock_config, llm=mock_llm)
                client.host_client = mock_host_client
                return client


def test_nyx_langchain_initialization(nyx_langchain, mock_config, mock_llm):
    assert isinstance(nyx_langchain, NyxLangChain)
    assert nyx_langchain.config == mock_config
    assert nyx_langchain.llm == mock_llm


@pytest.mark.skip
@patch("nyx_client.extensions.langchain.Parser.dataset_as_db")
@patch("nyx_client.extensions.langchain.SQLDatabase")
@patch("nyx_client.extensions.langchain.SQLDatabaseToolkit")
@patch("nyx_client.extensions.langchain.create_react_agent")
def test_query(mock_create_react_agent, mock_toolkit, mock_sqldb, mock_dataset_as_db, nyx_langchain):
    # Mock the necessary components
    mock_engine = MagicMock()
    mock_dataset_as_db.return_value = mock_engine
    mock_db = MagicMock()
    mock_sqldb.return_value = mock_db
    mock_tools = MagicMock()
    mock_toolkit.return_value.get_tools.return_value = mock_tools
    mock_agent_executor = MagicMock()
    mock_create_react_agent.return_value = mock_agent_executor

    # Mock the stream method to return an iterable
    mock_agent_executor.stream.return_value = iter([{"messages": [MagicMock(content="Intermediate content")]}])

    # Mock get_subscribed_datasets
    with patch.object(
        nyx_langchain,
        "get_subscribed_datasets",
        return_value=[
            MagicMock(
                name="test_data", access_url="http://test.com", title="Test", org="test_org", mediaType="text/csv"
            )
        ],
    ):
        # Test the query method
        result = nyx_langchain.query("Test query")

        # Assertions
        assert result == "Intermediate content"
        mock_dataset_as_db.assert_called_once()
        mock_sqldb.assert_called_once_with(engine=mock_engine)
        mock_toolkit.assert_called_once()
        mock_create_react_agent.assert_called_once()
        mock_agent_executor.stream.assert_called_once()


@pytest.mark.skip
@patch("nyx_client.extensions.langchain.os.remove")
def test_query_with_sqlite_file(mock_remove, nyx_langchain):
    with patch.object(nyx_langchain, "_federated_sparql_query") as mock_query:
        mock_query.return_value = [
            {"name": "data1", "downloadUrl": "url1", "title": "Data 1"},
            {"name": "data2", "downloadUrl": "url2", "title": "Data 2"},
        ]

        with patch("nyx_client.extensions.langchain.Parser.dataset_as_db") as mock_dataset_as_db:
            with patch("nyx_client.extensions.langchain.SQLDatabase") as mock_sqldb:
                with patch("nyx_client.extensions.langchain.SQLDatabaseToolkit") as mock_toolkit:
                    with patch("nyx_client.extensions.langchain.create_react_agent") as mock_create_react_agent:
                        mock_agent_executor = MagicMock()
                        mock_create_react_agent.return_value = mock_agent_executor
                        mock_agent_executor.stream.return_value = iter(
                            [{"messages": [MagicMock(content="Result content")]}]
                        )

                        result = nyx_langchain.query("Test query", sqlite_file="test.db")

                        assert result == "Result content"
                        mock_remove.assert_called_once_with("test.db")
