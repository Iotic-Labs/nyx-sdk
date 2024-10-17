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

import logging

from nyx_client.configuration import NyxConfigExtended, ConfigType, BaseNyxConfig
from nyx_extras.langchain import NyxLangChain


def main():
    """
    Main displays the most simple usage of the LangChain module of Nyx Client. By default,
    query will run against all the data, which will be downloaded and processed when the query method is called.

    A config object must be provided to the NyxLangChain class, internally creating an LLM specific class based on
    configuration type.

    When instantiating a language model specific config, the relevant API key must be available as an
    environment variable, or it must be passed in explicitly.
    """
    # Supply ConfigType.COHERE to use Cohere LLM instead
    base_config = BaseNyxConfig.from_env()
    config = NyxConfigExtended(base_config=base_config, provider=ConfigType.COHERE.OPENAI, api_key="your_api_key_here")
    client = NyxLangChain(config=config, log_level=logging.DEBUG)
    while True:
        prompt = input("What is your question? ")
        if prompt == "":
            continue
        # When query is called, all subscribed data is pulled down from Nyx and supplied to the LLM.
        print(client.query(prompt))


def custom_data():
    """
    This displays how to limit the data you want to query. This can be useful if you want to
    speed up the prompt, by reducing the data, and also prevents the data being downloaded and processed
    automatically, giving you more control.
    """
    client = NyxLangChain()

    # Get data with the climate category only
    data = client.get_data(genre="sdktest1", categories=["ai"]) # Combine multiples

    while True:
        prompt = input("What is your question? ")
        if prompt == "":
            continue
        # Pass these into the query, now the LLM will only be supplied matching data
        print(client.query(prompt, data=data))


def include_own_data():
    """
    This displays how to include your own data, created in Nyx, in the query.
    """
    client = NyxLangChain()

    while True:
        prompt = input("What is your question? ")
        if prompt == "":
            continue
        print(client.query(prompt, include_own=True))


def custom_openai_llm():
    """
    This displays how to pass an OpenAI model class into the client, this will be used to execute queries on.
    In the LangChain module of Nyx, this will always be an instance of
    langchain_core.language_models.chat_models.BaseChatModel. The LLM provided must support tool calling, or a
    NotImplemented error will be raised.
    """
    from langchain_openai import ChatOpenAI

    config = NyxConfigExtended.from_env(provider=ConfigType.OPENAI)

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=config.api_key)
    client = NyxLangChain(config=config, llm=llm)

    while True:
        prompt = input("What is your question? ")
        if prompt == "":
            continue
        print(client.query(prompt, include_own=True))


if __name__ == "__main__":
    custom_openai_llm()
