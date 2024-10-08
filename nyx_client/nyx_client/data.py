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
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)


@dataclass
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

    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        org: str,
        url: str,
        content_type: str,
        creator: str,
        categories: list[str],
        genre: str,
        size: int = 0,
    ):
        """Initialize a Data instance.

        Args:
            name: unique name of data.
            title: human readable title of data.
            description: Short description of data.
            org: your organization name
            url: the access URL of the data.
            content_type: content type of the data, can be in format application/json, or URI.
            size: size in bytes of the data.
            genre: the genre of the data
            description: the description of the data
            categories: the categories of the data
            creator: Org name that created the data.

        Raises:
            KeyError: If any of the required fields are missing.
        """
        self.name = name
        self.title = title
        self.description = description
        self.org = org
        self._url = url
        self._content_type = content_type
        self.size = size
        self.creator = creator
        self.categories = categories
        self.genre = genre

    def __str__(self):
        return f"Data({self.title}, {self.url}, {self.content_type})"

    def __repr__(self) -> str:
        return self.__str__()

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
