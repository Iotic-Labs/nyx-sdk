# RAG API web server

This example provides a web server chat bot that will consider all subscribed-to data sources.

## Overview

Unlike the high level CLI chat prompts, this demonstrates explicit configuration of:

- Nyx data retrieval
- Ingestion of nyx data into an in-memory DB
- Configuration of LLM provider agent
- Configuration of RAG agent to leverage nyx data stored in DB

## Setup

See [parent README](../../README.md#-installation)

ℹ️ Make sure you have set the `OPENAI_API_KEY` environment variable.

## Usage

1. Run the script
   ```
   python examples/advanced/rag_api/app.py
   ```

2. Open the [minimal web UI](../chat_interface.html) to perform queries
