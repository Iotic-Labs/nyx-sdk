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
from collections.abc import Sequence

import requests

from nyx_client.property import Property

log = logging.getLogger(__name__)


class Data:
    """Represents the data in the Nyx system.

    This class encapsulates the information and functionality related to the data
    in the Nyx system, including its metadata and content retrieval.
    """

    name: str
    """Unique name of data."""
    title: str
    """Human readable title of data."""
    description: str
    """Short description of data."""
    org: str
    """Your organization name."""
    url: str
    """The access URL of the data."""
    content_type: str
    """Content type of the data, can be in format application/json, or URI."""
    creator: str
    """Org name that created the data."""
    categories: list[str]
    """The categories of the data."""
    genre: str
    """The genre of the data."""
    size: int
    """Size in bytes of the data."""
    custom_metadata: list[Property]
    """Additional metadata properties to decorate the data with. Note that nyx-internal properties are not allowed.
    """
    connection_id: str | None
    """The ID of the connection (id from :class`.Connection`)"""

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
        custom_metadata: Sequence[Property] = (),
        connection_id: str | None = None,
    ):
        """Initialize a Data instance.

        Raises:
            KeyError: If any of the required fields are missing.
        """
        self.name = name
        self.title = title
        self.description = description
        self.org = org
        self.url = url + f"?buyer_org={self.org}"
        self.content_type = content_type
        if content_type.startswith("http"):
            self.content_type = content_type.split("/")[-1]
        self.size = size
        self.creator = creator
        self.categories = categories
        self.genre = genre
        self.custom_metadata = list(custom_metadata)
        self.connection_id = connection_id

    def __str__(self):
        """Return a string representation of the Data instance."""
        return f"Data({self.title}, {self.url}, {self.content_type})"

    def as_string(self) -> str | None:
        """Download the content of the data as a string.

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
            return None

    def as_bytes(self) -> bytes | None:
        """Download the content of the data as bytes.

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
            return None
