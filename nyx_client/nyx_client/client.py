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
from typing import Any, Dict, Literal, Optional

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
NYX_PURCHASES_TRANSACTIONS_ENDPOINT = "purchases/transactions/"

log = logging.getLogger(__name__)


# not a dataclass?
@dataclass
class NyxClient:
    """A client for interacting with the Nyx system.

    This client provides methods for querying and processing data from Nyx.

    Attributes:
        config (BaseNyxConfig): Configuration for the Nyx client.
    """

    config: BaseNyxConfig

    def __init__(
        self,
        env_file: Optional[str] = None,
        config: Optional[BaseNyxConfig] = None,
    ):
        # TODO: The docstrings shouldn't include types - those are already in the function declarations
        """Initialize a new NyxClient instance.

        Args:
            env_file (Optional[str]): Path to the environment file containing configuration.
            config (Optional[BaseNyxConfig]): Pre-configured BaseNyxConfig object.
        """
        if config:
            self.config = config
        else:
            self.config = BaseNyxConfig(env_file, validate=True)

        self._token = self.config.override_token
        self._refresh = ""

        self._is_setup = False
        # Runtime property from install (or default)?
        # Get like so? https://stackoverflow.com/a/74809114
        self._version = "0.2.0"

    def _setup(self):
        """Set up the client for first contact with API.

        This method is automatically called on first contact with the API to ensure the configuration is set.
        It authorizes the client and sets up user and host information.
        """
        # TODO - do at end of func so not True if has failed
        self._is_setup = True
        self._authorise(refresh=False)

        # Set user nickname
        # Same as NYX_USERNAME in conf?
        self.name = self._nyx_get(NYX_USERS_ME_ENDPOINT).get("name")
        log.debug("successful login as %s", self.name)

        # Get host info
        qapi = self._nyx_get(NYX_AUTH_QAPI_CONNECTION_ENDPOINT)
        self.config.community_mode = qapi.get("community_mode", False)
        self.config.org = f"{qapi['org_name']}/{self.name}" if self.config.community_mode else qapi["org_name"]

    def _authorise(self, refresh=True):
        """Authorize with the configured Nyx instance using basic authorization.

        Args:
            refresh (bool): Whether to refresh the token. Defaults to True.
        """
        if not refresh and self._token:
            # If it's not fresh then we'll return and use the existing token
            return
        resp = self._nyx_post(NYX_AUTH_LOGIN_ENDPOINT, self.config.nyx_auth)
        self._token = resp["access_token"]
        self._refresh = resp["refresh_token"]

    @ensure_setup
    @auth_retry
    def _nyx_post(
        self, endpoint: str, data: dict, headers: Optional[dict] = None, multipart: Optional[MultipartEncoder] = None
    ) -> Dict:
        # TODO - might not always return dict
        # TODO - no typing in Returns
        """Send a POST request to the Nyx API.

        Args:
            endpoint (str): The API endpoint to send the request to.
            data (dict): The data to send in the request body.
            headers (Optional[dict]): Additional headers to include in the request.
            multipart (Optional[MultipartEncoder]): Multipart encoder for file uploads.

        Returns:
            Dict: The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        if not headers:
            # content type to always be provided? (share common headerts with get)
            headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json", "sdk-version": self._version}

        headers["authorization"] = "Bearer " + self._token
        resp = requests.post(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        # TODO: The end user would have to look inside HTTPError.response.(text|json) to get the actual reason for
        # the failure rather than generic http error.
        # This doesn't seem very friendly. We should probably make it easier than that.
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_patch(
        self, endpoint: str, data: dict, headers: Optional[dict] = None, multipart: Optional[MultipartEncoder] = None
    ) -> Dict:
        """Send a PATCH request to the Nyx API.

        Args:
            endpoint (str): The API endpoint to send the request to.
            data (dict): The data to send in the request body.
            headers (Optional[dict]): Additional headers to include in the request.
            multipart (Optional[MultipartEncoder]): Multipart encoder for file uploads.

        Returns:
            Dict: The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        if not headers:
            headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json", "sdk-version": self._version}

        headers["authorization"] = "Bearer " + self._token
        resp = requests.patch(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=headers,
        )
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    # The response is not just Dict - it could be Dict/str/number/list/bool
    def _nyx_get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Send a GET request to the Nyx API.

        Args:
            endpoint (str): The API endpoint to send the request to.
            params (Optional[dict]): Query parameters to include in the request.

        Returns:
            The decoded JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        # Content type not relevant to GET
        # TODO - get not JSON?
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json", "sdk-version": self._version}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.get(url=self.config.nyx_url + NYX_API_BASE_URL + endpoint, headers=headers, params=params)
        resp.raise_for_status()
        return resp.json()

    @ensure_setup
    @auth_retry
    def _sparql_query(self, query: str, scope: Literal["local", "global"]) -> list[Dict[str, str]]:
        """Execute a SPARQL query and process the results.

        Args:
            query (str): The SPARQL query string.
            scope (Literal["local", "global"]): The scope of the query (LOCAL or GLOBAL).

        Returns:
            list[Dict[str, str]]: A list of dictionaries representing the query results.

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
            list[str]: A list of category names.
        """
        return self._nyx_get(NYX_META_CATEGORIES_ENDPOINT)

    def genres(self) -> list[str]:
        """Retrieve all genres from the federated network.

        Returns:
            list[str]: A list of genre names.
        """
        return self._nyx_get(NYX_META_GENRES_ENDPOINT)

    def creators(self) -> list[str]:
        """Retrieve all creators from the federated network.

        Returns:
            list[str]: A list of creator names.
        """
        return self._nyx_get(NYX_META_CREATORS_ENDPOINT)

    def content_types(self) -> list[str]:
        """Retrieve all content Types from the federated network.

        Returns:
            list[str]: A list of content types.
        """
        return self._nyx_get(NYX_META_CONTENT_TYPES_ENDPOINT)

    def licenses(self) -> list[str]:
        """Retrieve all licenses from the federated network.

        Returns:
            list[str]: A list of licenses.
        """
        return self._nyx_get(NYX_META_LICENSES_ENDPOINT)

    def search(
        self,
        categories: Optional[list[str]] = None,
        genre: Optional[str] = None,
        creator: Optional[str] = None,
        text: Optional[str] = None,
        license: Optional[str] = None,
        content_type: Optional[str] = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
        timeout: int = 3,
    ) -> list[Data]:
        """Search for new data in the Nyx system.

        Args:
            categories (Optional[list[str]]): List of categories to filter by.
            genre (Optional[str]): Genre to filter by.
            creator (Optional[str]): Creator to filter by.
            text (Optional[str]): Text to search for.
            license (Optional[str]): License to filter by.
            content_type (Optional[str]): Content type to filter by.
            subscription_state (Literal["subscribed", "all", "not-subscribed"]): Subscription state to filter by.
            timeout (int): Timeout for the search request in seconds.

        Returns:
            list[Data]: A list of `Data` instances matching the search criteria.
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
                org=self.config.org,
                categories=resp["categories"],
                genre=resp["genre"],
            )
            for resp in resps
        ]

    # TODO - shorthand to get subs?
    # TODO - shorthand for getting own (created) data? (local + own org)
    def get_data(
        self,
        categories: Optional[list[str]] = None,
        genre: Optional[str] = None,
        creator: Optional[str] = None,
        license: Optional[str] = None,
        content_type: Optional[str] = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
    ) -> list[Data]:
        """Retrieve subscribed data from the federated network.

        Args:
            categories (Optional[list[str]]): List of categories to filter by.
            genre (Optional[str]): Genre to filter by.
            creator (Optional[str]): Creator to filter by.
            license (Optional[str]): License to filter by.
            content_type (Optional[str]): Content type to filter by.
            subscription_state (Literal["subscribed", "all", "not-subscribed"]): Subscription state to filter by.

        Returns:
            list[Data]: A list of `Data` instances matching the criteria.
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
                org=self.config.org,
                categories=resp["categories"],
                genre=resp["genre"],
            )
            for resp in resps
        ]

    def get_data_by_name(self, name: str) -> Optional[Data]:
        """Retrieve a data based on its unique name.

        Args:
            name (str): The data unique name.

        Returns:
            Optional[Data]: The `Data` instance identified with the provided name or None if it does not exist.
        """
        resp = self._nyx_get(f"{NYX_PRODUCTS_ENDPOINT}/{name}")
        return Data(
            name=resp["name"],
            title=resp["title"],
            description=resp["description"],
            url=resp["accessURL"],
            content_type=resp["contentType"],
            creator=resp["creator"],
            org=self.config.org,
            categories=resp["categories"],
            genre=resp["genre"],
        )

    @ensure_setup
    @auth_retry
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
        # default None (since can have no price) and also price is in dollars ), not cents.
        # the diff between 0 & None might be that the former triggers a purchase flow whilst the latter doesn't
        price: int = 0,
        # Default should be no license? (like in UI)
        license_url: str = "https://creativecommons.org/publicdomain/zero/1.0/",
    ) -> Data:
        """Create new data in the system.

        Args:
            name (str): The unique identifier for the data.
            title (str): The display title of the data.
            description (str): A detailed description of the data.
            size (int): The size of the data, typically in bytes.
            genre (str): The genre or category of the data.
            categories (list[str]): A list of categories the data belongs to.
            download_url (str): The URL where the data can be downloaded.
            content_type (str): The mime type of the data located at download_url.
            lang (str, optional): The language of the data. Defaults to "en".
            status (str, optional): The publication status of the data. Defaults to "published".
            preview (str, optional): A preview or sample of the data. Defaults to an empty string.
            price (int, optional): The price of the data in cents. If 0, the data is free. Defaults to 0.
            license_url (str, optional): The URL of the license for the data. Defaults to Creative Commons Zero.

        Returns:
            Data: A `Data` instance, containing the download URL and title.

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

        resp = self._nyx_post(NYX_PRODUCTS_ENDPOINT, data, headers, multipart_data)

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
            # TODO - the access url will never be empty
            url=access_url if access_url else resp_download_url,
            creator=self.config.org,
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
        price: int = 0,
        license_url: str = "https://creativecommons.org/publicdomain/zero/1.0/",
    ) -> Data:
        """Updates existing data in the system.

        Args:
            name (str): The unique identifier for the data.
            title (str): The display title of the data.
            description (str): A detailed description of the data.
            size (int): The size of the data, typically in bytes.
            genre (str): The genre or category of the data.
            categories (list[str]): A list of categories the data belongs to.
            download_url (str): The URL where the data can be downloaded.
            content_type (str): The mime type of the data located at download_url.
            lang (str, optional): The language of the data. Defaults to "en".
            status (str, optional): The publication status of the data. Defaults to "published".
            preview (str, optional): A preview or sample of the data. Defaults to an empty string.
            price (int, optional): The price of the data in cents. If 0, the data is free. Defaults to 0.
            license_url (str, optional): The URL of the license for the data. Defaults to Creative Commons Zero.

        Returns:
            Data: A `Data` instance, containing the updated information.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        input_bytes = preview.encode("utf-8")
        base64_bytes = base64.b64encode(input_bytes)
        preview_base64_string = base64_bytes.decode("utf-8")

        data = {
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

        resp = self._nyx_patch(f"{NYX_PRODUCTS_ENDPOINT}/{name}", data, headers, multipart_data)

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
            creator=self.config.org,
            categories=resp["categories"],
            genre=resp["genre"],
        )

    def delete_data(self, product: Data):
        """Delete the provided data from Nyx.

        Args:
            product (Data): The data to delete.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self.delete_data_by_name(product.name)

    @ensure_setup
    @auth_retry
    def delete_data_by_name(self, name: str):
        """Delete the data uniquely identified by the provided name from Nyx.

        Args:
            name (str): The data unique name.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.delete(
            url=self.config.nyx_url + NYX_API_BASE_URL + f"{NYX_PRODUCTS_ENDPOINT}/{name}",
            headers=headers,
        )
        resp.raise_for_status()

    @ensure_setup
    def subscribe(self, data: Data):
        """Subscribe to the data.

        Args:
            data (Data): The data object to subscribe to.

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
            data (Data): The data object to unsubscribe from.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": "application/json"}
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        resp = requests.delete(
            url=self.config.nyx_url + NYX_API_BASE_URL + f"{NYX_PURCHASES_TRANSACTIONS_ENDPOINT}{data.creator}/{data.name}",
            headers=headers,
        )
        resp.raise_for_status()
