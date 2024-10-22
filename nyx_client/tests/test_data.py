import pytest
import requests

from nyx_client.data import Data


@pytest.fixture
def mock_data_details():
    return {
        "url": "http://example.com",
        "title": "Test Data",
        "org": "TestOrg",
        "name": "test_data",
        "content_type": "text/csv",
        "size": 321,
        "description": "Some description of sorts",
        "creator": "Test Creator",
        "categories": ["ai"],
        "genre": "ai",
    }


def test_data_initialization(mock_data_details):
    data = Data(**mock_data_details)
    assert data.title == "Test Data"
    assert data.description == "Some description of sorts"
    assert data.url == "http://example.com?buyer_org=TestOrg"
    assert data.content_type == "text/csv"
    assert data.size == 321
    assert data.creator == "Test Creator"
    assert data.org == "TestOrg"


def test_nyx_data_no_size(mock_data_details):
    mock_data_details.pop("size")

    data = Data(**mock_data_details)
    assert data.size == 0


def test_data_initialization_missing_fields():
    with pytest.raises(TypeError):
        Data(title="Test Data", org="Test Org")


def test_data_str(mock_data_details):
    data = Data(**mock_data_details)
    assert str(data) == "Data(Test Data, http://example.com?buyer_org=TestOrg, text/csv)"


def test_data_as_str(requests_mock, mock_data_details):
    data = Data(**mock_data_details)

    requests_mock.get(data.url, text="Test Content")

    content = data.as_string()
    assert content == "Test Content"


def test_data_as_bytes(requests_mock, mock_data_details):
    data = Data(**mock_data_details)

    requests_mock.get(data.url, text="Test Content")

    content = data.as_bytes()
    assert content == b"Test Content"


def test_nyx_data_download_failure(requests_mock, mock_data_details):
    data = Data(**mock_data_details)

    requests_mock.get(data.url, exc=requests.exceptions.ConnectTimeout)

    content = data.as_string()
    assert content is None
