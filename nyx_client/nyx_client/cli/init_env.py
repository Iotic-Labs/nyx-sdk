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
from getpass import getpass

import click
import requests

from nyx_client.cli.common import SDK_CLI_DEFAULT_HEADERS

TERMS = """
To use Nyx you must agree to our Terms of Service when sharing content


I understand that the data I am uploading will be visible in the Nyx Playground,
including to users outside my organisation.
I confirm that I have the right to share this data.
I confirm that this data does not contain any Personally Identifiable Information
or otherwise sensitive information, and that it does not violate any laws.
I confirm I have read the Nyx Terms of Service and I am content to proceed.
https://www.get-nyx.io/terms

Agree (y/N):"""


def init_env(filename: str = ".env"):
    """Interactively generate configuration and save it to the file with the given name."""
    if filename != "-":
        # Check .env exists, to ask if we should override it
        if os.path.exists(filename):
            prompt = f"'{filename}' already exists, do you wish to override it? (y/N): "
        else:
            prompt = f"Do you want to interactively create '{filename}'? (y/N): "
        # Default is always no action
        if input(prompt).lower() != "y":
            click.echo("Exiting with no changes")
            return

    # Check user is aware of T&Cs
    tcs = input(TERMS)
    if tcs.lower() != "y":
        click.echo("You must agree to the Terms of Service!")
        return

    # Get instance details, to get everything from API
    url = input("Enter Nyx URL: ").rstrip("/")
    email = input("Enter Nyx email: ")
    password = getpass("Enter Nyx password: ")

    headers = SDK_CLI_DEFAULT_HEADERS.copy()

    resp = requests.post(
        url + "/api/portal/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )

    # Display any failures and exit without writing
    if not resp.ok:
        raise RuntimeError(f"Unable to authorize on Nyx instance, {resp.text}")

    token = resp.json()["access_token"]
    headers["authorization"] = f"Bearer {token}"

    secrets = ""

    # NYX creds
    secrets += f'\nNYX_PASSWORD="{password}"'
    secrets += f'\nNYX_EMAIL="{email}"'
    secrets += f'\nNYX_URL="{url}"'

    click.echo(
        "Our high level client (NyxLangChain) expects a configured language model, "
        "however it can be configured with other language model wrappers provided by langchain "
        "providing they support 'tool calling'. "
        "Don't forget to set the appropriate API KEY as an environment variable for the language model you wish to use."
    )

    click.echo(f"Writing contents to {filename}")
    with click.open_file(filename, mode="w") as output:
        output.write(secrets)
