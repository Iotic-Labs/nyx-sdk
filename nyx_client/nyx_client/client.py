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
from dataclasses import dataclass
from typing import Dict, Literal, Optional

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data
from nyx_client.utils import auth_retry, ensure_setup

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
        self.subscribed_data: list[str] = []

        self._is_setup = False

    def _setup(self):
        """This is auto called on first contact with API, to ensure config is set."""
        self._is_setup = True
        self._authorise(refresh=False)

        # Set user nickname
        self.name = self._nyx_get("users/me").get("name")
        log.debug("successful login as %s", self.name)

        self.update_subscriptions()

        # Get host info
        qapi = self._nyx_get("auth/qapi-connection")
        self.config.community_mode = qapi.get("community_mode", False)
        self.config.org = f"{qapi['org_name']}/{self.name}" if self.config.community_mode else qapi["org_name"]

    def _authorise(self, refresh=True):
        """Authorise with the configured Nyx instance using basic authorisation."""
        if not refresh and self._token:
            # If it's not fresh then we'll return and use the existing token
            return
        resp = self._nyx_post("auth/login", self.config.nyx_auth)
        log.debug("Login response: %s", resp)
        self._token = resp["access_token"]
        self._refresh = resp["refresh_token"]

    @ensure_setup
    @auth_retry
    def _nyx_post(
        self, endpoint: str, data: dict, headers: Optional[dict] = None, multipart: Optional[MultipartEncoder] = None
    ) -> Dict:
        if not headers:
            headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}

        headers["authorization"] = "Bearer " + self._token
        resp = requests.post(
            url=self.config.nyx_url + "/api/portal/" + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_get(self, endpoint: str, params: Optional[dict] = None) -> Dict:
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.get(url=self.config.nyx_url + "/api/portal/" + endpoint, headers=headers, params=params)
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _sparql_query(self, query: str, scope: Literal["local", "global"]) -> list[Dict[str, str]]:
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
        headers = {
            "X-Requested-With": "nyx-sdk",
            "Content-Type": "application/json",
            "Accept": "application/sparql-results+json",
        }
        headers["authorization"] = "Bearer " + self._token
        resp = requests.get(
            url=self.config.nyx_url + "/api/portal/meta/sparql/" + scope,
            params={"query": query},
            headers=headers,
        )
        resp.raise_for_status()

        resp_json = resp.json()
        results = []
        for binding in resp_json["results"]["bindings"]:
            inner_json = {}
            for k in binding:
                inner_json[k] = binding[k]["value"]
            results.append(inner_json)

        return results

    def _local_sparql_query(self, query: str) -> list[Dict[str, str]]:
        """Execute a SPARQL query against the configured IOTICS host.

        Args:
            query: The SPARQL query string.

        Returns:
            A list of dictionaries representing the query results.
        """
        return self._sparql_query(query, "local")

    def _federated_sparql_query(self, query: str) -> list[Dict[str, str]]:
        """Execute a SPARQL query against the federated network.

        Args:
            query: The SPARQL query string.

        Returns:
            A list of dictionaries representing the query results.
        """
        return self._sparql_query(query, "global")

    def _get_all_unique(self, obj_name: str, include_all: bool = False) -> list[str]:
        limit = ""
        if include_all:
            # For include all we add the name filter. But also check that there is subscribed data
            if len(self.subscribed_data) == 0:
                return []
            limit = f"""
            ?s <{DATA_NAME}> ?name .
            FILTER({" || ".join([f'?name = "{data}"' for data in self.subscribed_data])})
            """
        query = f"""
        PREFIX dcat: <http://www.w3.org/ns/dcat#>
        PREFIX dct: <http://purl.org/dc/terms/>

        SELECT DISTINCT ?thing
        WHERE {{
          ?s {obj_name} ?thing .
          {limit}
        }}
        """

        return [r["thing"] for r in self._federated_sparql_query(query)]

    def get_categories(self, include_all: bool = False) -> list[str]:
        """Retrieve all categories from the federated network.

        Returns:
            A list of category names.
        """
        return self._get_all_unique("dcat:theme", include_all)

    def get_genres(self, include_all: bool = False) -> list[str]:
        """Retrieve all genres from the federated network.

        Returns:
            A list of genre names.
        """
        return self._get_all_unique("dct:genre", include_all)

    def get_creators(self, include_all: bool = False) -> list[str]:
        """Retrieve all creators from the federated network.

        Returns:
            A list of creator names.
        """
        return self._get_all_unique("dct:creator", include_all)

    def get_data(self) -> list[Data]:
        """Retrieve subscribed data from the federated network.

        Returns:
            A list of `Data` instances.
        """
        resps = self._nyx_get("products")
        return [
            Data(
                name=resp["name"],
                title=resp["title"],
                description=resp["description"],
                url=resp["accessURL"],
                content_type=resp["contentType"],
                creator=resp["creator"],
                org=self.config.org,
            )
            for resp in resps
        ]

    def get_data_by_name(self, name: str) -> Optional[Data]:
        """Retrieve a data based on its unique name.

        Args:
            name (str): The data unique name.

        Returns:
            The `Data` instance identified with the provided name or None if it does not exist.
        """
        resp = self._nyx_get("products/" + name)
        return Data(
            name=resp["name"],
            title=resp["title"],
            description=resp["description"],
            url=resp["accessURL"],
            content_type=resp["contentType"],
            creator=resp["creator"],
            org=self.config.org,
        )

    def update_subscriptions(self):
        """Update the list of subscribed data."""
        # Get all the data we're subscribed to, so the results are relevant to what the user wants
        purchases = self._nyx_get("purchases/transactions")
        if not purchases:
            self.subscribed_data = []
            return
        self.subscribed_data = [k["product_name"] for k in purchases]

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

        resp_download_url = resp.get("downloadURL")
        access_url = resp.get("accessURL")

        if resp_download_url:
            args["download_url"] = resp_download_url

        if access_url:
            args["access_url"] = access_url
        
        return Data(
                name=name,
                title=title,
                description=description,
                org=self.config.org,
                content_type=content_type,
                size=size,
                url=access_url if access_url else resp_download_url,
                creator=self.config.org
        )

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
