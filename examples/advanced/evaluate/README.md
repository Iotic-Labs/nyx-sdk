# LLM Comparison Tool

This application is built using the nyx_client SDK to compare the performance of different Language Models (LLMs) on a set of predefined questions.

## Overview

This tool evaluates the performance of various LLMs (OpenAI and Cohere models) by:
1. Asking a set of predefined questions
2. Measuring response time
3. Judging the accuracy and source usage of the responses


## Setup

1. Install the required packages:
   ```
   pip install -r examples/requirements.txt
   ```

2. Set up your API keys for OpenAI and Cohere in your environment variables or through the nyx_client configuration.

## Usage

1. Run the script:
   ```
   python examples/advanced/evaluate/evaluate.py
   ```

2. The script will query different LLMs with the predefined questions and evaluate their responses.

3. Results are saved to `llm_comparison_results.json`.

## Customization

- Modify the `input_prompts` in `config.py` to change the evaluation questions.
- Adjust the `clients` tuple in `config.py` to include or exclude specific LLM models.
- Update the `JUDGE_PROMPT` in `config.py` to refine the evaluation criteria.

## Note

Larger models (gpt-4o and command-r-plus) are commented out in the `clients` tuple to manage costs. Uncomment these in `config.py` to include them in the evaluation.

## Output

The script generates a JSON file with detailed results for each LLM, including:
- Accuracy scores
- Source usage
- Execution time
- Input questions and outputs

This data can be used for further analysis and comparison of LLM performance.

Optionally it can be uploaded to https://endearing-twilight-588648.netlify.app/ to explore