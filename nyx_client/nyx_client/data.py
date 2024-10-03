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
    def content_type(self) -> str:
        """Content type (as a simple string, without IANA prefix)."""
        if self._content_type.startswith("http"):
            return self._content_type.split("/")[-1]
        return self._content_type

    @property
    def url(self):
        """The server generated url for brokered access to a subscribed dataset/product."""
        return self._url + f"?buyer_org={self.org}"

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
        self.title = kwargs["title"]
        self._url = kwargs.get("access_url", "")
        if self._url == "":
            self._url = kwargs["download_url"]
        self.org = kwargs.get("org")
        try:
            self._size = int(kwargs.get("size", 0))
        except (ValueError, TypeError):
            self._size = 0
        self.creator = kwargs.get("creator", "unknown")
        self.content = None
        self.name = kwargs.get("name", "unknown")
        self.description = kwargs.get("description", "unkown description")

        if content_type := kwargs.get("mediaType"):
            self._content_type = content_type
        else:
            self._content_type = "unknown"

    def __str__(self):
        return f"Data({self.title}, {self.url}, {self.content_type})"

    def as_string(self) -> str | None:
        """Download the content of the data as as string.

        This method attempts to download the content from the data's URL.

        Returns:
            The downloaded content as decoded text or None, if the download fails.
        """
        try:
            rsp = requests.get(self.url)
            rsp.raise_for_status()
            return rsp.text
        except requests.RequestException as ex:
            log.warning(
                "Failed to download content of data [%s], "
                "confirm the source is still available with the data producer: %s",
                self.title,
                ex,
            )

    def as_bytes(self) -> bytes | None:
        """Download the content of the data as as bytes.

        This method attempts to download the content from the data's URL.

        Returns:
            The downloaded content as bytes or None, if the download fails.
        """
        try:
            rsp = requests.get(self.url)
            rsp.raise_for_status()
            return rsp.content
        except requests.RequestException as ex:
            log.warning(
                "Failed to download content of data [%s], "
                "confirm the source is still available with the data producer: %s",
                self.title,
                ex,
            )
