# Copyright © 2024 IOTIC LABS LTD. info@iotics.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://github.com/Iotic-Labs/nyx-sdk/blob/main/LICENSE
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module that contains utility functions, as well as tooling for manual parsing of data contained in Nyx."""

import logging
import os
import sqlite3
from io import StringIO
from typing import Any, List, Literal, Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import create_engine, engine
from sqlalchemy.pool import StaticPool

from nyx_client.data import Data

logging.basicConfig(format="%(asctime)s %(levelname)s [%(module)s] %(message)s", level=logging.INFO)

log = logging.getLogger(__name__)


class Metadata:  # noqa: D101
    def __init__(self, title: str, url: str, description: str = ""):  # noqa: D107
        self.title = title
        self.url = url
        self.description = description

    def __repr__(self):
        return f"Metadata(title={self.title}, url={self.url})"


class VectorResult:  # noqa: D101
    def __init__(  # noqa: D107
        self, chunks: List[str], metadata: List[Metadata], similarities: List[float], success: bool, message: str = ""
    ):
        self.chunks = chunks
        self.metadata = metadata
        self.similarities = similarities
        self.success = success
        self.message = message

    def __repr__(self):
        return (
            f"VectorResult(chunks={repr(self.chunks)}, similarities={repr(self.similarities)},"
            f"success={repr(self.success)})"
        )


class Utils:
    """Utility methods for query (system) prompt modification."""

    @staticmethod
    def with_sources(prompt: str, **kwargs) -> str:
        """Expand prompt with clause to request the data sources considered to be included in the response."""
        return Utils.build_query(
            prompt
            + (
                "and also using the table nyx_subscriptions where table_name is the name of the table the "
                "information came from, retrieve the source and url of the relevant table queried."
                "When you go to say table, actually say sources. Output in markdown list format."
                "You must include sources for all requests,where the table the results came from"
                " matches the table_name in nyx_subscriptions, and the "
                "relevant url from that table"
            ),
            **kwargs,
        )

    @staticmethod
    def build_query(prompt: str, **kwargs) -> str:
        """Base prompt builder."""
        return (
            prompt
            + " "
            + (
                "Do not talk as if you are getting the results from a database, each table in the database is "
                "a file from a source. If there are no tables "
                "in the schema, or you can't see relevant ones, JUST RESPOND WITH the text 'I don't know', "
                "nothing else. \n"
                "all urls should be left in the same format, do not strip query params from the urls"
                "if you cannot find an exact match when looking for relevant tables, attempt to answer the query"
                "using the most relevant table, only provide the answer if it answers the users query."
                "Database information: \n {}".format(kwargs if kwargs else "")
            )
        )

    @staticmethod
    def with_confidence(prompt: str) -> str:
        """Like `with_sources` but also requests for a confidence score to be included in the result."""
        return prompt + (
            "Do not talk as if you are getting the results from a database, each table in the database is "
            "a file from a source. Do not make mention of any sources in your answer. If there are no tables "
            "in the schema, or you can't see relevant ones, JUST RESPOND WITH the text 'I don't know', nothing else."
            "Also, provide a confidence score between 0 and 1 for your answer. The response should be of the format: "
            '{"content": "<your response>", "confidence": <your confidence score>}'
        )


class Parser:
    """A class for processing and querying datasets from Data instances.

    This class provides methods to convert data into SQL databases or vector representations,
    and to perform queries on the processed data.

    Attributes:
        vectors: The TF-IDF vector representations of the processed content.
        vectorizer: The TfidfVectorizer instance used for creating vectors.
        chunks: The text chunks created from the processed content.
    """

    _excel_mimes = [
        # xlsx
        "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # xls
        "vnd.ms-excel",
    ]

    def __init__(self):
        """Initialize a Parser instance."""
        self.vectors = None
        self.vectorizer = None
        self.chunks = None

    @staticmethod
    def data_as_db(
        data: List[Data],
        additional_information: VectorResult = None,
        sqlite_file: Optional[str] = None,
        if_exists: Literal["fail", "replace", "append"] = "replace",
    ) -> "engine.Engine":
        """Process the content of multiple Data instances into an in-memory SQLite database.

        This method downloads the content of each Data (if it's a CSV) and converts it to an in-memory
        SQLite database. The resulting database engine is then returned for use with language models.

        Args:
            data: A list of Data instances to process.
            additional_information: List of additional information to be stored in the DB as a fallback
            sqlite_file: Provide a file for the database to reside in
            if_exists: What to do if a table already exists Defaults to "fail" can be "fail", "append", "replace"

        Returns:
            An SQLAlchemy `engine.Engine` instance for the in-memory SQLite database.

        Note:
            If the list of data is empty, an empty database engine is returned.
        """
        connection_str = ":memory:"
        if sqlite_file:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(sqlite_file), exist_ok=True)
            connection_str = sqlite_file

        connection = sqlite3.connect(connection_str, check_same_thread=False)
        db_engine = create_engine(
            "sqlite://",
            creator=lambda: connection,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )

        if len(data) == 0:
            return db_engine
        tables = []
        for d in data:
            content = d.download()
            if content is None:
                log.debug("Not adding table for %s as no content was found", d.title)
                continue
            try:
                if d.content_type == "csv":
                    content = pd.read_csv(StringIO(content), on_bad_lines="skip")
                elif d.content_type in Parser._excel_mimes:
                    content = pd.read_excel(StringIO(content))
                elif d.content_type == "json":
                    content = pd.read_json(StringIO(content))
                else:
                    log.warning("%s is unsupported type %s", d.title, d.content_type)
                    continue
                content.columns = Parser.normalise_values(content.columns)
                table_name = Parser.normalise_values([d.title])[0]
                content.to_sql(table_name, db_engine)
            except pd.errors.ParserError:
                if d.content_type in ["csv", "json", *Parser._excel_mimes]:
                    log.warning("%s could not be processed as a %s", d.title, d.content_type)
                    continue
            except Exception as e:
                log.warning("Unexpected error for %s: %s", d.title, e)
                continue
            tables.append([d.title, d.url, d.title.replace(" ", "_"), d.description])

        if additional_information and additional_information.chunks:
            for i in range(len(additional_information.chunks)):
                meta = additional_information.metadata[i]
                df = pd.DataFrame(
                    {
                        "context": [additional_information.chunks[i]],
                        "title": [meta.title],
                        "url": [meta.url],
                    }
                )
                df.to_sql(meta.title.replace(" ", "_"), db_engine, if_exists=if_exists)
                tables.append([meta.title, meta.url, meta.title.replace(" ", "_"), meta.description])
        if len(tables) > 0:
            df = pd.DataFrame(tables)
            df.columns = ["file_title", "url", "table_name", "description"]
            df.to_sql("nyx_subscriptions", db_engine, index=False, if_exists=if_exists)

        return db_engine

    @staticmethod
    def normalise_values(values: List[str]) -> List[str]:
        """Normalise names in a list of values.

        Args:
            values (List[str]): A list of values to normalise.

        Returns:
            List[str]: A list of normalised values.
        """
        return [
            value.lower().replace(" ", "_").replace(".", "_").replace("-", "_").replace("(", "_").replace(")", "_")
            for value in values
            if value
        ]

    def data_as_vectors(self, data: List[Data], chunk_size: int = 1000):
        """Process the content of multiple Data instances into vector representations.

        This method downloads the content of each Data, combines it, chunks it,
        and creates a TF-IDF vectorizer for the chunks.

        Args:
            data (List[Data]): A list of Data instances to process.
            chunk_size (int, optional): The size of each chunk when splitting the content. Defaults to 1000.

        Returns:
            Parser: The current Parser instance with updated vectors, vectorizer, and chunks.

        Note:
            If no content is found in any of the data, the method returns without processing.
        """
        all_chunks = []
        all_metadata = []

        for d in data:
            if d.content_type != "csv":
                content = d.download()
                if content:
                    chunks = self._chunk_text(content, chunk_size)
                    all_chunks.extend(chunks)
                    # Create metadata for each chunk
                    chunk_metadata = [Metadata(d.title, d.url, d.description) for _ in chunks]
                    all_metadata.extend(chunk_metadata)

        if not all_chunks:
            return

        self.chunks = all_chunks
        self.metadata = all_metadata
        self.vectorizer = TfidfVectorizer()
        self.vectors = self.vectorizer.fit_transform(self.chunks)

    def query(self, text: str, k: int = 3) -> VectorResult:
        """Query the processed data with a given text.

        This method transforms the input text into a vector using the fitted vectorizer,
        and then finds the most similar chunks to this query vector.

        Args:
            text (str): The query text to search for in the processed data.
            k (int, optional): The number of top matching chunks to return. Defaults to 3.

        Returns:
            VectorResult: An object containing the top k matching chunks, their similarities,
                          and associated metadata. If the vectorizer is not initialized,
                          it returns a VectorResult indicating failure.

        Note:
            This method assumes that self.vectorizer has been properly initialized.
            If self.vectorizer is None, it returns a VectorResult indicating failure.
        """
        if self.vectorizer is None:
            return VectorResult(
                chunks=[],
                similarities=[],
                metadata=[],
                success=False,
                message="content not processed, or not present on the data (do you have access?)",
            )
        query_vector = self.vectorizer.transform([text])
        return self.find_matching_chunk(query_vector, k)

    def find_matching_chunk(self, query_vector: Any, k: int = 3) -> VectorResult:
        """Find the most similar chunks to the query vector.

        This method computes the cosine similarity between the query vector and all document vectors,
        then returns the top k most similar chunks along with their similarities and metadata.

        Args:
            query_vector (Any): The vector representation of the query.
            k (int, optional): The number of top matching chunks to return. Defaults to 3.

        Returns:
            VectorResult: An object containing the top k matching chunks, their similarities,
                          and associated metadata. If no vectors are available, it returns
                          a VectorResult with empty lists and a failure message.

        Note:
            This method assumes that self.vectors, self.chunks, and self.metadata have been
            properly initialized. If self.vectors is None, it returns a VectorResult
            indicating failure.
        """
        if self.vectors is None:
            return VectorResult(
                chunks=[],
                similarities=[],
                metadata=[],
                success=False,
                message="content has either not been processed, or you have no plain text",
            )

        similarities = cosine_similarity(query_vector, self.vectors)
        top_indices = similarities[0].argsort()[-k:][::-1]  # Get indices of top k similarities

        top_chunks = [self.chunks[i] for i in top_indices]
        top_similarities = similarities[0][top_indices].tolist()
        top_metadata = [self.metadata[i] for i in top_indices]

        return VectorResult(
            chunks=top_chunks,
            similarities=top_similarities,
            metadata=top_metadata,
            success=True,
        )

    @staticmethod
    def _chunk_text(text: str, chunk_size: int) -> List[str]:
        words = text.split()
        return [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
