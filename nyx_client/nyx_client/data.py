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
            name: Unique name of data.
            title: Human readable title of data.
            description: Short description of data.
            org: Your organization name.
            url: The access URL of the data.
            content_type: Content type of the data, can be in format application/json, or URI.
            creator: Org name that created the data.
            categories: The categories of the data.
            genre: The genre of the data.
            size: Size in bytes of the data.

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
