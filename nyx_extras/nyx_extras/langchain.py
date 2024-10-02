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

"""Optional module for tight integration between Nyx and LangChain."""

import logging
import os
from typing import Optional

from nyx_client.configuration import BaseNyxConfig, CohereNyxConfig, OpenAINyxConfig

try:
    from langchain_community.agent_toolkits import create_sql_agent
    from langchain_community.utilities import SQLDatabase
    from langchain_core.language_models import BaseChatModel
except ImportError as err:
    raise ImportError(
        "LangChain dependencies are not installed. "
        "Please install them with `pip install nyx_client[langchain-openai]` or "
        "`pip install nyx_client[langchain-cohere]`"
    ) from err

try:
    from langchain_openai import ChatOpenAI
except ImportError:

    class ChatOpenAI:  # noqa: D101
        def __init__(self, *args, **kwargs):  # noqa: D107
            raise ImportError(
                "LangChain OpenAI dependencies are not installed. "
                "Please install them with `pip install nyx_client[langchain-openai]`"
            )


try:
    from langchain_cohere import ChatCohere
    from langchain_cohere.sql_agent.agent import create_sql_agent as create_cohere_sql_agent
except ImportError:

    class ChatCohere:  # noqa: D101
        def __init__(self, *args, **kwargs):  # noqa: D107
            raise ImportError(
                "LangChain Cohere dependencies are not installed. "
                "Please install them with `pip install nyx_client[langchain-cohere]`"
            )


from langchain.agents.mrkl import prompt as react_prompt
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    PromptTemplate,
)

from nyx_client.client import NyxClient
from nyx_client.data import Data
from nyx_client.utils import Parser, Utils

EXAMPLES = [
    {
        "input": "List all the characters in Anna Karenina",
        "query": "SELECT DISTINCT characterNames FROM novels WHERE novelName = 'Anna Karenina'",
    },
]

SYSTEM_PREFIX = """
You are an agent designed to interact with an SQLite database containing data from a decentralized file sharing
application. Given an input question, create a syntactically correct query to run against the database,
then look at the results of the query and return the answer.
Follow these steps:

Identify the relevant tables to query by examining the nyx_subscriptions table, which contains information about
each file (table) in the database, including the name, url, description, and table_name.
If the question is related to available products, subscriptions, or data, respond with a list of all entries from the
nyx_subscriptions table, including the name, description, and url for each entry. Do not filter or limit the results
for these specific queries. Other questions about Nyx that are not related to subscriptions, or any questions about
subscriptions that are not related to nyx, you should reference other tables.

Some tables contain a column called "context" this is a chunk that contains information from relevants files

For other questions, determine which tables are most relevant based on the description and name columns in the
nyx_subscriptions table. Query the schema of the relevant tables to understand their structure.
Write an optimized query to answer the question based on the schema, selecting only the necessary columns.
Avoid querying for all columns from a specific table.
Execute the query and check the results. If you encounter an error, rewrite the query and try again.
Return the query results as the answer in a human-readable format, citing the sources (tables) used.

If the question does not seem related to the database, respond with: "I am not sure what data you're talking about.
Please try asking again, referencing the specific data you're interested in."
Remember:

Only use the given tools and the information returned by the tools to construct your final answer.
Do not make any DML statements (INSERT, UPDATE, DELETE, DROP, etc.) to the database.
Order the results by a relevant column to return the most interesting examples, unless the user
specifies a specific number of examples they wish to obtain.

Your thought process should be as follows:

Examine the full nyx_subscriptions table to identify relevant tables to query.
Query the schema of the most relevant tables.
Write an optimized query to answer the question based on the schema.
Execute the query and check the results.
Return the results of the query as the answer in a human-readable format, citing the sources (tables) used.
"""

BASIC_PREFIX = """
    Begin!

    Question: {input}
    Thought: I should look at the nyx_subscriptions table in the database to see what I can query.
    Then I should query the schema of the most relevant tables.
    {agent_scratchpad}

"""

EXAMPLE_PROMPT = ChatPromptTemplate.from_messages(
    messages=[
        ("human", "Hello, I am going to ask you a question now which you will need to answer using SQL."),
        ("ai", "OK, I will do my best to answer your question using SQL."),
        ("human", "{query}"),
    ]
)

FEW_SHOT_PROMPT = FewShotChatMessagePromptTemplate(
    examples=EXAMPLES,
    example_prompt=EXAMPLE_PROMPT,
    input_variables=["input", "agent_scratchpad"],
)

FORMAT_INSTRUCTIONS = (
    f"{react_prompt.FORMAT_INSTRUCTIONS}\n "
    f"Here are some examples of user inputs and "
    f"their corresponding SQL queries:\n"
)

TEMPLATE = "\n\n".join([SYSTEM_PREFIX, FORMAT_INSTRUCTIONS, FEW_SHOT_PROMPT.format(), BASIC_PREFIX])

DEFAULT_COHERE_MODEL = "command-r"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class NyxLangChain(NyxClient):
    """An opinionated client wrapping langChain to evaluate user queries against contents of a Nyx network.

    This class extends NyxClient to provide LangChain-based functionality for querying Nyx network contents.

    Note:
        The LLM must support tool calling.
    """

    def __init__(
        self,
        config: Optional[BaseNyxConfig] = None,
        env_file: Optional[str] = None,
        llm: Optional[BaseChatModel] = None,
        log_level: int = logging.WARN,
        system_prompt: Optional[str] = None,
    ):
        """Initialise a new langChain client.

        Args:
            config: Configuration for the Nyx client.
            env_file: Path to the environment file.
            llm: Language model to use.
            log_level: the logging level to use for nyx client, and langchain modules
            system_prompt: provide an override for the system prompt
        """
        super().__init__(env_file, config)
        logging.basicConfig(format="%(asctime)s %(levelname)s [%(module)s] %(message)s", level=log_level)

        # Disable langchain network requests log
        logging.getLogger("httpx").setLevel(log_level)
        logging.getLogger("httpcore").setLevel(log_level)

        self.log = logging.getLogger(__name__)
        self.log.setLevel(log_level)

        self.verbose = False
        if log_level <= logging.DEBUG:
            self.verbose = True
        self.create_agent_func = create_sql_agent

        if llm:
            self.llm = llm
            if isinstance(self.llm, ChatCohere):
                self.create_agent_func = create_cohere_sql_agent
        else:
            if isinstance(self.config, CohereNyxConfig):
                self.llm = ChatCohere(
                    model=DEFAULT_COHERE_MODEL,
                    cohere_api_key=self.config.api_key,
                    temperature=0.0,
                )
                self.create_agent_func = create_cohere_sql_agent
            elif isinstance(self.config, OpenAINyxConfig):
                self.llm = ChatOpenAI(
                    model=DEFAULT_OPENAI_MODEL,
                    api_key=self.config.api_key,
                    temperature=0.0,
                )
            else:
                raise ValueError("No language model provided and no valid config found")

        self.template = "\n\n".join([system_prompt if system_prompt else "", TEMPLATE])
        self.prompt = PromptTemplate.from_template(template=self.template)

    def query(
        self,
        query: str,
        data: Optional[list[Data]] = None,
        include_own: bool = False,
        sqlite_file: Optional[str] = None,
        update_subscribed: bool = True,
        k: int = 3,
    ) -> str:
        """Query the LLM with a user prompt and context from Nyx.

        This method takes a user prompt and invokes it against the LLM associated with this instance,
        using context from Nyx.

        Args:
            query (str): The user input.
            data (Optional[list[Data]], optional): List of products to use for context.
                If None, uses all subscribed data. Defaults to None.
            include_own (bool): Include your own data, created in Nyx, in the query.
            sqlite_file (Optional[str]): A file location to write the sql_lite file to.
            update_subscribed (bool): if set to true this will re-poll Nyx for subscribed data
            k (int): Max number of vector matches to include

        Returns:
            str: The answer from the LLM.

        Note:
            If the data list is not provided, this method updates subscriptions and retrieves all subscribed data.
        """
        if update_subscribed:
            self.update_subscriptions()
        if data is None:
            data = self.get_subscribed_data()
        if include_own:
            data.extend(self.get_data_for_creators(creators=[self.config.org]))
        self.log.debug("using products: %s", [d.title for d in data])

        engine = Parser.data_as_db(data, additional_information=None, sqlite_file=sqlite_file, if_exists="replace")
        db = SQLDatabase(engine=engine, sample_rows_in_table_info=0)
        agent_executor = self.create_agent_func(self.llm, db=db, agent_type="tool-calling", verbose=self.verbose)

        res = agent_executor.invoke(
            {
                "input": self.prompt.format(
                    input=Utils.with_sources(query, database_tables=db.get_table_info()),
                    agent_scratchpad="",
                    tool_names=agent_executor.tools,
                )
            }
        )

        if sqlite_file:
            os.remove(sqlite_file)

        return res["output"]
