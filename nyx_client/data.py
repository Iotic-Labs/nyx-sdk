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

"""Module that manages individual Nyx Data."""

import logging

import requests

log = logging.getLogger(__name__)


class Data:
    """Represents the data in the Nyx system.

    This class encapsulates the information and functionality related to the data
    in the Nyx system, including its metadata and content retrieval.
    """

    @property
    def name(self) -> str:
        """The unique name of the product."""
        return self._name

    @property
    def title(self) -> str:
        """The title of the product."""
        return self._title

    @property
    def creator(self) -> str:
        """The creator of the product."""
        return self._creator

    @property
    def description(self) -> str:
        """The description of the data."""
        return self._description

    @property
    def size(self) -> int:
        """The size of the product in bytes."""
        return self._size

    @property
    def content_type(self) -> str:
        """Content type (as a simple string, without IANA prefix)."""
        if self._content_type.startswith("http"):
            return self._content_type.split("/")[-1]
        return self._content_type

    @property
    def url(self):
        """The server generated url for brokered access to a subscribed dataset/product."""
        if not self._access_url:
            return self._download_url
        return self._access_url + f"?buyer_org={self._org}"

    @property
    def content(self) -> str | None:
        """The downloaded content of the product (None if not yet downloaded)."""
        return self._content

    def __init__(self, **kwargs):
        """Initialize a Data instance.

        Args:
            **kwargs: Keyword arguments containing data information.
                Required keys: 'access_url'/'download_url', 'title', 'org'

        Raises:
            KeyError: If any of the required fields are missing.
        """
        if not kwargs.get("title") or not kwargs.get("org"):
            raise KeyError(f"Required fields include 'title' and 'org'. Provided fields: {', '.join(kwargs.keys())}")
        if not (kwargs.get("access_url") or kwargs.get("download_url")):
            raise KeyError(
                f"At least one of 'access_url' or 'download_url' is required. "
                f"Provided fields: {', '.join(kwargs.keys())}"
            )

        self._title = kwargs.get("title")
        self._access_url = kwargs.get("access_url")
        self._download_url = kwargs.get("download_url")
        self._org = kwargs.get("org")
        try:
            self._size = int(kwargs.get("size"))
        except (ValueError, TypeError):
            self._size = 0
        self._creator = kwargs.get("creator")
        self._content = None
        self._name = kwargs.get("name", "unknown")
        self._description = kwargs.get("description", "unkown description")

        if content_type := kwargs.get("mediaType"):
            self._content_type = content_type
        else:
            self._content_type = "unknown"

    def __str__(self):
        return f"Data({self._title}, {self.url}, {self._content_type})"

    def download(self) -> str | None:
        """Download the content of the data and populate the class content field.

        This method attempts to download the content from the data's URL
        and stores it in the `content` attribute.

        Returns:
            The downloaded content as decoded text or None, if the download fails.

        Note:
            If the content has already been downloaded, this method returns the cached content without re-downloading.
        """
        if not self._content:
            try:
                rsp = requests.get(self.url)
                rsp.raise_for_status()
                self._content = rsp.text
            except requests.RequestException as ex:
                log.warning(
                    "Failed to download content of data [%s], "
                    "confirm the source is still available with the data producer: %s",
                    self._title,
                    ex,
                )

        return self._content
