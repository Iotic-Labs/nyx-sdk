# Nyx AI Examples

A set of demo built on top of the Nyx SDK

![https://iotics.com](https://img.shields.io/badge/Powered%20by-Iotics-blue)

## 🤔 Why Nyx for AI?

- **Decentralized Data Gathering:** Access a vast network of data producers.
- **Efficiency:** Augment smaller language models with relevant information for informed decision-making.
- **Sustainability:** Smaller models are good for the planet, cost-effective whilst still providing grounded answers with the help of RAG.

## 🔥 Quick Start

If you'd like to experience the SDK without installing it first:

- See the [notebook section](#-try-it-out-jupyter).
- Visit `https://[nyx_host]/try-me-now`


## 💾 Installation

To get started, we recommend installing the package extras which provide close integration with one of the most popular AI libraries for Python: [LangChain](https://python.langchain.com).

You can install the full set of extras as follows:
```shell
cd examples
pip install -r requirements.txt
```

This will install core functionality to interact with Nyx, as well as some support for auto-vectorization, and conversion of CSV products from Nyx into an [SQLite](https://www.sqlite.org/) DB that can be handled by an AI. It's designed to support advanced usage where you will integrate results from Nyx yourself.

To only install the core of the client with `pip install nyx_client` if you're planning on advanced usage. See [Nyx SDK](../README.sdk.md).

## ⚙️ Configuration

See [First time set up](../README.sdk.md#First-time-set-up) on how to generate initial configuration to communicate with your nyx instance.

### 🔐 API Keys

The Nyx SDK currently supports a variety of [LangChain](https://python.langchain.com)-based LLM specific plugins, including [Cohere](https://cohere.com/) and [OpenAI](https://openai.com/).
To use these, you will need to expose the specific API key to your application through environment variables or instantiate the relevant configuration object with the key.

```shell
export OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
```
or
```python
from nyx_client.configuration import ConfigProvider, ConfigType

ConfigProvider.create_config(ConfigType.OPENAI, api_key="your_api_key_here")
```
or if using Cohere
```shell
export COHERE_API_KEY=<YOUR_COHERE_API_KEY>
```
or
```python
from nyx_client.configuration import ConfigProvider, ConfigType

ConfigProvider.create_config(ConfigType.COHERE, api_key="your_api_key_here")
```

## 🎓 Examples

### [High-level](./high_level)

These use additional dependencies for an out-of-the-box experience with minimal integration.

Example | Summary | Notes
--|--|--
[`highlevel.py::main()`](./high_level/highlevel.py) | Minimal CLI chat prompt, considering all subscribed-to Nyx data. | Defaults to [OpenAI](https://openai.com/) LLM but can easily be changed to use [Cohere](https://cohere)
[`highlevel.py::custom_data()`](./high_level/highlevel.py) | Use a filtered set of data rather than all subscribed-to |
[`highlevel.py::include_own_data()`](./high_level/highlevel.py) | Include own data in addition to subscribed-to |
[`highlevel.py::custom_openai_llm()`](./high_level/highlevel.py) | Use a custom model instead of the nyx default one for an LLM. | This also demonstrates how do specify your own [`BaseChatModel`](https://api.python.langchain.com/en/latest/language_models/langchain_core.language_models.chat_models.BaseChatModel.html), i.e. any LLM provider supporting said LangChain interface.

### [Advanced Usage](./advanced)

These require manual integration with AI or other tools, offering more control over the process.

Example | Summary | Notes
--|--|--
[`rag_api`](./advanced/rag_api) | Web server chat bot | Demonstrates configuration of LLM agent, nyx data and RAG SQL tooling
[`rag_with_sources`](./advanced/rag_with_sources) | How to include information about data sources in query responses | Similar to `rag_api`
[`rag_with_judge`](./advanced/rag_with_judge) | Let the LLM attempt to answer the query on its own and enrich its context with data from Nyx | Similar to `rag_api`
[`evaluate`](./advanced/evaluate)| Compare the performance of different Language Models (LLMs) on a set of predefined questions.



## 📔 Try it out (Jupyter)

To get a feel for the NYX SDK without a local environment setup, you can try our [Jupyter](https://jupyter.org/) Notebooks.

### Available notebooks

Path | Summary
-- | --
[`examples/high_level/highlevel.ipynb`](./high_level/highlevel.ipynb) | Introduction to NYX SDK with minimal RAG demo code
[`examples/advanced/advanced.ipynb`](./advanced/advanced.ipynb) | RAG demo showing how to put the building blocks together yourself (LLM, agent, RAG tooling)

### Running in Google Colab

Click [![Open All Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Iotic-Labs/nyx-sdk), select one of the above listed examples and start running it by clicking the "Play" button on the first code snippet.

### Running with local [JupyterLab](https://jupyterlab.readthedocs.io/en/latest/)

Clone the repo:
```shell
git clone https://github.com/Iotic-Labs/nyx-sdk.git
cd nyx-sdk
```

Install JupyterLab in a new virtual environment:
```shell
python3 -mvenv jupyterlab
. jupyterlab/bin/activate
pip install jupyterlab
```

Thereafter, each time to start it:
```shell
. jupyterlab/bin/activate
jupyter lab
```

## 👉 Gotchas

See [SDK readme section](../README.sdk.md#-gotchas)

## 🐞 Troubleshooting

If you encounter any issues, we'd [love to hear from you](../README.sdk.md#-troubleshooting)


## 🤝 Contributing

See [SDK readme section](../README.sdk.md#-contributing).
