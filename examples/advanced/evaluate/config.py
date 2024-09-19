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

from langchain_cohere import ChatCohere
from langchain_openai import ChatOpenAI

from nyx_client.configuration import ConfigProvider, ConfigType
from nyx_client.extensions.langchain import NyxLangChain

# The judge prompt that can be updated to more accurately score
JUDGE_PROMPT = """
You are a judge that is designed to rate the ability of large language model to answer
question accurately and give it a percentage score. The large language models
you are rating will have access to documents provided at the end of this prompt

You should output your rating in the form of JSON, with the keys:
- "accuracy"
    For the total accuracy of the answer, this should be higher when the answer is more accurate
    and appears to be based on the provided sources.
- "source_accuracy"
    For the accuracy of the sources, this should be higher when the sources provided are more accurate
    and appear to be more relevant to the question asked.
- "sources"
    A list of urls referenced by the answer

If the question is about Nyx subscriptions, products, or available data, an accuracy of 100 should be given
if the response includes {file_names} in the answer, otherwise it should be 0.

For all other questions, the accuracy should be based on the ability of the LLM to answer the question, even if
you yourself cannot accurately answer the question.

You should only respond in JSON and the questions will be asked in the format.
I asked:
<question>
Answer:
<question>

The documents that are being questioned on are

"""

# Update or add questions to evaluate against these
input_prompts = [
    "What Nyx products am I subscribed to?",  # Nyx subscription question
    "What products do I have?",  # Nyx subscription question
    "What am I subscribed to?",  # Nyx subscription question
    "Who is my top customer?",  # SaaS sales question
    "What sales have I made for my SaaS?",  # SaaS sales question
    "What cybersecurity incidents have had the highest financial impact?",  # Cyber security question
    "What are the top cyber security incidents by duration?",  # Cyber security question
]

# Configure openAI gpt-4o-mini
config_openai = ConfigProvider.create_config(ConfigType.OPENAI)
client_openai_sm = NyxLangChain(config=config_openai, log_level=logging.WARN)

openai_ai = ChatOpenAI(model="gpt-4o")
client_openai_bg = NyxLangChain(config=config_openai, llm=openai_ai, log_level=logging.WARN)

# Configure cohere cmd-R
config_cohere = ConfigProvider.create_config(ConfigType.COHERE)
client_cohere_sm = NyxLangChain(config=config_cohere, log_level=logging.WARN)

cmd_r = ChatCohere(model="command-r-plus")
client_cohere_bg = NyxLangChain(config=config_cohere, llm=cmd_r, log_level=logging.WARN)


clients = (
    ("4o-mini", client_openai_sm),
    # ("4o", client_openai_bg), # Large model commented for cost
    ("cmd-r", client_cohere_sm),
    # ("cmd-r-plus", client_cohere_bg) # Larger model commented for cost
)
