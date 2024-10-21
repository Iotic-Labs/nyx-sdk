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
import importlib.metadata
import json
import logging
from typing import Any, Dict, Literal

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from nyx_client.configuration import BaseNyxConfig
from nyx_client.data import Data
from nyx_client.utils import auth_retry, ensure_setup

# Constants for URLs
NYX_API_BASE_URL = "/api/portal/"
NYX_AUTH_LOGIN_ENDPOINT = "auth/login"
NYX_USERS_ME_ENDPOINT = "users/me"
NYX_AUTH_QAPI_CONNECTION_ENDPOINT = "auth/qapi-connection"
NYX_META_SPARQL_ENDPOINT = "meta/sparql/"
NYX_META_CATEGORIES_ENDPOINT = "meta/categories"
NYX_META_GENRES_ENDPOINT = "meta/genres"
NYX_META_CREATORS_ENDPOINT = "meta/creators"
NYX_META_CONTENT_TYPES_ENDPOINT = "meta/contentTypes"
NYX_META_LICENSES_ENDPOINT = "meta/licenseURLs"
NYX_PRODUCTS_ENDPOINT = "products"
NYX_META_SEARCH_TEXT_ENDPOINT = "meta/search/text"
NYX_PURCHASES_TRANSACTIONS_ENDPOINT = "purchases/transactions"

log = logging.getLogger(__name__)


class NyxClient:
    """A client for interacting with the Nyx system.

    This client provides methods for querying and processing data from Nyx.

    Attributes:
        config: Configuration for the Nyx client.
    """

    config: BaseNyxConfig

    def __init__(
        self,
        config: BaseNyxConfig | None = None,
    ):
        """Initialize a new NyxClient instance.

        Args:
            config: Pre-configured BaseNyxConfig object.
        """
        if config:
            self.config = config
        else:
            self.config = BaseNyxConfig.from_env()

        self._token = self.config.override_token
        self._refresh = ""

        self._is_setup = False

        # If an override token is set, then we do not need to setup
        if self._token:
            self._is_setup = True
        self._version = importlib.metadata.version("nyx-client")

    def _setup(self):
        """Set up the client for first contact with API.

        This method is automatically called on first contact with the API to ensure the configuration is set.
        It authorizes the client and sets up user and host information.
        """
        # This is set at the start so API calls don't re-call setup
        self._is_setup = True
        try:
            self._authorise(refresh=False)

            # Set user nickname
            self.name = self._nyx_get(NYX_USERS_ME_ENDPOINT).get("name")
            log.debug("successful login as %s", self.name)

            # Get host info
            qapi = self._nyx_get(NYX_AUTH_QAPI_CONNECTION_ENDPOINT)
            self.community_mode = qapi.get("community_mode", False)
            self.org = f"{qapi['org_name']}/{self.name}" if self.community_mode else qapi["org_name"]
        except:
            self._is_setup = False
            raise

    def _authorise(self, refresh=True):
        """Authorize with the configured Nyx instance using basic authorization.

        Args:
            refresh: Whether to refresh the token.
        """
        if not refresh and self._token is not None:
            # If it's not fresh then we'll return and use the existing token
            return
        resp = self._nyx_post(NYX_AUTH_LOGIN_ENDPOINT, self.config.nyx_auth)
        self._token = resp["access_token"]
        self._refresh = resp["refresh_token"]

    def _common_headers(self) -> Dict:
        """Return common headers for API requests."""
        return {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json", "sdk-version": self._version}

    @ensure_setup
    @auth_retry
    def _nyx_post(
        self, endpoint: str, data: dict, headers: dict | None = None, multipart: MultipartEncoder | None = None
    ):
        """Send a POST request to the Nyx API.

        Args:
            endpoint: The API endpoint to send the request to.
            data: The data to send in the request body.
            headers: Additional headers to include in the request.
            multipart: Multipart encoder for file uploads.

        Returns:
            The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        if not headers:
            headers = self._common_headers()

        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.post(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        if resp.status_code == 400:
            log.warning(resp.json())
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_patch(
        self, endpoint: str, data: dict, headers: dict | None = None, multipart: MultipartEncoder | None = None
    ):
        """Send a PATCH request to the Nyx API.

        Args:
            endpoint: The API endpoint to send the request to.
            data: The data to send in the request body.
            headers: Additional headers to include in the request.
            multipart: Multipart encoder for file uploads.

        Returns:
            The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        if not headers:
            headers = self._common_headers()

        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.patch(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        if resp.status_code == 400:
            log.warning(resp.json())
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_get(self, endpoint: str, params: dict | None = None):
        """Send a GET request to the Nyx API.

        Args:
            endpoint: The API endpoint to send the request to.
            params: Query parameters to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        headers = self._common_headers()
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.get(url=self.config.nyx_url + NYX_API_BASE_URL + endpoint, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_delete(self, endpoint: str, params: dict | None = None):
        """Send a DELETE request to the Nyx API.

        Args:
            endpoint: The API endpoint to send the request to.
            params: Query parameters to include in the request.

        Returns:
            The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        headers = self._common_headers()
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.delete(url=self.config.nyx_url + NYX_API_BASE_URL + endpoint, headers=headers, params=params)
        resp.raise_for_status()
        return

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
            requests.HTTPError: If there's an HTTP error during the query execution.
        """
        headers = {
            "X-Requested-With": "nyx-sdk",
            "Content-Type": "application/json",
            "Accept": "application/sparql-results+json",
            "sdk-version": self._version,
        }
        headers["authorization"] = "Bearer " + self._token
        resp = requests.get(
            url=self.config.nyx_url + NYX_API_BASE_URL + NYX_META_SPARQL_ENDPOINT + scope,
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

    def categories(self) -> list[str]:
        """Retrieve all categories from the federated network.

        Returns:
            A list of category names.
        """
        return self._nyx_get(NYX_META_CATEGORIES_ENDPOINT)

    def genres(self) -> list[str]:
        """Retrieve all genres from the federated network.

        Returns:
            A list of genre names.
        """
        return self._nyx_get(NYX_META_GENRES_ENDPOINT)

    def creators(self) -> list[str]:
        """Retrieve all creators from the federated network.

        Returns:
            A list of creator names.
        """
        return self._nyx_get(NYX_META_CREATORS_ENDPOINT)

    def content_types(self) -> list[str]:
        """Retrieve all content Types from the federated network.

        Returns:
            A list of content types.
        """
        return self._nyx_get(NYX_META_CONTENT_TYPES_ENDPOINT)

    def licenses(self) -> list[str]:
        """Retrieve all licenses from the federated network.

        Returns:
            A list of licenses.
        """
        return self._nyx_get(NYX_META_LICENSES_ENDPOINT)

    def search(
        self,
        categories: list[str] | None = None,
        genre: str | None = None,
        creator: str | None = None,
        text: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
        timeout: int = 3,
    ) -> list[Data]:
        """Search for new data in the Nyx system.

        Args:
            categories: List of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            text: Text to search for.
            license: License to filter by.
            content_type: Content type to filter by.
            subscription_state: Subscription state to filter by.
            timeout: Timeout for the search request in seconds.

        Returns:
            A list of `Data` instances matching the search criteria.
        """
        url = NYX_PRODUCTS_ENDPOINT
        params = {"include": subscription_state, "timeout": timeout, "scope": "global"}
        if categories:
            params["category"] = categories
        if genre:
            params["genre"] = genre
        if creator:
            params["creator"] = creator
        if license:
            params["license"] = license
        if content_type:
            params["contentType"] = content_type
        if text:
            params["text"] = text
            url = NYX_META_SEARCH_TEXT_ENDPOINT

        resps = self._nyx_get(url, params=params)
        return [
            Data(
                name=resp["name"],
                title=resp["title"],
                description=resp["description"],
                url=resp["accessURL"],
                content_type=resp["contentType"],
                creator=resp["creator"],
                org=self.org,
                categories=resp["categories"],
                genre=resp["genre"],
            )
            for resp in resps
        ]

    def my_subscriptions(
        self,
        categories: list[str] | None = None,
        genre: str | None = None,
        creator: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
    ) -> list[Data]:
        """Retrieve only subscribed data from the federated network.

        Args:
            categories: List of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            license: License to filter by.
            content_type: Content type to filter by.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        return self.get_data(categories, genre, creator, license, content_type, "subscribed")

    def my_products(
        self,
        categories: list[str] | None = None,
        genre: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
    ) -> list[Data]:
        """Retrieve products I have created.

        Args:
            categories: List of categories to filter by.
            genre: Genre to filter by.
            license: License to filter by.
            content_type: Content type to filter by.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        return self.get_data(categories, genre, self.org, license, content_type, "all")

    def get_data(
        self,
        categories: list[str] | None = None,
        genre: str | None = None,
        creator: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
    ) -> list[Data]:
        """Retrieve data from the federated network.

        Args:
            categories: List of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            license: License to filter by.
            content_type: Content type to filter by.
            subscription_state: Subscription state to filter by.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        params: dict[str, Any] = {"include": subscription_state, "timeout": 10, "scope": "global"}
        if categories:
            params["category"] = categories
        if genre:
            params["genre"] = genre
        if creator:
            params["creator"] = creator
        if license:
            params["license"] = license
        if content_type:
            params["contentType"] = content_type

        resps = self._nyx_get(NYX_PRODUCTS_ENDPOINT, params=params)
        return [
            Data(
                name=resp["name"],
                title=resp["title"],
                description=resp["description"],
                url=resp["accessURL"],
                content_type=resp["contentType"],
                creator=resp["creator"],
                size=resp["size"],
                org=self.org,
                categories=resp["categories"],
                genre=resp["genre"],
            )
            for resp in resps
        ]

    def get_data_by_name(self, name: str) -> Data:
        """Retrieve a data based on its unique name.

        Args:
            name: The data unique name.

        Returns:
            The `Data` instance identified with the provided name.
        """
        raise NotImplementedError()
        resp = self._nyx_get(f"{NYX_PRODUCTS_ENDPOINT}/{name}")
        return Data(
            name=resp["name"],
            title=resp["title"],
            description=resp["description"],
            url=resp["accessURL"],
            content_type=resp["contentType"],
            creator=resp["creator"],
            org=self.org,
            categories=resp["categories"],
            genre=resp["genre"],
        )

    @ensure_setup
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
        price: int | None = None,
        license_url: str | None = None,
    ) -> Data:
        """Create new data in the system.

        Args:
            name: The unique identifier for the data.
            title: The display title of the data.
            description: A detailed description of the data.
            size: The size of the data, typically in bytes.
            genre: The genre or category of the data.
            categories: A list of categories the data belongs to.
            download_url: The URL where the data can be downloaded.
            content_type: The mime type of the data located at download_url.
            lang: The language of the data.
            status: The publication status of the data.
            preview: A preview or sample of the data.
            price: The price of the data in cents. If 0, the data is free.
            license_url: The URL of the license for the data.

        Returns:
            A `Data` instance, containing the download URL and title.

        Raises:
            requests.HTTPError: If the API request fails.
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
            "contentType": content_type,
        }
        if price:
            data["price"] = price

        if license_url:
            data["licenseURL"] = license_url

        multipart_data = MultipartEncoder(
            fields={
                "productMetadata": json.dumps(data),
            }
        )

        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": multipart_data.content_type}

        resp = self._nyx_post(NYX_PRODUCTS_ENDPOINT, data, headers, multipart_data)

        return Data(
            name=name,
            title=title,
            description=description,
            org=self.org,
            content_type=content_type,
            size=size,
            url=resp.get("accessURL", download_url),
            creator=self.org,
            categories=resp["categories"],
            genre=resp["genre"],
        )

    @ensure_setup
    def update_data(
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
        price: int | None = None,
        license_url: str | None = None,
    ) -> Data:
        """Updates existing data in the system.

        Args:
            name: The unique identifier for the data.
            title: The display title of the data.
            description: A detailed description of the data.
            size: The size of the data, typically in bytes.
            genre: The genre or category of the data.
            categories: A list of categories the data belongs to.
            download_url: The URL where the data can be downloaded.
            content_type: The mime type of the data located at download_url.
            lang: The language of the data.
            status: The publication status of the data.
            preview: A preview or sample of the data.
            price: The price of the data in cents. If 0, the data is free.
            license_url: The URL of the license for the data.

        Returns:
            A `Data` instance, containing the updated information.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        input_bytes = preview.encode("utf-8")
        base64_bytes = base64.b64encode(input_bytes)
        preview_base64_string = base64_bytes.decode("utf-8")

        data = {
            "title": title,
            "name": name,
            "description": description,
            "size": size,
            "genre": genre,
            "categories": categories,
            "lang": lang,
            "status": status,
            "preview": preview_base64_string,
            "downloadURL": download_url,
            "contentType": content_type,
        }
        if price:
            data["price"] = price

        if license_url:
            data["licenseURL"] = license_url

        multipart_data = MultipartEncoder(
            fields={
                "productMetadata": json.dumps(data),
            }
        )

        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": multipart_data.content_type}

        resp = self._nyx_patch(f"{NYX_PRODUCTS_ENDPOINT}/{name}", data, headers, multipart_data)

        return Data(
            name=name,
            title=title,
            description=description,
            org=self.org,
            content_type=content_type,
            size=size,
            url=resp.get("accessURL", download_url),
            creator=self.org,
            categories=resp["categories"],
            genre=resp["genre"],
        )

    def delete_data(self, product: Data):
        """Delete the provided data from Nyx.

        Args:
            product: The data to delete.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self.delete_data_by_name(product.name)

    @ensure_setup
    def delete_data_by_name(self, name: str):
        """Delete the data uniquely identified by the provided name from Nyx.

        Args:
            name: The data unique name.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self._nyx_delete(f"{NYX_PRODUCTS_ENDPOINT}/{name}")

    @ensure_setup
    def subscribe(self, data: Data):
        """Subscribe to the data.

        Args:
            data: The data object to subscribe to.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        body = {
            "product_name": data.name,
            "seller_org": data.creator,
        }

        self._nyx_post(NYX_PURCHASES_TRANSACTIONS_ENDPOINT, body)

    @ensure_setup
    def unsubscribe(self, data: Data):
        """Unsubscribe from the data.

        Args:
            data: The data object to unsubscribe from.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self._nyx_delete(f"{NYX_PURCHASES_TRANSACTIONS_ENDPOINT}/{data.creator}/{data.name}")
