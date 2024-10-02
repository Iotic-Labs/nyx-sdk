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

import os

import grpc
from iotics.lib.grpc import AuthInterface, IoticsApi
from iotics.lib.grpc.helpers import KEEP_ALIVE_CHANNEL_OPTIONS

from nyx_client.configuration import BaseHostConfig
from nyx_client.identity_auth import IdentityAuth, IdentityAuthError

DID_TOKEN_DURATION = os.getenv("DID_TOKEN_DURATION", "30")


class HostClient:
    """HostClient is a context manager that provides a gRPC channel to IOTICSpace and instantiates API stubs.

    Attributes:
        verify_ssl: Whether to verify the SSL certificate.
        identity: IdentityAuth instance.
        api: IoticsApi instance.
        fqdn: Fully qualified domain name.
    """

    verify_ssl: bool
    identity: IdentityAuth
    api: IoticsApi
    fqdn: str

    def __init__(self, config: BaseHostConfig):
        """Initialize a HostClient instance.

        Args:
            config: `BaseHostConfig` instance.
        """
        host_url = config.host_url
        if host_url is None:
            host_url = os.getenv("HOST_ADDRESS", "localhost:10000")
        self.verify_ssl = config.host_verify_ssl

        try:
            self.identity = IdentityAuth(
                host_url,
                config.resolver_url,
                config.did_user_id,
                config.did_agent_id,
                config.did_agent_key_name,
                config.did_agent_name,
                config.did_agent_secret,
                DID_TOKEN_DURATION,
                self.verify_ssl,
            )
        except IdentityAuthError as error:
            raise error

        self.fqdn = self.identity.get_host_with_scheme()

    def __enter__(self):
        self.identity.refresh_token()
        self.api = IoticsApi(
            auth=self.identity,
            channel=get_channel(auth=self.identity, verify_ssl=self.verify_ssl),
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api.channel.close()


def get_channel(auth: AuthInterface, verify_ssl: bool = True, channel_options: [tuple, ...] = None) -> grpc.Channel:
    """Creates a gRPC channel to IOTICSpace and instantiates API stub.

    Args:
        auth: Required to get a space host name and authentication token.
        verify_ssl: Whether to verify the SSL certificate
        channel_options: options argument passed to the grpc.secure_channel call
          by default will use KEEP_ALIVE_CHANNEL_OPTIONS

    Returns: gRPC channel.
    """
    if channel_options is None:
        channel_options = KEEP_ALIVE_CHANNEL_OPTIONS

    channel_credentials = grpc.ssl_channel_credentials() if verify_ssl else grpc.local_channel_credentials()

    call_credentials = grpc.access_token_call_credentials(auth.get_token())
    composite_credentials = grpc.composite_channel_credentials(channel_credentials, call_credentials)
    return grpc.secure_channel(auth.get_host(), composite_credentials, options=channel_options)
