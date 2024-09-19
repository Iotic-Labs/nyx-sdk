import pytest
import requests

from nyx_client.data import Data


@pytest.fixture
def mock_data_details():
    return {
        "access_url": "http://example.com",
        "title": "Test Data",
        "org": "TestOrg",
        "name": "test_data",
        "mediaType": "text/csv",
        "size": "321",
        "description": "Some description of sorts",
        "creator": "Test Creator",
    }


def test_data_initialization(mock_data_details):
    data = Data(**mock_data_details)
    assert data.title == "Test Data"
    assert data.description == "Some description of sorts"
    assert data.url == "http://example.com?buyer_org=TestOrg"
    assert data.content_type == "text/csv"
    assert data.size == 321
    assert data._creator == "Test Creator"
    assert data._org == "TestOrg"
    assert data._content is None


def test_nyx_data_invalid_size(mock_data_details):
    details = mock_data_details
    details["size"] = "aaa"

    data = Data(**mock_data_details)
    assert data.size == 0


def test_nyx_data_no_size(mock_data_details):
    mock_data_details.pop("size")

    data = Data(**mock_data_details)
    assert data.size == 0


def test_data_initialization_missing_fields():
    with pytest.raises(KeyError):
        Data(title="Test Data", org="Test Org")


def test_data_str(mock_data_details):
    data = Data(**mock_data_details)
    assert str(data) == "Data(Test Data, http://example.com?buyer_org=TestOrg, text/csv)"


def test_data_download(requests_mock, mock_data_details):
    data = Data(**mock_data_details)

    requests_mock.get(data.url, text="Test Content")

    content = data.download()
    assert content == "Test Content"
    assert data._content == "Test Content"


def test_data_download_cached(mocker, mock_data_details):
    mock_urlopen = mocker.patch("urllib.request.urlopen")

    data = Data(**mock_data_details)
    data._content = "Cached Content"
    content = data.download()
    assert content == "Cached Content"
    mock_urlopen.assert_not_called()


def test_nyx_data_download_failure(requests_mock, mock_data_details):
    data = Data(**mock_data_details)

    requests_mock.get(data.url, exc=requests.exceptions.ConnectTimeout)

    content = data.download()
    assert content is None
    assert data._content is None
