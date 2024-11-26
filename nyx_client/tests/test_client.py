from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
import requests
from requests_mock import Mocker as RequestsMocker

from nyx_client.client import NyxClient, SparqlResultType
from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data
from nyx_client.property import Property

TEST_NYX_URL = "https://mock.nyx.url"
TEST_NYX_API_ROOT = f"{TEST_NYX_URL}/api/portal/"

TEST_PROPERTIES = [
    Property.lang_string("https://example.com/somePredicate1", "hello there", "en"),
    Property.string("https://example.com/somePredicate2", "abcd"),
    Property.literal("https://example.com/somePredicate3", "1.234", "float"),
    Property.uri("https://example.com/somePredicate4", "https://example.com/some/where"),
]
TEST_PROPERTIES_ENCODED = [prop.as_dict() for prop in TEST_PROPERTIES]


@pytest.fixture(autouse=True)
def mock_dotenv_values():
    mock_values = {
        "NYX_URL": "https://mock.nyx.url",
        "NYX_EMAIL": "mock@email.com",
        "NYX_PASSWORD": "mock_password",
    }
    with (
        patch("nyx_client.configuration.dotenv_values", return_value=mock_values),
        patch("nyx_client.configuration.find_dotenv", return_value="mock_env_location/.env"),
    ):
        yield


@pytest.fixture
def mock_config() -> Generator[BaseNyxConfig]:
    config = BaseNyxConfig.from_env(override_token="test_token")
    yield config


@pytest.fixture
def nyx_client(mock_config: BaseNyxConfig) -> Generator[NyxClient]:
    with patch("nyx_client.client.NyxClient._setup"):
        client = NyxClient(config=mock_config)
        client.org = "test"
        yield client


def test_nyx_client_initialization(nyx_client: NyxClient, mock_config: BaseNyxConfig):
    assert isinstance(nyx_client, NyxClient)
    assert nyx_client.config == mock_config


def test_nyx_post(requests_mock: RequestsMocker, nyx_client: NyxClient):
    rsp_data = {"key": "value"}
    requests_mock.post(TEST_NYX_API_ROOT + "test_endpoint", json=rsp_data)

    result = nyx_client._nyx_post("test_endpoint", {"data": "test"})
    assert result == rsp_data
    assert requests_mock.call_count == 1


def test_nyx_get(requests_mock: RequestsMocker, nyx_client: NyxClient):
    rsp_data = {"key": "value"}
    requests_mock.get(TEST_NYX_API_ROOT + "test_endpoint", json=rsp_data)

    result = nyx_client._nyx_get("test_endpoint")
    assert result == rsp_data
    assert requests_mock.call_count == 1


def test_delete_data(requests_mock: RequestsMocker, nyx_client: NyxClient):
    name = "test_data"

    requests_mock.delete(TEST_NYX_API_ROOT + f"products/{name}")

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


def test_nyx_post_network_error(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.post(TEST_NYX_API_ROOT + "test_endpoint", exc=requests.ConnectionError)

    with pytest.raises(requests.ConnectionError):
        nyx_client._nyx_post("test_endpoint", {"data": "test"})


def test_nyx_get_network_error(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.get(TEST_NYX_API_ROOT + "test_endpoint", exc=requests.ConnectionError)

    with pytest.raises(requests.ConnectionError):
        nyx_client._nyx_get("test_endpoint")


def test_authorise_invalid_credentials(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.post(TEST_NYX_API_ROOT + "auth/login", status_code=401)
    with pytest.raises(requests.HTTPError):
        nyx_client._authorise()


def test_get_all_categories_empty_result(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.get(TEST_NYX_API_ROOT + "meta/categories", json=[])
    result = nyx_client.categories()
    assert result == []


# Minimum response fields necessary for create response to work.
MIN_CREATE_DATA_RESPONSE = {
    "name": "aha",
    "title": "aha2",
    "description": "server description",
    "contentType": "ctype",
    "creator": "the creator",
    "genre": "server whatever",
    "categories": ["server", "categories"],
    "size": 101,
    "accessURL": "http://here.com/server",
}


def test_create_data_with_size(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.post(TEST_NYX_API_ROOT + "products", json=MIN_CREATE_DATA_RESPONSE)
    result = nyx_client.create_data(
        name="a_name",
        title="a_title",
        description="foo",
        genre="x",
        categories=[],
        content_type="text/csv",
        size=MIN_CREATE_DATA_RESPONSE["size"] + 999,
        download_url="http://here.com",
    )

    # NOTE: The size from the response should be returned, not the input
    assert result.size == MIN_CREATE_DATA_RESPONSE["size"]


def test_create_data_minimal(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.post(TEST_NYX_API_ROOT + "products", json=MIN_CREATE_DATA_RESPONSE)
    result = nyx_client.create_data(
        name="a_name",
        title="a_title",
        description="foo",
        genre="x",
        categories=[],
        content_type="text/csv",
        download_url="http://here.com",
    )
    # NOTE: The following should have values taken from the server response, regardless of what the client has supplied
    assert result.name == MIN_CREATE_DATA_RESPONSE["name"]
    assert result.title == MIN_CREATE_DATA_RESPONSE["title"]
    assert result.description == MIN_CREATE_DATA_RESPONSE["description"]
    assert result.content_type == MIN_CREATE_DATA_RESPONSE["contentType"]
    assert result.creator == MIN_CREATE_DATA_RESPONSE["creator"]
    assert result.size == MIN_CREATE_DATA_RESPONSE["size"]
    assert result.url.startswith(MIN_CREATE_DATA_RESPONSE["accessURL"])
    assert result.categories == MIN_CREATE_DATA_RESPONSE["categories"]
    assert result.genre == MIN_CREATE_DATA_RESPONSE["genre"]
    assert result.custom_metadata == []


def test_create_data_with_custom_metadata(requests_mock: RequestsMocker, nyx_client: NyxClient):
    data = MIN_CREATE_DATA_RESPONSE.copy()
    data["customMetadata"] = TEST_PROPERTIES_ENCODED

    requests_mock.post(TEST_NYX_API_ROOT + "products", json=data)
    result = nyx_client.create_data(
        name="a_name",
        title="a_title",
        description="foo",
        genre="x",
        categories=[],
        content_type="text/csv",
        download_url="http://here.com",
    )

    # NOTE: Other fields validated elsewhere already
    assert result.custom_metadata == TEST_PROPERTIES


def test_create_product_invalid_input(requests_mock: RequestsMocker, nyx_client: NyxClient):
    requests_mock.post(TEST_NYX_API_ROOT + "products", status_code=400, json={})
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


def test_delete_data_not_found(requests_mock: RequestsMocker, nyx_client: NyxClient):
    name = "non_existent"

    requests_mock.delete(TEST_NYX_API_ROOT + f"products/{name}", status_code=404)

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


def assert_data_matches_dict_response(data: Data, resp: dict[str, Any], nyx_client: NyxClient):
    assert data.name == resp["name"]
    assert data.title == resp["title"]
    assert data.description == resp["description"]
    assert data.org == nyx_client.org
    assert data.url == f"{resp['accessURL']}?buyer_org={nyx_client.org}"
    assert data.content_type == resp["contentType"]
    assert data.creator == resp["creator"]
    assert data.genre == resp["genre"]
    assert set(data.categories) == set(resp["categories"])
    assert data.size == resp["size"]
    assert data.custom_metadata == [Property.from_dict(prop) for prop in resp.get("customMetadata", ())]


def test_get_data_returns_data_objects(requests_mock: RequestsMocker, nyx_client: NyxClient):
    # Mock response from "get data" endpoint
    mock_response = [
        {
            "name": "test_data",
            "title": "Test Data",
            "description": "Some description of sorts",
            "accessURL": "https://example.com/access",
            "contentType": "application/json",
            "creator": "TestCreator",
            "genre": "ai",
            "categories": ["ai"],
            "size": 321,
            "customMetadata": TEST_PROPERTIES_ENCODED,
        }
    ]
    requests_mock.get(
        TEST_NYX_API_ROOT + "products?" + "&".join(("scope=global", "include=all")),
        json=mock_response,
    )

    result = nyx_client.get_data()
    assert len(result) == 1
    assert_data_matches_dict_response(result[0], mock_response[0], nyx_client)


def test_sparql_query(requests_mock: RequestsMocker, nyx_client: NyxClient):
    query = "SELECT * WHERE { ?s ?p ?o }"
    expected_response = '{"results": {"bindings": []}}'
    requests_mock.post(
        TEST_NYX_API_ROOT + "meta/sparql/global",
        text=expected_response,
        headers={"Content-Type": "application/sparql-results+json"},
    )
    requests_mock.post(
        TEST_NYX_API_ROOT + "meta/sparql/local",
        text=expected_response,
        headers={"Content-Type": "application/sparql-results+json"},
    )

    result = nyx_client.sparql_query(query)
    assert result == expected_response

    # Test with different result type
    result = nyx_client.sparql_query(query, result_type=SparqlResultType.SPARQL_XML, local_only=True)
    assert result == expected_response
    assert requests_mock.last_request.headers["Accept"] == SparqlResultType.SPARQL_XML.value
    assert "local" in requests_mock.last_request.url


def test_search(requests_mock: RequestsMocker, nyx_client: NyxClient):
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
            "size": 999,
            "customMetadata": TEST_PROPERTIES_ENCODED,
        }
    ]

    requests_mock.get(TEST_NYX_API_ROOT + "meta/search/text", json=mock_response)

    requests_mock.get(
        TEST_NYX_API_ROOT
        + "meta/search/text?"
        + "&".join(
            (
                "genre=test_genre",
                "creator=test_creator",
                "text=test",
                "license=MIT",
                "contentType=text/csv",
                "timeout=5",
                "scope=local",
                "include=all",
                *(f"category={cat}" for cat in ("test_category", "another_cat")),
            )
        ),
        json=mock_response,
    )

    result = nyx_client.search(
        "test",
        categories=["test_category", "another_cat"],
        genre="test_genre",
        creator="test_creator",
        license="MIT",
        content_type="text/csv",
        subscription_state="all",
        timeout=5,
        local_only=True,
    )

    assert len(result) == 1
    assert_data_matches_dict_response(result[0], mock_response[0], nyx_client)


def test_my_subscriptions(requests_mock: RequestsMocker, nyx_client: NyxClient):
    mock_rsp = [
        {
            "name": "test_sub",
            "title": "Test Subscription",
            "description": "Test Description",
            "accessURL": "https://example.com/data",
            "contentType": "text/csv",
            "creator": "test_creator",
            "size": 1234,
            "categories": ["test_category"],
            "genre": "test_genre",
            "customMetadata": TEST_PROPERTIES_ENCODED,
        }
    ]

    requests_mock.get(
        TEST_NYX_API_ROOT
        + "products?"
        + "&".join(
            (
                "genre=test_genre",
                "creator=test_creator",
                "license=MIT",
                "contentType=text/csv",
                "include=subscribed",
                "scope=global",
                *(f"category={cat}" for cat in ("test_category", "another_category")),
            )
        ),
        json=mock_rsp,
    )

    result = nyx_client.my_subscriptions(
        categories=["test_category", "another_category"],
        genre="test_genre",
        creator="test_creator",
        license="MIT",
        content_type="text/csv",
    )

    assert len(result) == 1
    assert_data_matches_dict_response(result[0], mock_rsp[0], nyx_client)


def test_my_data(requests_mock: RequestsMocker, nyx_client: NyxClient):
    mock_rsp = [
        {
            "name": "test_data",
            "title": "My Test Data",
            "description": "Test Description",
            "accessURL": "https://example.com/data",
            "contentType": "text/csv",
            "creator": nyx_client.org,
            "size": 1234,
            "categories": ["test_category"],
            "genre": "test_genre",
            "customMetadata": TEST_PROPERTIES_ENCODED,
        }
    ]

    requests_mock.get(
        TEST_NYX_API_ROOT
        + "products?"
        + "&".join(
            (
                "genre=test_genre",
                f"creator={nyx_client.org}",
                "license=MIT",
                "contentType=text/csv",
                "include=all",
                "scope=local",
                "category=test_category",
            )
        ),
        json=mock_rsp,
    )

    result = nyx_client.my_data(
        categories=["test_category"], genre="test_genre", license="MIT", content_type="text/csv"
    )

    assert len(result) == 1
    assert_data_matches_dict_response(result[0], mock_rsp[0], nyx_client)


def test_update_data(requests_mock: RequestsMocker, nyx_client: NyxClient):
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
        "size": 4456,
        "customMetadata": TEST_PROPERTIES_ENCODED,
    }

    requests_mock.patch(TEST_NYX_API_ROOT + f"products/{name}", json=mock_response)

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

    assert_data_matches_dict_response(result, mock_response, nyx_client)

    # Verify the multipart request was formed correctly
    last_request = requests_mock.last_request
    assert last_request.headers["Content-Type"].startswith("multipart/form-data")


def test_subscribe_unsubscribe(requests_mock: RequestsMocker, nyx_client: NyxClient):
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
    requests_mock.post(TEST_NYX_API_ROOT + "purchases/transactions", json={"status": "success"})

    nyx_client.subscribe(test_data)
    assert requests_mock.call_count == 1
    assert requests_mock.last_request.json() == {"product_name": test_data.name, "seller_org": test_data.creator}

    # Test unsubscribe
    requests_mock.delete(TEST_NYX_API_ROOT + f"purchases/transactions/{test_data.creator}/{test_data.name}")

    nyx_client.unsubscribe(test_data)
    assert requests_mock.call_count == 2


def test_subscribe_error(requests_mock: RequestsMocker, nyx_client: NyxClient):
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

    requests_mock.post(TEST_NYX_API_ROOT + "purchases/transactions", status_code=400, json=error_response)

    with pytest.raises(requests.HTTPError) as exc_info:
        nyx_client.subscribe(test_data)

    # Verify the error response was received
    assert exc_info.value.response.status_code == 400
    assert exc_info.value.response.json() == error_response


def test_unsubscribe_error(requests_mock: RequestsMocker, nyx_client: NyxClient):
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
        TEST_NYX_API_ROOT + f"purchases/transactions/{test_data.creator}/{test_data.name}", status_code=404
    )

    with pytest.raises(requests.HTTPError):
        nyx_client.unsubscribe(test_data)
