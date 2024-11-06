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

class RemoteHost:
    """Represents a remote host on the network"""

    def __init__(self, name: str, did: str):
        self.name = name
        self.did = did

    def __repr__(self):
        return f"RemoteHost({self.name}, {self.did})"

class Circle:
    """Represents a circle, which is a grouping of remote hosts
    """

    def __init__(self, did: str, name: str, description: str | None = None, organizations: list[RemoteHost] | None = None):
        self.did = did
        self.name = name
        self.description = description
        self.organizations = organizations

    def __repr__(self):
        return f"Circle({self.name}, {self.description}, {self.organizations})"

    def contains(self, to_check: RemoteHost | str) -> bool:
        """Checks if provided host is in the circle

        Args:
            to_check: Either the RemoteHost to check, or a DID, or org name.

        Returns:
            Boolean showing if the remote host is included
        """
        if not self.organizations:
            return False
        if isinstance(to_check, str):
            for host in self.organizations:
                if to_check == host.did or to_check == host.name:
                    return True
        elif isinstance(to_check, RemoteHost):
            return to_check in self.organizations

        return False

    @classmethod
    def from_json(cls, value: dict):
        allowed_hosts : list[RemoteHost] = []
        for raw_host in value.get("organizations", []):
            allowed_hosts.append(RemoteHost(did=raw_host["did"], name=raw_host["name"]))
        return cls(
            did=value["did"],
            name=value["name"],
            description=value.get("description"),
            organizations=allowed_hosts,
        )

    def as_dict(self) -> dict:
        resp: dict[str, str | list] = {
                "did": self.did,
                "name": self.name,
        }

        if self.description:
            resp["description"] = self.description

        if self.organizations:
            resp["organizations"] = [{"did": o.did} for o in self.organizations]


        return resp


