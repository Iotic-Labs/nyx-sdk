# RAG API web server with source metadata

Similar to [`rag_api`](../rag_api) except it also returns information about the sources that were used to answer the query.

## Overview

- See [`rag_api`](../rag_api/README.md#overview)
- Uses the `Utils.with_sources` prompt modification to demand information about the data sources be included in responses.

## Setup

See [parent README](../../README.md#-installation)

ℹ️ Make sure you have set the `OPENAI_API_KEY` environment variable.

## Usage

- See [`rag_api`](../rag_api/README.md#usage)
