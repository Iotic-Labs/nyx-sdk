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

"""Module for managing connection to Nyx."""

import base64
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

import grpc
import requests
from iotics.api.common_pb2 import Headers, Scope
from iotics.api.meta_pb2 import SparqlQueryResponse, SparqlResultType
from requests_toolbelt.multipart.encoder import MultipartEncoder

from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data
from nyx_client.host_client import HostClient

logging.basicConfig(format="%(asctime)s %(levelname)s [%(module)s] %(message)s", level=logging.INFO)

log = logging.getLogger(__name__)

NS_IOTICS = "http://data.iotics.com/iotics#"
NS_NYX = "http://data.iotics.com/pnyx#"

DATA_NAME = NS_NYX + "productName"

_SELECT = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT ?access_url ?title ?org ?name ?mediaType ?size ?creator ?description
"""

_COMMON_FILTER = f"""
          ?s <{DATA_NAME}> ?name ;
              dcat:accessURL ?access_url ;
              dct:title ?title ;
              dcat:mediaType ?mediaType ;
              dct:creator ?creator ;
              dcat:byteSize ?size ;
              dct:description ?description .
"""


@dataclass
class NyxClient:
    """A client for interacting with the Nyx system.

    This client provides methods for querying and processing data from Nyx.

    Attributes:
        config: Configuration for the Nyx client.
        host_client: Client for interacting with the host.
    """

    config: BaseNyxConfig
    host_client: HostClient

    def __init__(
        self,
        env_file: Optional[str] = None,
        config: Optional[BaseNyxConfig] = None,
    ):
        """Instantiate a new client.

        Args:
            env_file: Path to the environment file containing configuration.
            config: Pre-configured BaseNyxConfig object.
        """
        if config:
            self.config = config
        else:
            self.config = BaseNyxConfig(env_file, validate=True)

        self._token = self.config.override_token
        self._refresh = ""
        self._subscribed_data: tuple[str] = ()

        self._setup()

    def _setup(self):
        self._authorise(refresh=False)

        # Set user nickname
        self.name = self._nyx_get("users/me").get("name")
        log.debug("successful login as %s", self.name)

        self.update_subscriptions(refresh=False)

        # Get host info
        qapi = self._nyx_get("auth/qapi-connection")
        self.config.community_mode = qapi.get("community_mode", False)
        self.config.org = f"{qapi.get('org_name')}/{self.name}" if self.config.community_mode else qapi.get("org_name")
        self.config.host_config.host_url = qapi.get("grpc_url")
        self.config.host_config.resolver_url = qapi.get("resolver_url")

        self.host_client = HostClient(self.config.host_config)

    def _nyx_post(self, endpoint: str, data: dict, headers: dict = None, multipart: MultipartEncoder = None) -> dict:
        if not headers:
            headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.post(
            url=self.config.nyx_url + "/api/portal/" + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        resp.raise_for_status()

        return resp.json()

    def _nyx_get(self, endpoint: str) -> dict:
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.get(url=self.config.nyx_url + "/api/portal/" + endpoint, headers=headers)
        resp.raise_for_status()

        return resp.json()

    def _authorise(self, refresh=True):
        """Authorise with the configured Nyx instance using basic authorisation."""
        if not refresh and self._token:
            # If it's not fresh then we'll return and use the existing token
            return
        resp = self._nyx_post("auth/login", self.config.nyx_auth)
        log.debug("Login response: %s", resp)
        self._token = resp["access_token"]
        self._refresh = resp["refresh_token"]

    def update_subscriptions(self, refresh=True):
        """Update the list of subscribed data."""
        self._authorise(refresh)
        # Get all the data we're subscribed to, so the results are relevant to what the user wants
        purchases = self._nyx_get("purchases/transactions")
        if not purchases:
            self._subscribed_data = []
            return
        self._subscribed_data = tuple(k["product_name"] for k in purchases)

    def close(self):
        """Cleanup any resources used by the client."""
        pass

    @property
    def subscribed_data(self) -> tuple[str]:
        """Names of subscribed-to products.

        Can be explicitly updated by calling `update_subscriptions`.
        """
        return self._subscribed_data

    def _local_sparql_query(self, query: str) -> list[Dict[str, str]]:
        """Execute a SPARQL query against the configured IOTICS host.

        Args:
            query: The SPARQL query string.

        Returns:
            A list of dictionaries representing the query results.
        """
        return self._sparql_query(query, Scope.LOCAL)

    def _federated_sparql_query(self, query: str) -> list[Dict[str, str]]:
        """Execute a SPARQL query against the federated network.

        Args:
            query: The SPARQL query string.

        Returns:
            A list of dictionaries representing the query results.
        """
        return self._sparql_query(query, Scope.GLOBAL)

    def _sparql_query(self, query: str, scope: Scope) -> list[Dict[str, str]]:
        """Execute a SPARQL query and process the results.

        Args:
            query: The SPARQL query string.
            scope: The scope of the query (LOCAL or GLOBAL).

        Returns:
            A list of dictionaries representing the query results.

        Raises:
            ValueError: If the response is incomplete.
            grpc.RpcError: If there's an RPC error during the query execution.
        """
        with self.host_client as client:
            chunks: dict[int, SparqlQueryResponse] = {}
            stream = client.api.sparql_api.sparql_query(
                query,
                result_content_type=SparqlResultType.SPARQL_JSON,
                scope=scope,
                headers=Headers(transactionRef=("nyx_sdk", str(uuid.uuid4()))),
            )
            try:
                for response in stream:
                    chunks[response.payload.seqNum] = response
            except grpc.RpcError as err:
                err: grpc._channel._MultiThreadedRendezvous
                if err.code() != grpc.StatusCode.DEADLINE_EXCEEDED:
                    raise err

            sorted_chunks = sorted(chunks.values(), key=lambda r: r.payload.seqNum)
            if len(sorted_chunks) == 0:
                return []
            last_chunk = sorted_chunks[-1]

            if not last_chunk.payload.last or len(chunks) != last_chunk.payload.seqNum + 1:
                raise ValueError("Incomplete response")
            resp_json = json.loads("".join([c.payload.resultChunk.decode() for c in sorted_chunks]))
            results = []
            for binding in resp_json["results"]["bindings"]:
                inner_json = {}
                for k in binding:
                    inner_json[k] = binding[k]["value"]
                results.append(inner_json)

            return results

    def get_all_categories(self) -> list[str]:
        """Retrieve all categories from the federated network.

        Returns:
            A list of category names.
        """
        query = """
        PREFIX dcat: <http://www.w3.org/ns/dcat#>

        SELECT DISTINCT ?theme
        WHERE {
          ?s dcat:theme ?theme .
        }
        """

        return [r["theme"] for r in self._federated_sparql_query(query)]

    def get_subscribed_categories(self) -> list[str]:
        """Retrieve subscribed categories from the federated network.

        Returns:
            A list of category names.
        """
        if len(self._subscribed_data) == 0:
            return []

        query = f"""
        PREFIX dcat: <http://www.w3.org/ns/dcat#>

        SELECT DISTINCT ?theme
        WHERE {{
          ?s dcat:theme ?theme .
          ?s <{DATA_NAME}> ?name .
          ?s dct:creator ?creator .
          FILTER(?creator != "{self.config.org}")
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
        }}
        """

        return [r["theme"] for r in self._federated_sparql_query(query)]

    def get_all_genres(self) -> list[str]:
        """Retrieve all genres from the federated network.

        Returns:
            A list of genre names.
        """
        query = """
        PREFIX dc: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?genre
        WHERE {
          ?s dc:type ?genre .
        }
        """

        return [r["genre"] for r in self._federated_sparql_query(query)]

    def get_subscribed_genres(self) -> list[str]:
        """Retrieve subscribed genres from the federated network.

        Returns:
            A list of genre names.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        PREFIX dc: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?genre
        WHERE {{
          ?s dc:type ?genre .
          ?s <{DATA_NAME}> ?name .
          ?s dct:creator ?creator .
          FILTER(?creator != "{self.config.org}")
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
        }}
        """

        return [r["genre"] for r in self._federated_sparql_query(query)]

    def get_subscribed_creators(self) -> list[str]:
        """Retrieve subscribed creators from the federated network.

        Returns:
            A list of creator names.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?creator
        WHERE {{
          ?s dct:creator ?creator .
          ?s <{DATA_NAME}> ?name .
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
        }}
        """

        return [r["creator"] for r in self._federated_sparql_query(query)]

    def get_all_creators(self) -> list[str]:
        """Retrieve all creators from the federated network.

        Returns:
            A list of creator names.
        """
        query = """
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?creator
        WHERE {
          ?s dct:creator ?creator .
        }
        """

        return [r["creator"] for r in self._federated_sparql_query(query)]

    def get_subscribed_data(self) -> list[Data]:
        """Retrieve subscribed data from the federated network.

        Returns:
            A list of `Data` instances.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER(?creator != "{self.config.org}")
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def get_subscribed_data_for_categories(self, categories: list[str]) -> list[Data]:
        """Retrieve subscribed data for specific categories from the federated network.

        Args:
            categories: A list of category names to filter by.

        Returns:
            A list of `Data` instances matching the specified categories.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER(?creator != "{self.config.org}")
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
          ?s dcat:theme ?theme .
          FILTER({" || ".join([f'?theme = "{theme.lower()}"' for theme in categories])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def get_data_for_categories(self, categories: list[str]) -> list[Data]:
        """Retrieve all data for specific categories from the federated network.

        Args:
            categories: A list of category names to filter by.

        Returns:
            A list of `Data` instances matching the specified categories.
        """
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          ?s dcat:theme ?theme .
          FILTER({" || ".join([f'?theme = "{theme.lower()}"' for theme in categories])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def get_subscribed_data_for_genres(self, genres: list[str]) -> list[Data]:
        """Retrieve subscribed data for specific genres from the federated network.

        Args:
            genres: A list of genre names to filter by.

        Returns:
            A list of `Data` instances matching the specified genres.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER(?creator != "{self.config.org}")
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
          ?s dct:type ?type .
          FILTER({" || ".join([f'?type = "{genre.lower()}"' for genre in genres])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def get_data_for_genres(self, genres: list[str]) -> list[Data]:
        """Retrieve data for specific genres from the federated network.

        Args:
            genres: A list of genre names to filter by.

        Returns:
            A list of `Data` instances matching the specified genres.
        """
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          ?s dct:type ?type .
          FILTER({" || ".join([f'?type = "{genre.lower()}"' for genre in genres])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def get_data_by_name(self, name: str) -> Optional[Data]:
        """Retrieve a data based on its unique name.

        Args:
            name (str): The data unique name.

        Returns:
            The `Data` instance identified with the provided name or None if it does not exist.
        """
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER(?name = "{name}")
        }}
        """

        data = [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]
        # In normal state the result can either be a list of one if the data exists or 0.
        return data[0] if data else None

    def get_subscribed_data_for_creators(self, creators: list[str]) -> list[Data]:
        """Retrieve subscribed data from specific creators from the federated network.

        Args:
            creators: A list of creators to filter by.

        Returns:
            A list of `Data` instances matching the specified creators.
        """
        if len(self._subscribed_data) == 0:
            return []
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
          FILTER({" || ".join([f'?creator = "{creator}"' for creator in creators])})
        }}
        """

        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def create_data(
        self,
        name: str,
        title: str,
        description: str,
        size: int,
        genre: str,
        categories: list[str],
        download_url: str,
        content_type: str,
        lang: str = "en",
        status: str = "published",
        preview: str = "",
        price: int = 0,
        license_url: str = "https://creativecommons.org/publicdomain/zero/1.0/",
    ) -> Data:
        """Create new data in the system.

        This method creates new data with the provided details and posts it to Nyx.

        Args:
            name: The unique identifier for the data.
            title: The display title of the data.
            description: A detailed description of the data.
            size: The size of the data, typically in bytes.
            genre: The genre or category of the data.
            categories: A list of categories the data belongs to.
            download_url: The URL where the data can be downloaded.
            content_type: The mime type of the data located at download_url.
            lang: The language of the data. Defaults to "en".
            status: The publication status of the data. Defaults to "published".
            preview: A preview or sample of the data. Defaults to an empty string.
            price: The price of the data in cents. If 0, the data is free. Defaults to 0.
            license_url: The URL of the license for the data. Defaults to Creative Commons Zero.

        Returns:
            A `Data` instance, containing the download URL and title.

        Example:
            >>> data = self.create_data(
            ...     name="uniquedataid",
            ...     title="Amazing Data",
            ...     description="This is some amazing data that does wonderful things.",
            ...     size=1024000,
            ...     genre="Software",
            ...     categories=["Utility", "Productivity"],
            ...     download_url="https://example.com/download/amazing-data",
            ...     content_type="text/csv",
            ...     price=1999  # $19.99
            ... )
            >>> print(f"Created data: {data.title}")
            Created data: Amazing Data
        """
        input_bytes = preview.encode("utf-8")
        base64_bytes = base64.b64encode(input_bytes)
        preview_base64_string = base64_bytes.decode("utf-8")

        data = {
            "name": name,
            "title": title,
            "description": description,
            "size": size,
            "genre": genre,
            "categories": categories,
            "lang": lang,
            "status": status,
            "preview": preview_base64_string,
            "downloadURL": download_url,
            "licenseURL": license_url,
            "contentType": content_type,
        }
        if price > 0:
            data["price"] = price

        multipart_data = MultipartEncoder(
            fields={
                "productMetadata": json.dumps(data),
            }
        )

        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": multipart_data.content_type}

        resp = self._nyx_post("products", data, headers, multipart_data)

        args = {
            "name": name,
            "title": title,
            "description": description,
            "org": self.config.org,
            "mediaType": content_type,
            "size": size,
        }

        download_url = resp.get("downloadURL")
        access_url = resp.get("accessURL")

        if download_url:
            args["download_url"] = download_url

        if access_url:
            args["access_url"] = access_url

        return Data(**args)

    def get_data_for_creators(self, creators: list[str]) -> list[Data]:
        """Retrieve data from specific creators from the federated network.

        Args:
            creators: A list of creators to filter by.

        Returns:
            A list of `Data` instances matching the specified creators.
        """
        query = f"""
        {_SELECT}
        WHERE {{
          {_COMMON_FILTER}
          FILTER({" || ".join([f'?creator = "{creator}"' for creator in creators])})
        }}
        """
        return [Data(**r, org=self.config.org) for r in self._federated_sparql_query(query)]

    def delete_data(self, product: Data):
        """Delete the provided data from Nyx.

        Args:
            product: The data to delete.
        """
        self.delete_data_by_name(product.name)

    def delete_data_by_name(self, name: str):
        """Delete the data uniquely identified by the provided name from Nyx.

        Args:
            name: The data unique name.
        """
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.delete(
            url=self.config.nyx_url + f"/api/portal/products/{name}",
            headers=headers,
        )
        resp.raise_for_status()
