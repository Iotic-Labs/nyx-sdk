# RAG API web server with confidence judging

Similar to [`rag_api`](../rag_api) except that it first lets the LLM attempt to answer the query. If not confident enough to answer, re-runs the query using data retrieved from nyx subscriptions.

## Overview

- See [`rag_api`](../rag_api/README.md#overview)
- Uses the `Utils.with_confidence` prompt modification to demand the LLM judge its own answer.

## Setup

See [parent README](../../README.md#-installation)

ℹ️ Make sure you have set the `OPENAI_API_KEY` environment variable.

## Usage

- See [`rag_api`](../rag_api/README.md#usage)
