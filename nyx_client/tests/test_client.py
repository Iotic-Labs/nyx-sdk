from unittest.mock import MagicMock, patch

import pytest
import requests
from requests_mock import ANY

from nyx_client.client import NyxClient
from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data


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
    config = BaseNyxConfig.from_env(env_file=None, override_token="test_token")
    yield config


@pytest.fixture
def nyx_client(mock_config):
    with patch("nyx_client.client.NyxClient._setup"):
        client = NyxClient(config=mock_config)
        client.org = "test"
        yield client


def test_nyx_client_initialization(nyx_client, mock_config):
    assert isinstance(nyx_client, NyxClient)
    assert nyx_client.config == mock_config


def test_nyx_post(requests_mock, nyx_client):
    rsp_data = {"key": "value"}
    requests_mock.post("https://mock.nyx.url/api/portal/test_endpoint", json=rsp_data)

    result = nyx_client._nyx_post("test_endpoint", {"data": "test"})
    assert result == rsp_data
    assert requests_mock.call_count == 1


def test_nyx_get(requests_mock, nyx_client):
    rsp_data = {"key": "value"}
    requests_mock.get("https://mock.nyx.url/api/portal/test_endpoint", json=rsp_data)

    result = nyx_client._nyx_get("test_endpoint")
    assert result == rsp_data
    assert requests_mock.call_count == 1


def test_delete_data(requests_mock, nyx_client):
    name = "test_data"

    requests_mock.delete(f"https://mock.nyx.url/api/portal/products/{name}")

    data = Data(
        url="http://test.com",
        title="Test",
        org="test_org",
        name=name,
        description="",
        content_type="application/poney",
        creator="me",
        categories=["ai"],
        genre="ai",
    )
    nyx_client.delete_data(data)
    assert requests_mock.call_count == 1


def test_nyx_post_network_error(requests_mock, nyx_client):
    requests_mock.post(ANY, exc=requests.ConnectionError)

    with pytest.raises(requests.ConnectionError):
        nyx_client._nyx_post("test_endpoint", {"data": "test"})


def test_nyx_get_network_error(requests_mock, nyx_client):
    requests_mock.get(ANY, exc=requests.ConnectionError)

    with pytest.raises(requests.ConnectionError):
        nyx_client._nyx_get("test_endpoint")


def test_authorise_invalid_credentials(nyx_client):
    with patch.object(nyx_client, "_nyx_post") as mock_post:
        mock_post.side_effect = requests.HTTPError("401 Unauthorized")
        with pytest.raises(requests.HTTPError):
            nyx_client._authorise()


def test_get_all_categories_empty_result(nyx_client):
    with patch.object(nyx_client, "_nyx_get", return_value=[]):
        result = nyx_client.categories()
        assert result == []


@patch.object(NyxClient, "_nyx_post")
def test_create_data_with_with_size(mock_nyx_post, nyx_client):
    mock_nyx_post.json.return_value = {}
    result = nyx_client.create_data(
        content_type="text/csv",
        description="foo",
        name="a_name",
        title="a_title",
        size=100,
        download_url="http://here.com",
        categories=[],
        genre="x",
    )

    assert result.size == 100


@patch.object(NyxClient, "_nyx_post")
def test_create_data_with_description(mock_nyx_post, nyx_client):
    mock_nyx_post.json.return_value = {}
    result = nyx_client.create_data(
        content_type="text/csv",
        description="foo",
        name="a_name",
        size=10,
        title="a_title",
        download_url="http://here.com",
        categories=[],
        genre="x",
    )

    assert result.description == "foo"


@patch.object(NyxClient, "_nyx_post")
def test_create_product_invalid_input(mock_nyx_post, nyx_client):
    mock_nyx_post.side_effect = requests.HTTPError("400 Bad Request")
    with pytest.raises(requests.HTTPError):
        nyx_client.create_data(
            name="",
            title="Test Data",
            description="A test data",
            size=1000,
            genre="Test",
            categories=["Test"],
            download_url="http://example.com/test.zip",
            content_type="text/csv",
        )


def test_delete_data_not_found(requests_mock, nyx_client):
    name = "non_existent"

    requests_mock.delete(f"https://mock.nyx.url/api/portal/products/{name}", status_code=404)

    data = Data(
        url="http://test.com",
        title="Test",
        org="test_org",
        name=name,
        description="",
        content_type="application/poney",
        creator="me",
        categories=["ai"],
        genre="ai",
    )
    with pytest.raises(requests.HTTPError):
        nyx_client.delete_data(data)


def test_sparql_query_constructs_data(nyx_client):
    # Mock response from _sparql_query
    mock_response = [
        {
            "accessURL": "https://example.com/access",
            "title": "Test Data",
            "name": "test_data",
            "contentType": "application/json",
            "creator": "TestCreator",
            "size": 321,
            "description": "Some description of sorts",
            "categories": ["ai"],
            "genre": "ai",
        }
    ]

    # Patch the _sparql_query method to return our mock response
    with patch.object(nyx_client, "_nyx_get", return_value=mock_response):
        # Call a method that uses _sparql_query and constructs Data
        # For this example, we'll use get_all_datasets, but you can use any method that fits
        data = nyx_client.get_data()

        # Assert that we got a list with one data element
        assert len(data) == 1

        # Assert that the Data has the correct attributes
        assert data[0].url == f"https://example.com/access?buyer_org={nyx_client.org}"
        assert data[0].title == "Test Data"
        assert data[0].name == "test_data"
        assert data[0].content_type == "application/json"
        assert data[0].size == 321
        assert data[0].creator == "TestCreator"
        assert data[0].description == "Some description of sorts"
