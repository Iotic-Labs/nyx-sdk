# Multi-Agent chat with all data

This is a demo application that shows how Nyx allows out of the box processing of 
both structured and unstructed data sources. 

## Overview

What each agent does
 - The first agent is a simple `NyxLangChain` instance, it handles structured data, as in the other examples
 - The next agent, is just a vector matcher, it vectorizes unstructured data, and finds matches based on the user's query
 - The final agent aggregates the two results, and only displays what is relevant.

This approach allows us to ask questions across multiple data sources, and recieve a varied response. The introduction
of the aggregation agent, also introduces a bit of flare in the answers (Base `NyxLangChain` is purposefully bland) and
is able to apply the data to actually answer the users questions

## Setup

 - Firstly create a virtual enviornment
 - `pip install -r requirements.txt` to install requirements
 - run `streamlit run main.py` and this will open your browser on the chat window

ℹ️ Make sure you have set the `OPENAI_API_KEY` environment variable.

## Notes

 1. This is not optimized, currently everything executes in order, so the responses can be a bit slow

