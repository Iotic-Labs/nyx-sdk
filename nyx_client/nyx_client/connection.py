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

"""Module for connection (3rd party data integrations) definitions in Nyx."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Connection:
    """Represents a connection to a 3rd party data integration."""

    id: str
    """the id of the connection"""
    name: str
    """the name of the connection"""
    json_blob: dict[str, Any]
    """json blob of non sensitive storage config"""
    description: str = ""
    """the description of the connection"""
    allow_update: bool = False
    """boolean to denote if upload is allowed from this connection"""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Connection":
        """Builds a connection object from json.

        Args:
            value: a dictionary of the connection object

        Returns:
            `Connection` object
        """
        return cls(
            name=value["name"],
            id=value["id"],
            json_blob=value["json_blob"],
            description=value.get("description", ""),
            allow_update=value.get("allow_upload", False),
        )

    def as_dict(self) -> dict[str, Any]:
        """Returns the object as a dictionary.

        Returns:
            A dictionary of the connection, that matches POST/PUT requests in the API.

        """
        return asdict(self)
