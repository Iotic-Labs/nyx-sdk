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

from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class RemoteHost:
    """Represents a remote host on the network.

    Attributes:
            name: the name of the organization
            did: the did of the remote host
    """

    did: str
    name: str = "Unknown host"

    @classmethod
    def from_json(cls, value: dict):
        """Builds a Remote Host object from json.

        Args:
            value: the json dictionary (returned from API).

        Returns:
            Remote Host object
        """
        return cls(name=value["name"], did=value["did"])


@dataclass
class Circle:
    """Represents a circle, which is a grouping of remote hosts.

    Attributes:
            did: the did of the circle
            name: the name of the circle
            description: optional description of what the circle is
            organizations: optional list of remote organizations in the circle
    """

    name: str
    description: str | None
    did: str | None = None
    organizations: Sequence[RemoteHost] = ()

    @classmethod
    def from_json(cls, value: dict):
        """Builds a circle object from json.

        Args:
            value: the json dictionary (returned from API).

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

    def as_dict(self) -> dict:
        """Returns the object as a dictionary.

        Returns:
            A dictionary of the circle, that matches POST/PUT requests in the API.

        """
        return asdict(self)
