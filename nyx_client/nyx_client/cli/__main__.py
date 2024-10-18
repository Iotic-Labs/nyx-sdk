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

import click

from nyx_client.cli.init_env import init_env


@click.group()
def cli():
    """NYX SDK command line utilities.

    For more information please visit https://github.com/Iotic-Labs/nyx-sdk
    """


@cli.command()
@click.argument("file", type=click.Path(writable=True, dir_okay=False), default=".env")
def init(file: str):
    """Generate an env file for the NYX client.

    Output is written to FILE (defaults to '.env' in the working directory)
    """
    init_env(file)


if __name__ == "__main__":
    cli()
