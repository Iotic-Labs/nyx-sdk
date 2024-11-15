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
import logging
import os
from dataclasses import dataclass

from dotenv import dotenv_values, find_dotenv

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaseNyxConfig:
    """Configuration for the Nyx client."""

    nyx_url: str
    """The URL of the Nyx instance."""
    nyx_password: str
    """The email of the Nyx user."""
    nyx_email: str
    """The password of the Nyx user."""
    override_token: str | None = None
    """Allows injection of JWT token"""

    @classmethod
    def from_env(
        cls,
        env_file: str = ".env",
        override_token: str | None = None,
    ):
        """Create a BaseNyxConfig instance from environment variables.

        Args:
            env_file: Relative (to the working directory) or absolute path to the environment file.
            override_token: Token to override the default authentication.

        Returns:
            A new `BaseNyxConfig` instance.

        Raises:
            ValueError: If a required variable is not set in the env file or the file does not exist.
        """
        log.info("Specified env file: %s", env_file)
        # NOTE: Calling find_dotenv directly instead of via dotenv_values so can use current working directory
        if not (found_env_file := find_dotenv(filename=env_file, usecwd=True)):
            raise ValueError(f"Env file not found from specified path: {env_file}")
        log.info("Found env file: %s", found_env_file)

        # Load from .env. NOTE: env vars will not be overwritten
        if not (vals := dotenv_values(dotenv_path=found_env_file)):
            raise ValueError(f"Env file empty: {env_file}")

        if not (url := vals.get("NYX_URL")):
            raise ValueError(f"NYX_URL not set in {env_file}")
        if not (email := vals.get("NYX_EMAIL")):
            raise ValueError(f"NYX_EMAIL not set in {env_file}")
        if not (password := vals.get("NYX_PASSWORD")):
            raise ValueError(f"NYX_PASSWORD not set in {env_file}")
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
    """Extended configuration for Nyx client with API integration."""

    api_key: str
    """The API key for the selected provider."""
    provider: ConfigType
    """The type of configuration provider."""
    base_config: BaseNyxConfig
    """The base Nyx configuration."""

    @classmethod
    def from_env(
        cls,
        provider: ConfigType,
        env_file: str = ".env",
        override_token: str | None = None,
    ):
        """Create a NyxConfigExtended instance from environment variables.

        Args:
            provider: The type of configuration provider.
            env_file: Relative (to the working directory) or absolute path to the environment file.
            override_token: Token to override the default authentication.

        Returns:
            A new `NyxConfigExtended` instance.

        Raises:
            ValueError: If a required variable is not set in the env file, the env file does not exist or the
                corresponding `api_key` env var is not set.
        """
        api_key = ""
        match provider:
            case ConfigType.OPENAI:
                api_key_var = "OPENAI_API_KEY"
            case ConfigType.COHERE:
                api_key_var = "COHERE_API_KEY"
            case _:
                api_key_var = ""
        if api_key_var:
            try:
                api_key = os.environ[api_key_var]
            except KeyError as ex:
                raise ValueError(f"{api_key_var} env var not set") from ex

        base = BaseNyxConfig.from_env(env_file=env_file, override_token=override_token)
        return NyxConfigExtended(api_key=api_key, provider=provider, base_config=base)
