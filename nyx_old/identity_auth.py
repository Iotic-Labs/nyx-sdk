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

# ruff: noqa: D101,D102,D107

from time import time
from typing import Optional

import names_generator
import requests
from iotics.lib.grpc.auth import AuthInterface
from iotics.lib.identity import (
    IdentityApi,
    KeyPairSecretsHelper,
    RegisteredIdentity,
    SeedMethod,
    get_rest_high_level_identity_api,
    get_rest_identity_api,
    make_identifier,
)


class IdentityAuthError(Exception):
    """Raised when `IdentityAuth` cannot be instantiated correctly."""


class IdentityAuth(AuthInterface):
    regular_api: IdentityApi
    agent: RegisteredIdentity
    host_with_scheme: str
    grpc_url: str
    token_ttl: int
    user_did: str
    user_pubkey: str
    token_last_updated: float
    host_verify_ssl: bool

    def __init__(
        self,
        space: str,
        resolver_url: Optional[str],
        user_did: str,
        agent_did: str,
        agent_key_name: str,
        agent_name: str,
        agent_secret: str,
        token_ttl: Optional[str],
        host_verify_ssl: Optional[bool],
    ):
        self.regular_api = get_rest_identity_api(resolver_url=resolver_url)
        split_url = space.partition("://")
        space = split_url[2] or split_url[0]
        self.host_verify_ssl = host_verify_ssl
        self.host_with_scheme = f"https://{space}" if host_verify_ssl else f"http://{space}"
        self.grpc_url = space
        if not resolver_url:
            index_url = f"https://{space}/index.json"
            try:
                resolver_url = requests.get(index_url).json()["resolver"]
            except requests.exceptions.ConnectionError as ex:
                raise IdentityAuthError(f"Could not fetch resolver URL from `{index_url}`.") from ex
        if token_ttl:
            self.token_ttl = int(token_ttl)
        if not agent_name.startswith("#"):
            agent_name = "#" + agent_name

        self.agent = self._get_agent(resolver_url, agent_did, agent_key_name, agent_name, agent_secret)
        self.api = get_rest_high_level_identity_api(resolver_url=resolver_url)
        self.grpc_token = self.api.create_agent_auth_token(self.agent, user_did, self.token_ttl)
        self.token_last_updated = time()
        self.user_did = user_did

        self.user_pubkey = list(self.regular_api.get_register_document(user_did).public_keys.values())[0].base58

    def get_host(self) -> str:
        return self.grpc_url

    def get_host_with_scheme(self) -> str:
        return self.host_with_scheme

    def get_token(self, ttl: Optional[int] = None) -> str:
        if self.grpc_token:
            return self.grpc_token

        self.refresh_token(ttl or self.token_ttl)
        return self.grpc_token

    def refresh_token(self, ttl: Optional[int] = None):
        self.grpc_token = self.api.create_agent_auth_token(self.agent, self.user_did, ttl or self.token_ttl)
        self.token_last_updated = time()

    @staticmethod
    def _get_agent(
        resolver_url: str,
        agent_did: str,
        agent_key_name: str,
        agent_name: str,
        agent_secret: str,
    ):
        # Gets an agent identity using the provided credentials, taking into account that the agent DID may have been
        # generated using either of two SeedMethods
        agent_secret = bytes.fromhex(agent_secret)
        api = get_rest_identity_api(resolver_url)
        agent = api.get_agent_identity(agent_secret, agent_key_name, agent_did, agent_name)
        did_from_keys = make_identifier(KeyPairSecretsHelper.get_key_pair(agent.key_pair_secrets).public_bytes)
        if did_from_keys == agent_did:
            return agent
        return api.get_agent_identity(
            agent_secret,
            agent_key_name,
            agent_did,
            agent_name,
            SeedMethod.SEED_METHOD_NONE,
        )

    @staticmethod
    def generate_config(resolver: str) -> str:
        """Create new user and agent with auth delegation and return an env-file ready string representation thereof."""
        high_level_api = get_rest_high_level_identity_api(resolver_url=resolver)
        user_seed = high_level_api.create_seed()
        agent_seed = high_level_api.create_seed()
        user_key = f"#user-{names_generator.generate_name()}"
        agent_key = f"#agent-{names_generator.generate_name()}"
        if len(user_key) > 24:
            user_key = user_key[0:23]
        if len(agent_key) > 24:
            agent_key = agent_key[0:23]

        user_deleg = "#testagent"

        if len(user_key) > 24:
            user_key = user_key[0:23]
        if len(agent_key) > 24:
            agent_key = agent_key[0:23]

        user, agent = high_level_api.create_user_and_agent_with_auth_delegation(
            user_seed=user_seed,
            user_key_name=user_key,
            agent_seed=agent_seed,
            agent_key_name=agent_key,
            delegation_name=user_deleg,
            user_name=user_key,
            agent_name=agent_key,
        )

        return f"""
#### Autogenerated by nyx_client - do not edit manually
DID_USER_DID={user.did}
DID_AGENT_DID={agent.did}
DID_AGENT_KEY_NAME="{agent_key}"
DID_AGENT_NAME="{agent_key}"
DID_AGENT_SECRET={agent_seed.hex()}
HOST_VERIFY_SSL=true # Set to false for development
"""
