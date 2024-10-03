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
import inspect
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import dotenv_values


@dataclass
class BaseNyxConfig:
    """Configuration for the Nyx client.

    Attributes:
        host_config (BaseHostConfig): Configuration for the host client.
        nyx_url (str): The URL of the Nyx instance.
        nyx_username (str): The username of the Nyx user.
        nyx_email (str): The email of the Nyx user.
        nyx_password (str): The password of the Nyx user.
        org (str): The organisation name.
        community_mode (bool): Whether the host is in community mode.
    """

    required_if_token_empty = [
        "nyx_username",
        "nyx_email",
        "nyx_password",
    ]

    def __init__(
        self,
        env_file: Optional[str] = None,
        override_token: str = "",
        validate: bool = True,
    ):
        """Instantiate a new nyx base configuration.

        Args:
            env_file: Path to the environment file. If None, dotenv will search for a .env file.
            override_token: Token to override the default authentication. Defaults to username and password.
            validate: Whether to validate the environment variables. Defaults to False.
            host_config: Configuration for the host client.

        """
        # Load from .env, note env vars will not be overwritten
        # If no env file supplied dotenv will traverse up the directory tree looking for a .env file
        vals: Dict[str, Optional[str]] = dotenv_values(dotenv_path=env_file if env_file else None)

        self._override_token: str = override_token

        self.nyx_url: str = vals.get("NYX_URL", "https://nyx-community-1.dev.iotics.space")
        self.nyx_username: str = vals.get("NYX_USERNAME")
        self.nyx_email: str = vals.get("NYX_EMAIL")
        self.nyx_password: str = vals.get("NYX_PASSWORD")
        self.org: str = ""
        self.host_url: str = ""
        self._host_verify_ssl: bool = vals.get("HOST_VERIFY_SSL", "True").lower() == "true"
        self._community_mode: bool = False
        self._validated = False

        if validate and not self._validated:
            self.validate()


    def validate(self):
        if self._validated:
            return

        # Only check for auth if no token is supplied
        if not self.override_token:
            missing = [k for k in BaseNyxConfig.required_if_token_empty if getattr(self, k) is None]
            if len(missing) > 0:
                raise OSError(f"Missing Required env vars {missing}")

    def __str__(self):
        return json.dumps(self.__dict__)

    @property
    def nyx_auth(self) -> dict:
        return {"email": self.nyx_email, "password": self.nyx_password}

    @property
    def community_mode(self) -> bool:
        return self._community_mode

    @community_mode.setter
    def community_mode(self, mode):
        self._community_mode = mode

    @property
    def override_token(self) -> str:
        return self._override_token

    @override_token.setter
    def override_token(self, token):
        self._override_token = token


@dataclass
class CohereNyxConfig(BaseNyxConfig):
    """Cohere specific configuration for the Nyx client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        env_file: Optional[str] = None,
        override_token: str = "",
        validate: bool = True,
    ):
        """Instantiate a new Cohere nyx configuration.

        Args:
            api_key: The Cohere API key.
            env_file: Path to the environment file. If None, dotenv will search for a .env file.
            override_token: Token to override the default authentication. Defaults to username and password.
            validate: Whether to validate the environment variables. Defaults to False.
            host_config: Configuration for the host client.
        """
        if api_key:
            self._api_key: str = api_key
        else:
            self._api_key: str = os.getenv("COHERE_API_KEY", "")
        super().__init__(env_file, override_token, validate)

        if validate:
            self.validate()

    def validate(self):
        if not self._api_key:
            raise OSError("Missing Required env var: COHERE_API_KEY")
        if not self._validated:
            super().validate()

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, api_key: str):
        self._api_key = api_key


@dataclass
class OpenAINyxConfig(BaseNyxConfig):
    """OpenAI specific configuration for the Nyx client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        env_file: Optional[str] = None,
        override_token: str = "",
        validate: bool = True,
    ):
        """Instantiate a new OpenAI nyx configuration.

        Args:
            api_key: The OpenAI API key.
            env_file: Path to the environment file. If None, dotenv will search for a .env file.
            override_token: Token to override the default authentication. Defaults to username and password.
            validate: Whether to validate the environment variables. Defaults to False.
            host_config: Configuration for the host client.
        """
        if api_key:
            self._api_key: str = api_key
        else:
            self._api_key: str = os.getenv("OPENAI_API_KEY", "")
        super().__init__(env_file, override_token, validate)

        if validate:
            self.validate()

    def validate(self):
        if not self._api_key:
            raise OSError("Missing Required env var: OPENAI_API_KEY")
        if not self._validated:
            super().validate()

    @property
    def api_key(self) -> str:
        return self._api_key

    @api_key.setter
    def api_key(self, api_key: str):
        self._api_key = api_key


@enum.unique
class ConfigType(str, enum.Enum):
    """nyx configuration types."""

    BASE = "base"
    OPENAI = "openai"
    COHERE = "cohere"


class ConfigProvider:
    """Factory class to create Nyx configuration objects.

    Attributes:
        config_classes (dict): A dictionary of configuration classes: base, openai, cohere.
    """

    config_classes = {
        ConfigType.BASE: BaseNyxConfig,
        ConfigType.OPENAI: OpenAINyxConfig,
        ConfigType.COHERE: CohereNyxConfig,
    }

    @staticmethod
    def create_config(
        config_type: ConfigType,
        api_key: Optional[str] = None,
        env_file: Optional[str] = None,
        override_token: str = "",
        validate: bool = True,
    ):
        config_class = ConfigProvider.config_classes.get(config_type)
        if not config_class:
            raise ValueError(f"Unknown config type: {config_type}")

        constructor_signature = inspect.signature(config_class.__init__)
        parameters = constructor_signature.parameters

        # Dynamically create arguments to pass based on what the constructor expects
        kwargs = {
            "env_file": env_file,
            "override_token": override_token,
            "validate": validate,
        }

        # If 'api_key' is part of the constructor, include it in the arguments
        if "api_key" in parameters:
            kwargs["api_key"] = api_key

        # Call the config class with the correct arguments
        return config_class(**kwargs)
