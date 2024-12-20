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

import json

from flask import Flask, request
from flask_cors import CORS
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai.chat_models import ChatOpenAI

from nyx_client import NyxClient
from nyx_extras import Parser, Utils,

app = Flask(__name__)
CORS(app)

log = app.logger
client = NyxClient()


@app.post("/chat")
def chat():
    try:
        prompt = request.json["query"]
    except KeyError:
        return 'bad request, body issue: {"query": "the query"} expected', 400

    try:
        # 1. Create a new LLM model
        llm = ChatOpenAI(model="gpt-4", temperature=0)
        # 2. Query the LLM with the prompt and have it act as a judge of its own response
        llm_response = llm.invoke(Utils.with_confidence(prompt))
        llm_content = json.loads(llm_response.content)
        print(llm_content)

        # 3. Check if the LLM provides a confident answer
        if llm_content.get("confidence", 0) > 0.8:  # Assuming confidence is a value between 0 and 1
            print(llm_content.get("content"))
            return {
                "message": llm_content.get("content").replace("\n", "<br />").replace('\\"', '"').replace('"', ""),
            }
        else:
            # 4. Otherwise use the LLM to query your subscribed nyx data
            data = client.my_subscriptions()
            # 2. Load them into sql-lite DB in memory
            engine = Parser.data_as_db(data)

            # 3. Build langChain specific tooling from this, and send it a prompt!
            db = SQLDatabase(engine=engine)
            # Create sql agent with new llm model
            agent_executor = create_sql_agent(llm, db=db, agent_type="tool-calling")

            # Extend the prompt to include sources
            res = agent_executor.invoke({"input": Utils.with_sources(prompt)})

            # 4. Print the result
            print(res["output"])
            return {
                "message": res["output"].replace("\n", "<br />").replace('\\"', '"').replace('"', ""),
            }
    except Exception as e:
        log.error("Exception: %s", e.with_traceback(None))
        return '{"message": "Something went wrong, shutting down"}', 500


if __name__ == "__main__":
    app.run(debug=True, port=5002)
