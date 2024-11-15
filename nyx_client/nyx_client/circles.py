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

"""Module for Circles-related (i.e. ACL) definitions in Nyx."""

from dataclasses import asdict, dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class RemoteHost:
    """Represents a remote host on the network."""

    did: str
    """the name of the organization"""
    name: str = ""
    """the name of the organization"""

    @classmethod
    def from_dict(cls, value: dict) -> "RemoteHost":
        """Builds a Remote Host object from json.

        Args:
            value: a dictionary of the organization object

        Returns:
            `RemoteHost` object
        """
        return cls(name=value["name"], did=value["did"])


@dataclass
class Circle:
    """Represents a circle, which is a grouping of remote hosts."""

    name: str
    """The name of the circle, this must be unique within your instance."""
    description: str | None = None
    """Optional description of what the circle is."""
    did: str | None = None
    """The did of the circle."""
    organizations: Sequence[RemoteHost] = ()
    """Optional list of remote organizations in the circle."""

    @classmethod
    def from_dict(cls, value: dict) -> "Circle":
        """Builds a circle object from json.

        Args:
            value: a dictionary of the circle object

        Returns:
            Circle object
        """
        allowed_hosts: list[RemoteHost] = []
        for raw_host in value.get("organizations", ()):
            allowed_hosts.append(RemoteHost(did=raw_host["did"], name=raw_host["name"]))
        return cls(
            did=value["did"],
            name=value["name"],
            description=value.get("description"),
            organizations=allowed_hosts,
        )

    def as_dict(self) -> dict[str, Any]:
        """Returns the object as a dictionary.

        Returns:
            A dictionary of the circle, that matches POST/PUT requests in the API.

        """
        return asdict(self)
