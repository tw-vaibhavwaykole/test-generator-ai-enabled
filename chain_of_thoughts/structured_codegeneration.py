import os
import json
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback

load_dotenv()


def load_merged_json(file_path: str) -> dict:
    """
    Load the merged JSON file produced by the pre-processing module.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


def generate_test_code(merged_json: dict) -> str:
    """
    Use LangChain's components to generate a complete Python test script
    based on the provided merged JSON and print token usage metadata.
    """
    prompt_template = """
You are a Python code generation assistant. Your task is to generate a complete, robust Python end-to-end test script using the pytest framework and the requests library. Follow these guidelines:

1. The script must be executable as a pytest file without extraneous markdown formatting.
2. Do not encapsulate test steps inside a global object; instead, generate individual test functions for each test step.
3. Each test function should:
   - Construct the full URL by concatenating the base URL (from static_details.base_url) with the endpoint, replacing any placeholders with corresponding values from "merged_path_params".
   - Send an HTTP request using the HTTP method specified (e.g., POST) with:
       - JSON payload from "merged_payload"
       - HTTP headers from "merged_headers"
       - Query parameters from "merged_query_params"
   - Assert that the response status code is 200 (or as specified).
   - Log or print the response content.
   - Include proper error handling.
4. For any field in the merged payload, headers, or query parameters that has the placeholder "<value>", inspect the schema provided in the JSON and replace "<value>" with the best possible default (e.g., if the field has an enum, choose the first value; if a string without an enum, use "default").
5. Include a main test runner if appropriate, so that the test functions can be executed directly.
6. Log or print when the test starts and test ends.
7. let the timeout be 5 seconds.
8. assert the test code for the response code.

Below is the JSON object describing the test case:
{merged_json}

Generate the complete Python code for the test script.
    """
    prompt = PromptTemplate(
        input_variables=["merged_json"],
        template=prompt_template
    )
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("Please set the OPENAI_API_KEY environment variable.")

    # Initialize the LLM using ChatOpenAI
    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")

    # Correctly chain the prompt and the LLM (prompt first, then llm)
    chain = prompt | llm

    # Use callback to capture token usage
    with get_openai_callback() as cb:
        result = chain.invoke({
            "merged_json": json.dumps(merged_json, indent=2)
        })

    # Print token usage metadata
    print("Token usage details:")
    print(f"  Total Tokens: {cb.total_tokens}")
    print(f"  Prompt Tokens: {cb.prompt_tokens}")
    print(f"  Completion Tokens: {cb.completion_tokens}")
    print(f"  Total Cost (USD): ${cb.total_cost:.5f}")

    return result.content


def main():
    # Path to the merged JSON produced by the pre-processing module.
    scenario_file_path = "output/structured_preprocessing.json"  # adjust as needed
    output_file_path = "output/structured_generated_test_code.py"

    # Load the merged JSON.
    merged_json = load_merged_json(scenario_file_path)

    # Generate the test code using the updated chain.
    test_code = generate_test_code(merged_json)

    # Print the generated test code.
    print("Generated Test Code:\n")
    print(test_code)

    # Ensure the output directory exists.
    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

    # Write the generated code to a file.
    with open(output_file_path, "w") as f:
        f.write(test_code)

    print(f"Test code has been saved to {output_file_path}")


if __name__ == "__main__":
    main()
