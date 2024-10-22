from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from nyx_client.data import Data
from sqlalchemy import text

from nyx_extras import Metadata, Parser, VectorResult


@pytest.fixture
def sample_csv_content():
    return bytes(
        """
    id,name,value
    1,Alice,100
    2,Bob,200
    3,Charlie,300
    """,
        encoding="utf-8",
    )


@pytest.fixture
def sample_csv_content_2():
    return bytes(
        """
    id,name,value
    1,Andy,1000
    2,Conal,10
    3,Phil,300
    """,
        encoding="utf-8",
    )


@pytest.fixture
def sample_data():
    return [
        Data(
            url="http://test.com",
            title="Test data 1",
            org="test_org",
            name="testdata1",
            description="",
            content_type="csv",
            creator="me",
            categories=["ai"],
            genre="ai",
        ),
        Data(
            url="http://test.com",
            title="Test data 2",
            org="test_org",
            name="testdata2",
            description="",
            content_type="csv",
            creator="me",
            categories=["ai"],
            genre="ai",
        ),
    ]


def test_dataset_as_db_empty_list():
    engine = Parser.data_as_db([])
    assert engine is not None, "Engine should not be None for empty list"
    assert hasattr(engine, "connect"), "Engine should have a 'connect' method"

    # Optionally, try to use the engine to ensure it's a valid SQLAlchemy engine
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).fetchone()
        assert result == (1,), "Engine should be able to execute a simple query"


def test_dataset_as_db_with_data(sample_data, sample_csv_content):
    with patch.object(Data, "as_bytes", return_value=sample_csv_content):
        engine = Parser.data_as_db(sample_data)
        assert engine is not None, "Engine should not be None"

        # Verify that the tables were created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
            table_names = [row[0] for row in result]
            assert "test_data_1" in table_names, "test_data_1 table should be created"
            assert "test_data_2" in table_names, "test_data_2 table should be created"
            assert "nyx_subscriptions" in table_names, "nyx_subscriptions table should be created"


def test_dataset_as_vectors(sample_data):
    parser = Parser()
    sample_data[0].content_type = "txt"
    sample_data[1].content_type = "txt"

    with patch.object(Data, "as_string", side_effect=["This is a test content.", "Another test content here."]):
        parser.data_as_vectors(sample_data, chunk_size=4)

        assert parser.vectors is not None
        assert parser.vectorizer is not None
        assert len(parser.chunks) == 3


def test_chunk_text():
    text = "This is a test sentence. This is another test sentence."
    chunks = Parser._chunk_text(text, chunk_size=5)
    assert len(chunks) == 2
    assert chunks[0] == "This is a test sentence."
    assert chunks[1] == "This is another test sentence."


def test_find_matching_chunk():
    parser = Parser()
    parser.chunks = ["This is chunk one.", "This is chunk two.", "This is chunk three.", "This is chunk four."]
    parser.vectorizer = MagicMock()
    parser.vectors = np.array([[0.1, 0.2, 0.3, 0.4], [0.2, 0.3, 0.4, 0.5], [0.3, 0.4, 0.5, 0.6], [0.4, 0.5, 0.6, 0.7]])
    parser.metadata = [
        Metadata("Test Data 1", "http://example.com/1", "This is chunk one."),
        Metadata("Test Data 2", "http://example.com/2", "This is chunk two."),
        Metadata("Test Data 3", "http://example.com/3", "This is chunk three."),
        Metadata("Test Data 4", "http://example.com/4", "This is chunk four."),
    ]

    with patch("nyx_extras.utils.cosine_similarity", return_value=np.array([[0.5, 0.7, 0.6, 0.8]])):
        result = parser.find_matching_chunk(MagicMock(), k=3)
        assert len(result.chunks) == 3
        assert result.chunks == ["This is chunk four.", "This is chunk two.", "This is chunk three."]
        assert result.similarities == [0.8, 0.7, 0.6]
        assert result.success is True


def test_query():
    parser = Parser()
    parser.vectorizer = MagicMock()
    parser.find_matching_chunk = MagicMock(
        return_value=VectorResult(
            chunks=["Matched chunk 1", "Matched chunk 2", "Matched chunk 3"],
            similarities=[0.9, 0.8, 0.7],
            success=True,
            metadata=[
                Metadata("Test Data 1", "http://example.com/1", "This is chunk one."),
                Metadata("Test Data 2", "http://example.com/2", "This is chunk two."),
                Metadata("Test Data 3", "http://example.com/3", "This is chunk three."),
                Metadata("Test Data 4", "http://example.com/4", "This is chunk four."),
            ],
        )
    )

    result = parser.query("Test query", k=3)
    assert len(result.chunks) == 3
    assert result.chunks == ["Matched chunk 1", "Matched chunk 2", "Matched chunk 3"]
    assert result.similarities == [0.9, 0.8, 0.7]
    assert result.success is True


def test_query_no_vectorizer():
    parser = Parser()
    result = parser.query("Test query")
    assert result.success is False
    assert "content not processed" in result.message
    assert len(result.chunks) == 0
    assert len(result.similarities) == 0
