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
from collections.abc import Sequence
from enum import Enum, unique
from io import RawIOBase
from typing import Any, Literal
from urllib.parse import quote_plus

import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from nyx_client.circles import Circle, RemoteHost
from nyx_client.configuration import BaseNyxConfig
from nyx_client.connection import Connection
from nyx_client.data import Data
from nyx_client.ontology import ALLOW_ALL, ALLOW_NONE
from nyx_client.property import Property
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
NYX_CIRCLE_ENDPOINT = "circles"
NYX_ORG_ENDPOINT = "organizations"
NYX_CONNECTIONS_ENDPOINT = "connections"

log = logging.getLogger(__name__)


@unique
class SparqlResultType(str, Enum):
    """Available query result (response) types for SPARQL query."""

    SPARQL_JSON = "application/sparql-results+json"
    SPARQL_XML = "application/sparql-results+xml"
    SPARQL_CSV = ("text/csv",)
    RDF_NTRIPLES = "application/n-triples"
    RDF_TURTLE = "text/turtle"
    RDF_XML = "application/rdf+xml"

    def __str__(self) -> str:
        return self.value


class NyxClient:
    """A client for interacting with the Nyx system.

    This client provides methods for querying and processing data from Nyx.
    """

    config: BaseNyxConfig
    """Configuration for the Nyx client."""
    org: str
    """Your organization name on Nyx."""
    name: str
    """Your Nyx Username."""
    community_mode: bool
    """If you're using community mode."""

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

        self._base_headers: dict[str, str] = {
            "X-Requested-With": "nyx-sdk",
            "X-Client-Type": "nyx-sdk",
            "sdk-version": self._version,
        }

        self.org = ""
        self.name = ""
        self.community_mode = False

    def _setup(self):
        """Set up the client for first contact with API.

        This method is automatically called on first contact with the API to ensure the configuration is set.
        It authorizes the client and sets up user and host information.
        """
        # This is set at the start so API calls don't re-call setup
        self._is_setup = True
        self._authorise(refresh=False)

        # Set user nickname
        self.name = self._nyx_get(NYX_USERS_ME_ENDPOINT).get("name")
        log.debug("successful login as %s", self.name)

        # Get host info
        qapi = self._nyx_get(NYX_AUTH_QAPI_CONNECTION_ENDPOINT)
        self.community_mode = qapi.get("community_mode", False)
        self.org = f"{qapi['org_name']}/{self.name}" if self.community_mode else qapi["org_name"]

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

    def _make_headers(
        self, content_type: str = "application/json", extra_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Return common headers for API requests combined with the provided ones."""
        headers = self._base_headers.copy()
        headers["Content-Type"] = content_type
        if self._token:
            headers["authorization"] = "Bearer " + self._token
        if extra_headers:
            headers.update(extra_headers)
        return headers

    @ensure_setup
    @auth_retry
    def _nyx_post(
        self,
        endpoint: str,
        data: dict,
        headers: dict[str, str] | None = None,
        multipart: MultipartEncoder | None = None,
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
        resp = requests.post(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=self._make_headers(
                content_type="multipart/form-data" if multipart else "application/json", extra_headers=headers
            ),
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
        resp = requests.patch(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data if data else None,
            data=multipart if multipart else None,
            headers=self._make_headers(
                content_type="multipart/form-data" if multipart else "application/json", extra_headers=headers
            ),
        )
        if resp.status_code == 400:
            log.warning(resp.json())
        resp.raise_for_status()

        return resp.json()

    @ensure_setup
    @auth_retry
    def _nyx_put(self, endpoint: str, data: dict):
        """Send a PUT request to the Nyx API.

        Args:
            endpoint: The API endpoint to send the request to.
            data: The data to send in the request body.

        Returns:
            The JSON response from the API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        resp = requests.put(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint,
            json=data,
            headers=self._make_headers(),
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
        resp = requests.get(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint, headers=self._make_headers(), params=params
        )
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
        resp = requests.delete(
            url=self.config.nyx_url + NYX_API_BASE_URL + endpoint, headers=self._make_headers(), params=params
        )
        resp.raise_for_status()

    @ensure_setup
    @auth_retry
    def sparql_query(
        self, query: str, result_type: SparqlResultType = SparqlResultType.SPARQL_JSON, local_only: bool = False
    ) -> str:
        """Execute a SPARQL query and process the results.

        NOTE: This method is experimental and its definition might change without notice!

        Args:
            query: A SPARQL 1.1 query string.
            result_type: The result format for the query.
            local_only: Whether to only query the local Nyx instance as opposed to the whole Nyx network.

        Returns:
            A string of the result in the specified format

        Raises:
            requests.HTTPError: If there's an HTTP error during the query execution.
        """
        resp = requests.post(
            url=(
                self.config.nyx_url
                + NYX_API_BASE_URL
                + NYX_META_SPARQL_ENDPOINT
                + ("local" if local_only else "global")
            ),
            headers=self._make_headers(content_type="application/sparql-query", extra_headers={"Accept": result_type}),
            data=query,
        )
        resp.raise_for_status()
        return resp.text

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

    def _data_from_response_object(self, obj: dict[str, Any]) -> Data:
        """Constructs a new `Data` instance for an object contained in an API response."""
        return Data(
            name=obj["name"],
            title=obj["title"],
            description=obj["description"],
            org=self.org,
            url=obj["accessURL"],
            content_type=obj["contentType"],
            creator=obj["creator"],
            categories=obj["categories"],
            genre=obj["genre"],
            size=obj["size"],
            custom_metadata=(Property.from_dict(prop) for prop in obj.get("customMetadata", ())),
            connection_id=obj.get("connectionId"),
        )

    def search(
        self,
        text: str,
        *,
        categories: Sequence[str] = (),
        genre: str | None = None,
        creator: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
        timeout: int = 3,
        local_only: bool = False,
    ) -> list[Data]:
        """Find products using text in the Nyx network (or local instance).

        Usage of this endpoint is discouraged. Use :func:`get_data` instead, unless you want to perform a text search.

        Args:
            text: Text to search for.
            categories: Sequence of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            license: License to filter by.
            content_type: Content type to filter by.
            subscription_state: Subscription state to filter by.
            timeout: Timeout for the search request in seconds.
            local_only: Whether to only search for data defined in the local Nyx instance as opposed to the whole Nyx
                network.

        Returns:
            A list of `Data` instances matching the search criteria.
        """
        params = {
            "text": text,
            "include": subscription_state,
            "timeout": timeout,
            "scope": "local" if local_only else "global",
        }
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

        resps = self._nyx_get(NYX_META_SEARCH_TEXT_ENDPOINT, params=params)
        return [self._data_from_response_object(obj) for obj in resps]

    def my_subscriptions(
        self,
        *,
        categories: Sequence[str] = (),
        genre: str | None = None,
        creator: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
    ) -> list[Data]:
        """Retrieve only subscribed data from the federated network.

        Args:
            categories: Sequence of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            license: License to filter by.
            content_type: Content type to filter by.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        return self.get_data(
            categories=categories,
            genre=genre,
            creator=creator,
            license=license,
            content_type=content_type,
            subscription_state="subscribed",
        )

    def my_data(
        self,
        categories: Sequence[str] = (),
        genre: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
    ) -> list[Data]:
        """Retrieve data I have created.

        Args:
            categories: Sequence of categories to filter by.
            genre: Genre to filter by.
            license: License to filter by.
            content_type: Content type to filter by.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        return self.get_data(
            categories=categories,
            genre=genre,
            creator=self.org,
            license=license,
            content_type=content_type,
            subscription_state="all",
            local_only=True,
        )

    def get_data(
        self,
        *,
        categories: Sequence[str] = (),
        genre: str | None = None,
        creator: str | None = None,
        license: str | None = None,
        content_type: str | None = None,
        subscription_state: Literal["subscribed", "all", "not-subscribed"] = "all",
        local_only: bool = False,
    ) -> list[Data]:
        """Find products in the Nyx network (or local instance).

        Args:
            categories: Sequence of categories to filter by.
            genre: Genre to filter by.
            creator: Creator to filter by.
            license: License to filter by.
            content_type: Content type to filter by.
            subscription_state: Subscription state to filter by.
            local_only: Whether to only interrogate data defined in the local Nyx instance as opposed to the whole Nyx
                network.

        Returns:
            A list of `Data` instances matching the criteria.
        """
        params: dict[str, Any] = {
            "include": subscription_state,
            "timeout": 10,
            "scope": "local" if local_only else "global",
        }
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
        return [self._data_from_response_object(obj) for obj in resps]

    def get_my_data_by_name(self, name: str) -> Data:
        """Retrieve your own data based on its unique name.

        This only works on data you own

        Args:
            name: The data unique name (unique per organization).

        Returns:
            Your `Data` instance identified with the provided name.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        resp = self._nyx_get(f"{NYX_PRODUCTS_ENDPOINT}/{name}")
        return self._data_from_response_object(resp)

    @ensure_setup
    def create_data(
        self,
        name: str,
        title: str,
        description: str,
        genre: str,
        categories: Sequence[str],
        content_type: str,
        lang: str = "en",
        status: str = "published",
        preview: str = "",
        size: int | None = None,
        price: int | None = None,
        license_url: str | None = None,
        download_url: str | None = None,
        file: RawIOBase | None = None,
        access_control: Literal["all", "none"] | None = None,
        circles: Sequence[Circle] = (),
        custom_metadata: Sequence[Property] = (),
        connection_id: str | None = None,
    ) -> Data:
        """Create new data in the system.

        Args:
            name: The unique identifier for the data.
            title: The display title of the data.
            description: A detailed description of the data.
            size: Approximate size of the data, if a file is provided the size will be calculated
            genre: The genre or category of the data.
            categories: A list of categories the data belongs to.
            download_url: The URL where the data can be downloaded.
            file: the file like object (RawIOBase) that you wish to upload
            content_type: The mime type of the data located at download_url.
            lang: The language of the data.
            status: The publication status of the data.
            preview: A preview or sample of the data.
            price: The price of the data in cents. If 0, the data is free.
            license_url: The URL of the license for the data.
            access_control: Either allow all, or allow none
            circles: A list of circles to add share the data with
            custom_metadata: Additional metadata properties to decorate the data with. Note that nyx-internal properties
                are not allowed.
            connection_id: the id of a connection to use (id from :class:`nyx_client.connection.Connection`)

        Returns:
            A `Data` instance, containing the download URL and title.

        Raises:
            requests.HTTPError: If the API request fails.
            ValueError: When download_url and file are both provided or both missing
        """
        if not download_url and not file:
            raise ValueError("Either download_url or file should be supplied")

        if access_control and circles:
            raise ValueError("Both access_control and circles should not be supplied together")

        if download_url and file:
            raise ValueError("both download_url and file should not be supplied together")

        input_bytes = preview.encode("utf-8")
        base64_bytes = base64.b64encode(input_bytes)
        preview_base64_string = base64_bytes.decode("utf-8")

        data = {
            "name": name,
            "title": title,
            "description": description,
            "genre": genre,
            "categories": categories,
            "lang": lang,
            "status": status,
            "preview": preview_base64_string,
            "contentType": content_type,
            "customMetadata": [prop.as_dict() for prop in custom_metadata],
        }
        if price:
            data["price"] = price
        if download_url:
            data["downloadURL"] = download_url
            data["size"] = size
        if license_url:
            data["licenseURL"] = license_url
        if access_control == "all":
            data["accessControl"] = [ALLOW_ALL]
        elif access_control == "none":
            data["accessControl"] = [ALLOW_NONE]

        if connection_id:
            data["connectionId"] = connection_id

        if circles:
            data["circles"] = [c.did for c in circles]

        # We need to specify either access control or one circle
        if len(circles) == 0 and access_control is None:
            data["accessControl"] = [ALLOW_NONE]

        fields = {
            "productMetadata": json.dumps(data),
        }

        if file:
            fields["productData"] = (name, file, content_type)

        multipart_data = MultipartEncoder(fields=fields)

        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": multipart_data.content_type}

        resp = self._nyx_post(NYX_PRODUCTS_ENDPOINT, data, headers=headers, multipart=multipart_data)

        return self._data_from_response_object(resp)

    @ensure_setup
    def update_data(
        self,
        name: str,
        title: str,
        description: str,
        genre: str,
        categories: Sequence[str],
        content_type: str,
        lang: str = "en",
        status: str = "published",
        preview: str = "",
        size: int | None = None,
        price: int | None = None,
        license_url: str | None = None,
        download_url: str | None = None,
        file: RawIOBase | None = None,
        access_control: Literal["all", "none"] | None = None,
        circles: Sequence[Circle] = (),
        custom_metadata: Sequence[Property] = (),
        connection_id: str | None = None,
    ) -> Data:
        """Updates existing data in the system.

        Args:
            name: The unique identifier for the data.
            title: The display title of the data.
            description: A detailed description of the data.
            size: Approximate size of the data, if a file is provided the size will be calculated
            genre: The genre or category of the data.
            categories: A list of categories the data belongs to.
            download_url: The URL where the data can be downloaded.
            file: the file like object (RawIOBase) that you wish to upload
            content_type: The mime type of the data located at download_url.
            lang: The language of the data.
            status: The publication status of the data.
            preview: A preview or sample of the data.
            price: The price of the data in cents. If 0, the data is free.
            license_url: The URL of the license for the data.
            access_control: Either allow all, or allow none
            circles: A list of circles to add share the data with
            custom_metadata: Additional metadata properties to decorate the data with. Note that nyx-internal properties
                are not allowed.
            connection_id: the id of a connection to use

        Returns:
            A `Data` instance, containing the updated information.

        Raises:
            requests.HTTPError: If the API request fails.
            ValueError: When download_url and file are both provided or both missing
        """
        if not download_url and not file:
            raise ValueError("Either download_url or file should be supplied")

        if access_control and circles:
            raise ValueError("Both access_control and circles should not be supplied together")

        if download_url and file:
            raise ValueError("both download_url and file should not be supplied together")

        input_bytes = preview.encode("utf-8")
        base64_bytes = base64.b64encode(input_bytes)
        preview_base64_string = base64_bytes.decode("utf-8")

        data = {
            "name": name,
            "title": title,
            "description": description,
            "genre": genre,
            "categories": categories,
            "lang": lang,
            "status": status,
            "preview": preview_base64_string,
            "contentType": content_type,
            "customMetadata": [prop.as_dict() for prop in custom_metadata],
        }
        if price:
            data["price"] = price
        if download_url:
            data["downloadURL"] = download_url
            data["size"] = size
        if license_url:
            data["licenseURL"] = license_url
        if access_control == "all":
            data["accessControl"] = [ALLOW_ALL]
        elif access_control == "none":
            data["accessControl"] = [ALLOW_NONE]

        if connection_id:
            data["connectionId"] = connection_id

        if circles:
            data["circles"] = [c.did for c in circles]

        # We need to specify either access control or one circle
        if len(circles) == 0 and access_control is None:
            data["accessControl"] = [ALLOW_NONE]

        fields = {
            "productMetadata": json.dumps(data),
        }

        if file:
            fields["productData"] = (name, file, content_type)

        multipart_data = MultipartEncoder(fields=fields)

        headers = {"X-Requested-With": "nyx-sdk", "Content-Type": multipart_data.content_type}

        resp = self._nyx_patch(f"{NYX_PRODUCTS_ENDPOINT}/{name}", data, headers, multipart_data)

        return self._data_from_response_object(resp)

    def delete_data(self, data: Data):
        """Delete the provided data from Nyx.

        Args:
            data: The data to delete.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self.delete_data_by_name(data.name)

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
        # Creator is expected to be double encoded
        creator = quote_plus(quote_plus(data.creator))
        self._nyx_delete(f"{NYX_PURCHASES_TRANSACTIONS_ENDPOINT}/{creator}/{data.name}")

    def organizations(self) -> list[RemoteHost]:
        """Get a list of all organizations in the federated network.

        Returns:
            A list of `RemoteHost` objects

        Raises:
            requests.HTTPError: if the API request fails.
        """
        raw_orgs = self._nyx_get(NYX_ORG_ENDPOINT)
        return [RemoteHost.from_dict(org) for org in raw_orgs]

    def get_circles(self) -> list[Circle]:
        """Get a list of circles.

        Returns:
            A list of `Circle` objects

        Raises:
            requests.HTTPError: if the API request fails.
        """
        circles_raw = self._nyx_get(NYX_CIRCLE_ENDPOINT)
        return [Circle.from_dict(r) for r in circles_raw]

    def get_circle_by_name(self, circle_name: str) -> Circle:
        """Get a list of circles.

        Args:
            circle_name: The name of the circle to get.

        Returns:
            A `Circle` object

        Raises:
            requests.HTTPError: if the API request fails.
        """
        circle_raw = self._nyx_get(NYX_CIRCLE_ENDPOINT + "/" + circle_name)
        return Circle.from_dict(circle_raw)

    def create_circle(self, circle: Circle) -> Circle:
        """Create a circle.

        Args:
            circle: The circle to be created.

        Returns:
            An updated `Circle` object

        Raises:
            requests.HTTPError: If the API request fails.
        """
        circle_json = circle.as_dict()
        circle_json.pop("did")
        resp = self._nyx_post(NYX_CIRCLE_ENDPOINT, data=circle_json)

        circle.did = resp["did"]
        return circle

    def update_circle(self, circle: Circle):
        """Updates a circle, based on the cirle's name.

        Args:
            circle: The circle to be updated.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        circle_json = circle.as_dict()
        self._nyx_put(f"{NYX_CIRCLE_ENDPOINT}/{circle.name}", data=circle_json)

    def delete_circle_by_name(self, circle_name: str):
        """Deletes a circle.

        Args:
            circle_name: The name of the circle to be deleted.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self._nyx_delete(f"{NYX_CIRCLE_ENDPOINT}/{circle_name}")

    def delete_circle(self, circle: Circle):
        """Deletes a circle.

        Args:
            circle: The circle to be deleted.

        Raises:
            requests.HTTPError: If the API request fails.
        """
        self.delete_circle_by_name(circle.name)

    def get_connections(self, allow_upload: bool | None = None) -> list[Connection]:
        """Lists all connections.

        Args:
            allow_upload: Filter the connections by allow_upload, defaults to show all.

        Returns:
            A list of `Connection` objects

        Raises:
            requests.HTTPError: if the API request fails.
        """
        params = {"allow_upload": allow_upload} if allow_upload is not None else None
        connections = self._nyx_get(NYX_CONNECTIONS_ENDPOINT, params=params)

        return [Connection.from_dict(c) for c in connections]
