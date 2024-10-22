from typing import Tuple

from dotenv import dotenv_values
from langchain_openai import ChatOpenAI

from nyx_client import Data
from nyx_client.configuration import BaseHostConfig, ConfigProvider, ConfigType
from nyx_client.extensions.langchain import NyxLangChain
from nyx_client.utils import Parser

STRUCTED_DATA_CONTENT_TYPES = ["csv"]
UNSTRUCTED_DATA_CONTENT_TYPES = ["pdf", "markdown", "text", "plain"]

judge = ChatOpenAI(model="gpt-4o-mini")


def build_structed_agent_and_datasets() -> Tuple[NyxLangChain, list[Data], Parser]:
    """
    Builds an agent and a dataset of structured content types.

    Streamlit uses a different directory to load the .env file, so we need to manually
    build the config here.

    Returns:
        NxyLangChain: AI client to query structed data
        List[Data]: List of data of structed content types
        Parser: Parser to parse unstructed data
    """
    # Grab the agent config
    env_vars = dotenv_values()
    host_config = BaseHostConfig(env_vars)

    config = ConfigProvider.create_config(ConfigType.OPENAI, host_config=host_config)
    agent = NyxLangChain(config)
    dataset = agent.get_subscribed_data()
    structured = [d for d in dataset if d.content_type in STRUCTED_DATA_CONTENT_TYPES]
    unstructured = [d for d in dataset if d.content_type in UNSTRUCTED_DATA_CONTENT_TYPES]

    parser = Parser()
    parser.data_as_vectors(unstructured, chunk_size=200)
    return agent, structured, parser


def combine(query: str, structed: str, unstructed: str) -> str:
    query = f"""
    You are being given a response from 2 agents, your job is to combine the input of both of them to answer the users
    query.

    Agent 1 is a structured agent, it has accessed a structured dataset and returned a response that includes sources

    Agent 2 is an unstructured agent, it has accessed a text document

    The user query is: {query}

    Agent 1 response: {structed}

    Agent 2 response: {unstructed}

    Your job is to combine the responses from both agents into a single response.

    The combined response should be a single response to the users query.

    If one agent does not return anything ignore it's response.
    If one agent returns a response that is not relevant to the users query, ignore it's response.
    Agent 1 can sometimes respond with a list of sources, and only sources. If this is the case, ignore it's response,
    unless the user is asking about subscriptions
    """

    response = judge.invoke(query)

    return response.content
