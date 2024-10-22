<div align="center">

# Nyx Client SDK

[![Version](https://img.shields.io/pypi/v/nyx-client)](https://pypi.org/project/nyx-client)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](https://github.com/Iotic-Labs/nyx-sdk/blob/main/LICENSE)
[![Build](https://github.com/Iotic-Labs/nyx-sdk/actions/workflows/build.yaml/badge.svg?branch=main)](https://github.com/Iotic-Labs/nyx-sdk/actions/workflows/build.yaml)
[![Read The Docs](https://readthedocs.org/projects/nyx-client/badge/?version=stable)](https://nyx-client.readthedocs.io/en/stable)
[![GitHub Repo stars](https://img.shields.io/github/stars/Iotic-Labs/nyx-sdk)](https://github.com/Iotic-Labs/nyx-sdk)
[![Discord](https://img.shields.io/discord/1285252646554304555)](https://discord.gg/zS8pVHjqSf)


🌟 **Nyx Client SDK** offers a simple API for interacting with data in your Nyx network. Subscribe, search and download data from across your federated network with
ease, or if you're a publisher, easily created, update, or delete your existing data products programmatically!

If you're looking for an out of the box experience, try installing [nyx-extras](https://github.com/Iotic-Labs/nyx-sdk/tree/main/nyx_extras), to seamlessly and quickly
build powerful AI applications, to interact with data from your Nyx network!

[![https://iotics.com](https://img.shields.io/badge/Powered%20by-Iotics-blue)](https://iotics.com)
</div>

## 🚧 Status

The Nyx ecosystem is at an early stage of its development, please give us feedback through the [Github issues](https://github.com/Iotic-Labs/nyx-sdk/issues).

## What is the Nyx Client SDK

The Nyx Client SDK is a Python library that provides an API for easy interaction with the Nyx Platform. It enables end users to seamlessly connect their data to the Nyx ecosystem, search for data, subscribe to it, and consume it. With this SDK, users can ultimately build powerful AI applications.

Several examples of SDK usage in an AI context are available:

- [RAG demo examples](https://github.com/Iotic-Labs/nyx-sdk/tree/main/examples)
- `https://[nyx_host]/try-me-now`

See also [What is Nyx](https://github.com/Iotic-Labs/nyx-sdk?tab=readme-ov-file#-what-is-nyx)

# 🔥 Quick Start

## Installation

The Nyx Client SDK is available on [PyPI](https://pypi.org/project/nyx-client/) and can be installed via `pip` running the following command.

`pip install nyx-client`

## First time set up

Once the library is installed you can run `nyx-client init` to generate the .env file. You'll be asked to provide your Nyx username, password and Nyx endpoint.

<details>
<summary>Example output</summary>

```shell
NYX_URL=<ENTER URL>
NYX_EMAIL=<ENTER EMAIL>
NYX_PASSWORD=<ENTER PASSWORD>
```
</details>


## As a data producer

### I want to connect my Data

```python
from nyx_client import NyxClient

client = NyxClient()
client.create_data(
    name="MyData1",
    title="My Data #1",
    description="The description of the data #1",
    size=1080,
    genre="ai",
    categories=["cat1", "cat2", "cat3"],
    download_url="http://storage/dataset1.csv",
    content_type="text/csv",
    lang="fr",
    preview="col1, col2, col3\naaa, bbb, ccc",
    license_url="https://opensource.org/licenses/MIT",
)
```

### I want to delete/disconnect my Data

```python
from nyx_client import NyxClient

client = NyxClient()
client.delete_data_by_name(name="MyData1")
```

## As an application builder

### I want to subscribe to some data

```python
from nyx_client import NyxClient

client = NyxClient()
found_data = client.get_data(categories[genre="ai", categories=["cat1", "cat"], content_type="text/csv"])
for data in found_data:
  client.subscribe(data)
```

### I want to consume the data

```python
from nyx_client import NyxClient

client = NyxClient()
subscribed_data = client.my_subscriptions()
for data in subscribed_data:
  print(f"Downloading data {data.name}")
  content = data.as_string() # NOTE: If this is a binary file, use as_bytes() instead.
```

## 👉 Gotchas

- If the Data has been deleted/disconnected from Nyx, the SDK will no longer be able to access it. Ensure that the data is still available.

The Nyx ecosystem is at an early stage of its development, please give us feedback through [Github issues](https://github.com/Iotic-Labs/nyx-sdk/issues).

- If you get the SSL error
`httpcore.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`

then it may be that you need to set some environment variables like this before running your script:
```shell
CERT_PATH=$(python -m certifi)
export SSL_CERT_FILE=${CERT_PATH}
export REQUESTS_CA_BUNDLE=${CERT_PATH}
```

## 🐞 Troubleshooting

If you encounter any issues, ensure that:

- Your virtual environment is activated.
- All required dependencies are installed.
- Environment variables are set correctly.
- If an issue persists, check the Issues section on github

For further assistance:
- Refer to the [project documentation](https://nyx-client.readthedocs.io/en/stable)
  - 💡 If you have cloned the Git repo, you can run `make docs` and then view `docs/index.html`.
- [Raise an issue](https://github.com/Iotic-Labs/nyx-sdk/issues) on GitHub
- [Chat with us](https://discord.gg/zS8pVHjqSf) on Discord [![Discord](https://img.shields.io/discord/1285252646554304555)](https://discord.gg/zS8pVHjqSf)

## 🤝 Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](https://github.com/Iotic-Labs/nyx-sdk/blob/main/CONTRIBUTING.md) for guidelines.

## ⚖️ Terms and conditions

[https://www.get-nyx.io/terms](https://www.get-nyx.io/terms)
