from unittest.mock import MagicMock, patch

import pytest
import requests
from requests_mock import ANY

from nyx_client.client import NyxClient, SparqlResultType
from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data


@pytest.fixture(autouse=True)
def mock_dotenv_values():
    mock_values = {
        "NYX_URL": "https://mock.nyx.url",
        "NYX_EMAIL": "mock@email.com",
        "NYX_PASSWORD": "mock_password",
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


# Minimum response fields necessary for create response to work
MIN_CREATE_DATA_RESPONSE = {
    "description": "something",
    "genre": "whatever",
    "categories": (),
    "size": 101,
    "accessURL": "http://here.com",
}


def test_create_data_with_with_size(requests_mock, nyx_client):
    requests_mock.post("https://mock.nyx.url/api/portal/products", json=MIN_CREATE_DATA_RESPONSE)
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

    assert result.size == MIN_CREATE_DATA_RESPONSE["size"]


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
    # Mock response from "get data" endpoint
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


def test_sparql_query(requests_mock, nyx_client):
    query = "SELECT * WHERE { ?s ?p ?o }"
    expected_response = '{"results": {"bindings": []}}'
    requests_mock.post(
        "https://mock.nyx.url/api/portal/meta/sparql/global",
        text=expected_response,
        headers={"Content-Type": "application/sparql-results+json"},
    )
    requests_mock.post(
        "https://mock.nyx.url/api/portal/meta/sparql/local",
        text=expected_response,
        headers={"Content-Type": "application/sparql-results+json"},
    )

    result = nyx_client.sparql_query(query)
    assert result == expected_response

    # Test with different result type
    result = nyx_client.sparql_query(query, result_type=SparqlResultType.SPARQL_XML, local_only=True)
    assert requests_mock.last_request.headers["Accept"] == SparqlResultType.SPARQL_XML.value
    assert "local" in requests_mock.last_request.url


def test_search(requests_mock, nyx_client):
    mock_response = [
        {
            "name": "test_dataset",
            "title": "Test Dataset",
            "description": "Test Description",
            "accessURL": "https://example.com/data",
            "contentType": "text/csv",
            "creator": "test_creator",
            "categories": ["test_category"],
            "genre": "test_genre",
        }
    ]

    requests_mock.get("https://mock.nyx.url/api/portal/meta/search/text", json=mock_response)

    result = nyx_client.search(
        categories=["test_category"],
        genre="test_genre",
        creator="test_creator",
        text="test",
        license="MIT",
        content_type="text/csv",
        subscription_state="all",
        timeout=5,
        local_only=True,
    )

    assert len(result) == 1
    assert isinstance(result[0], Data)
    assert result[0].name == "test_dataset"

    # Verify query parameters
    last_request = requests_mock.last_request
    assert "category=test_category" in last_request.url
    assert "genre=test_genre" in last_request.url
    assert "creator=test_creator" in last_request.url
    assert "text=test" in last_request.url
    assert "license=MIT" in last_request.url
    assert "contentType=text%2Fcsv" in last_request.url
    assert "include=all" in last_request.url
    assert "timeout=5" in last_request.url
    assert "scope=local" in last_request.url


def test_my_subscriptions(nyx_client):
    with patch.object(nyx_client, "get_data") as mock_get_data:
        mock_data = [
            Data(
                name="test_sub",
                title="Test Subscription",
                description="Test Description",
                url="https://example.com/data",
                content_type="text/csv",
                creator="test_creator",
                org="test_org",
                categories=["test_category"],
                genre="test_genre",
            )
        ]
        mock_get_data.return_value = mock_data

        result = nyx_client.my_subscriptions(
            categories=["test_category"],
            genre="test_genre",
            creator="test_creator",
            license="MIT",
            content_type="text/csv",
        )

        mock_get_data.assert_called_once_with(
            categories=["test_category"],
            genre="test_genre",
            creator="test_creator",
            license="MIT",
            content_type="text/csv",
            subscription_state="subscribed",
        )
        assert result == mock_data


def test_my_data(nyx_client):
    with patch.object(nyx_client, "get_data") as mock_get_data:
        mock_data = [
            Data(
                name="test_data",
                title="My Test Data",
                description="Test Description",
                url="https://example.com/data",
                content_type="text/csv",
                creator=nyx_client.org,
                org=nyx_client.org,
                categories=["test_category"],
                genre="test_genre",
            )
        ]
        mock_get_data.return_value = mock_data

        result = nyx_client.my_data(
            categories=["test_category"], genre="test_genre", license="MIT", content_type="text/csv"
        )

        mock_get_data.assert_called_once_with(
            categories=["test_category"],
            genre="test_genre",
            creator=nyx_client.org,
            license="MIT",
            content_type="text/csv",
            subscription_state="all",
            local_only=True,
        )
        assert result == mock_data


def test_update_data(requests_mock, nyx_client):
    name = "test_data"
    mock_response = {
        "name": name,
        "title": "Updated Title",
        "description": "Updated Description",
        "accessURL": "https://example.com/updated",
        "contentType": "text/csv",
        "creator": nyx_client.org,
        "categories": ["updated_category"],
        "genre": "updated_genre",
    }

    requests_mock.patch(f"https://mock.nyx.url/api/portal/products/{name}", json=mock_response)

    result = nyx_client.update_data(
        name=name,
        title="Updated Title",
        description="Updated Description",
        size=1000,
        genre="updated_genre",
        categories=["updated_category"],
        download_url="https://example.com/updated",
        content_type="text/csv",
        preview="Test preview",
    )

    assert isinstance(result, Data)
    assert result.name == name
    assert result.title == "Updated Title"
    assert result.description == "Updated Description"
    assert result.content_type == "text/csv"
    assert result.creator == nyx_client.org

    # Verify the multipart request was formed correctly
    last_request = requests_mock.last_request
    assert last_request.headers["Content-Type"].startswith("multipart/form-data")


def test_subscribe_unsubscribe(requests_mock, nyx_client):
    test_data = Data(
        name="test_data",
        title="Test Data",
        description="Test Description",
        url="https://example.com/data",
        content_type="text/csv",
        creator="test_creator",
        org="test_org",
        categories=["test_category"],
        genre="test_genre",
    )

    # Test subscribe
    requests_mock.post("https://mock.nyx.url/api/portal/purchases/transactions", json={"status": "success"})

    nyx_client.subscribe(test_data)
    assert requests_mock.call_count == 1
    assert requests_mock.last_request.json() == {"product_name": test_data.name, "seller_org": test_data.creator}

    # Test unsubscribe
    requests_mock.delete(f"https://mock.nyx.url/api/portal/purchases/transactions/{test_data.creator}/{test_data.name}")

    nyx_client.unsubscribe(test_data)
    assert requests_mock.call_count == 2


def test_subscribe_error(requests_mock, nyx_client):
    test_data = Data(
        name="test_data",
        title="Test Data",
        description="Description",
        url="https://example.com/data",
        content_type="text/csv",
        creator="test_creator",
        org="test_org",
        categories=["test_category"],
        genre="test_genre",
    )

    error_response = {
        "error": "Subscription failed",
        "message": "Unable to subscribe to data: insufficient permissions",
        "code": "SUBSCRIPTION_ERROR",
    }

    requests_mock.post("https://mock.nyx.url/api/portal/purchases/transactions", status_code=400, json=error_response)

    with pytest.raises(requests.HTTPError) as exc_info:
        nyx_client.subscribe(test_data)

    # Verify the error response was received
    assert exc_info.value.response.status_code == 400
    assert exc_info.value.response.json() == error_response


def test_unsubscribe_error(requests_mock, nyx_client):
    test_data = Data(
        name="test_data",
        title="Test Data",
        description="Description",
        url="https://example.com/data",
        content_type="text/csv",
        creator="test_creator",
        org="test_org",
        categories=["test_category"],
        genre="test_genre",
    )

    requests_mock.delete(
        f"https://mock.nyx.url/api/portal/purchases/transactions/{test_data.creator}/{test_data.name}", status_code=404
    )

    with pytest.raises(requests.HTTPError):
        nyx_client.unsubscribe(test_data)
