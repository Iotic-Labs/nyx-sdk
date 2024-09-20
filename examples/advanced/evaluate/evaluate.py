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
import time

from openai import OpenAI
from pydantic import BaseModel

from examples.advanced.evaluate.config import JUDGE_PROMPT, client_openai_sm, clients, input_prompts
from nyx_client.extensions.langchain import NyxLangChain

# Judge OpenAI client
judge = OpenAI()


class Result(BaseModel):
    accuracy: int
    source_accuracy: int
    sources: list[str]


class Test(BaseModel):
    result: Result
    input: str
    output: str
    execution_time: float
    success: bool = True


class Evaluator:
    def __init__(self):
        # Build evaluation prompt with raw contents of documents
        self.data = client_openai_sm.get_subscribed_data()
        doc_str = ""
        for d in self.data:
            contents = d.as_string()
            if contents:
                doc_str += f"\n\n{d.name}: \n\n {contents}"

        self.judge_prompt = JUDGE_PROMPT + doc_str
        self.results = {}
        # Setup result dictionary for each client
        for name, _ in clients:
            self.results[name] = []

    def process(self, query: str, client: NyxLangChain) -> Test:
        print(".", end="", flush=True)  # noqa: T201
        start_time = time.time()
        try:
            # Query the client
            res = client.query(query, data=self.data, update_subscribed=False)
        except Exception as e:
            print("F", end="")  # noqa: T201

            end_time = time.time()
            execution_time = end_time - start_time

            # Log any failures
            judgement = Result(accuracy=0, source_accuracy=0, sources=[])
            return Test(result=judgement, input=query, output=f"{e}", execution_time=execution_time, success=False)

        end_time = time.time()
        execution_time = end_time - start_time

        # Get a scoring from the judge
        judgement_raw = judge.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": JUDGE_PROMPT.format(file_names=[d.title for d in self.data])},
                {"role": "user", "content": f"I asked: {query} Answer: {res} "},
            ],
            response_format=Result,
        )
        judgement = judgement_raw.choices[0].message.parsed
        return Test(result=judgement, input=query, output=res, execution_time=execution_time)

    def run(self):
        for name, client in clients:
            print(f"Querying {name}")  # noqa: T201
            for i in input_prompts:
                test_result = self.process(i, client)
                self.results[name].append(test_result)
            print()  # noqa: T201

        # Output the overall dictionary to a file
        output_file = "llm_comparison_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, default=lambda o: o.dict(), indent=2)

        print(
            f"\nResults have been written to {output_file}"
            " upload to https://endearing-twilight-588648.netlify.app/ "
            "for analysis"
        )  # noqa: T201


if __name__ == "__main__":
    evaluator = Evaluator()
    evaluator.run()
