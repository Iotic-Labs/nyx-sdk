import logging

import streamlit as st
from agent import build_structed_agent_and_datasets, combine

log = logging.getLogger(__name__)

st.title("Nyx Chat")
st.text("Ask questions about your data in Nyx, both structured and unstructured")

agent_0, dataset, parser = build_structed_agent_and_datasets()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Query the Nyx agent, with the dataset
    # Note: we only pass the dataset as it means the agent doesn't need to
    # fetch data for every single query
    structed_response = agent_0.query(prompt, data=dataset)

    # Get the TOP K chunk matches from unstructured text
    unstructed_response = parser.query(prompt, k=3)

    response = combine(prompt, structed_response, " ".join(unstructed_response.chunks))
    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(response)
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
