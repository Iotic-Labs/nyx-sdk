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

# ruff: noqa: D102

"""SDK configuration classes."""

import enum
import json
import os
from dataclasses import dataclass

from dotenv import dotenv_values


@dataclass(frozen=True)
class BaseNyxConfig:
    """Configuration for the Nyx client.

    Attributes:
        nyx_url: The URL of the Nyx instance.
        nyx_username: The username of the Nyx user.
        nyx_email: The email of the Nyx user.
        nyx_password: The password of the Nyx user.
    """

    nyx_url: str
    nyx_password: str
    nyx_email: str
    override_token: str | None

    @classmethod
    def from_env(
        cls,
        env_file: str | None = None,
        override_token: str | None = None,
    ):
        """Create a BaseNyxConfig instance from environment variables.

        Args:
            env_file: Path to the environment file.
            override_token: Token to override the default authentication.

        Returns:
            A new BaseNyxConfig instance.

        Raises:
            OSError: If required environment variables are not set.
        """
        # Load from .env, note env vars will not be overwritten
        # If no env file supplied dotenv will traverse up the directory tree looking for a .env file
        vals = dotenv_values(dotenv_path=env_file if env_file else None)
        url = vals.get("NYX_URL", "https://nyx-playground.iotics.space")
        email = vals.get("NYX_EMAIL")
        password = vals.get("NYX_PASSWORD")

        if not url:
            raise OSError("NYX_URL not set in env file")
        if not email:
            raise OSError("NYX_EMAIL not set in env file")
        if not password:
            raise OSError("NYX_PASSWORD not set in env file")
        config = BaseNyxConfig(url, password, email, override_token)
        return config

    def __str__(self):
        """Return a string representation of the configuration.

        Returns:
            A JSON string of the configuration.
        """
        return json.dumps(self.__dict__)

    @property
    def nyx_auth(self) -> dict:
        """Get the authentication credentials.

        Returns:
            A dictionary containing email and password for authentication.
        """
        return {"email": self.nyx_email, "password": self.nyx_password}


@enum.unique
class ConfigType(str, enum.Enum):
    """Nyx configuration types."""

    BASE = "base"
    OPENAI = "openai"
    COHERE = "cohere"


@dataclass(frozen=True)
class NyxConfigExtended:
    """Extended configuration for Nyx client with API integration.

    Attributes:
        api_key: The API key for the selected provider.
        provider: The type of configuration provider.
        base_config: The base Nyx configuration.
    """

    api_key: str
    provider: ConfigType
    base_config: BaseNyxConfig

    @classmethod
    def from_env(
        cls,
        provider: ConfigType,
        env_file: str | None = None,
        override_token: str | None = None,
    ):
        """Create a NyxConfigExtended instance from environment variables.

        Args:
            provider: The type of configuration provider.
            env_file: Path to the environment file.
            override_token: Token to override the default authentication.

        Returns:
            A new NyxConfigExtended instance.

        Raises:
            Exception: If an unsupported config type is provided.
        """
        api_key = ""
        match provider:
            case ConfigType.OPENAI:
                api_key = os.environ["OPENAI_API_KEY"]
            case ConfigType.COHERE:
                api_key = os.environ["COHERE_API_KEY"]
        base = BaseNyxConfig.from_env(env_file, override_token)
        return NyxConfigExtended(api_key=api_key, provider=provider, base_config=base)
