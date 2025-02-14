import os
import json
import yaml
from typing import List
from dotenv import load_dotenv
import logging

from langchain_community.callbacks import get_openai_callback
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits.openapi.spec import reduce_openapi_spec

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment.")
logger.info("Environment variables loaded successfully.")


def load_swagger_spec(file_path: str) -> dict:
    """Load the Swagger/OpenAPI specification from a YAML or JSON file.

    Args:
        file_path (str): Path to the specification file.

    Returns:
        dict: Loaded Swagger/OpenAPI specification.
    """
    logger.info("Loading specification from %s", file_path)
    with open(file_path, "r") as f:
        if file_path.endswith((".yaml", ".yml")):
            spec = yaml.safe_load(f)
        elif file_path.endswith(".json"):
            spec = json.load(f)
        else:
            raise ValueError("Unsupported file format. Use YAML or JSON.")
    return spec


def load_and_reduce_spec(file_path: str) -> str:
    """Load a Swagger spec and reduce it to key components.

    If the spec is in Swagger 2.0 format (without 'servers'), a default field is added.

    Args:
        file_path (str): Path to the Swagger/OpenAPI specification file.

    Returns:
        str: Reduced spec as a YAML string.
    """
    spec = load_swagger_spec(file_path)
    if "servers" not in spec:
        host = spec.get("host")
        basePath = spec.get("basePath", "")
        schemes = spec.get("schemes", ["https"])
        if host:
            scheme = schemes[0] if schemes else "https"
            spec["servers"] = [{"url": f"{scheme}://{host}{basePath}"}]
        logger.info("Added default servers field for Swagger 2.0 spec.")
    reduced = reduce_openapi_spec(spec)
    return yaml.dump(reduced, sort_keys=False)


def combine_and_maybe_summarize_specs(
    file_paths: List[str], llm: ChatOpenAI, token_limit: int = 3000
) -> str:
    """Combine and optionally summarize reduced Swagger specifications.

    Args:
        file_paths (List[str]): List of Swagger spec file paths.
        llm (ChatOpenAI): Chat model instance.
        token_limit (int, optional): Token threshold for summarization. Defaults to 3000.

    Returns:
        str: Combined (or summarized) Swagger specification.
    """
    logger.info("Combining specifications from files.")
    specs = [load_and_reduce_spec(path) for path in file_paths]
    combined_spec = "\n".join(specs)
    # if len(combined_spec) > token_limit * 4:
    #     logger.info("Combined spec is too long; summarizing...")
    #     summary_prompt_template = (
    #         "You are an expert in API documentation summarization. "
    #         "The text below is a concatenation of reduced Swagger/OpenAPI specifications. "
    #         "Summarize the key endpoints, required parameters, and response structures concisely. "
    #         "Only output the concise summary.\n\nText:\n{text}"
    #     )
    #     summary_chat_prompt = ChatPromptTemplate.from_messages([
    #         SystemMessagePromptTemplate.from_template(
    #             "You are an expert summarizer for API documentation."
    #         ),
    #         HumanMessagePromptTemplate.from_template(summary_prompt_template),
    #     ])
    #     summary_chain = llm | summary_chat_prompt
    #     summary_input = summary_chat_prompt.format(text=combined_spec)
    #     summarized = summary_chain.invoke(summary_input)
    #     if hasattr(summarized, "content"):
    #         summarized_content = summarized.content
    #     else:
    #         summarized_content = str(summarized)
    #     logger.info("Summarization complete.")
    #     combined_spec = summarized_content
    # else:
    #     logger.info("No summarization needed for combined spec.")
    return combined_spec


# Define the chat prompt template with a test data placeholder.
chat_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are an expert test automation engineer who generates end-to-end API test code in Python."
    ),
    HumanMessagePromptTemplate.from_template(
        "Using the following combined API specification, scenario description, and test data, generate complete, runnable Python code for an end-to-end test.\n\n"
        "Requirements:\n"
        "  - Organize the code into functions (one per API call).\n"
        "  - Use the 'requests' library to perform API calls.\n"
        "  - Add proper assertions for all important steps of the testcase.\n"
        "  - Output the complete Python function code without any Markdown formatting.\n"
        "  - Ensure that the generated code is complete and does not end abruptly or with partial tokens.\n"
        "  - Follow best practices for modularity and readability.\n"
        "  - Fetch endpoints, methods, and parameters from the spec.\n"
        "  - Generate test data as per the schema provided in the spec.\n"
        "  - Include minimal Google style documentation.\n\n"
        "Combined API Specification:\n{combined_spec}\n\n"
        "Scenario Description:\n{scenario}\n\n"
        "Test Data:\n{test_data}\n"
    )
])

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=2048)
logger.info("ChatOpenAI instance created.")

chain = chat_prompt | llm


def generate_test_code(
    swagger_files: List[str], scenario_text: str, test_data: str
) -> str:
    """Generate Python test code from Swagger specs, a scenario, and test data.

    Args:
        swagger_files (List[str]): List of Swagger spec file paths.
        scenario_text (str): The scenario description.
        test_data (str): Test data in JSON string format.

    Returns:
        str: Generated Python test code.
    """
    logger.info("Generating test code...")
    combined_spec = combine_and_maybe_summarize_specs(swagger_files, llm)
    input_data = {
        "combined_spec": combined_spec,
        "scenario": scenario_text,
        "test_data": test_data,
    }
    with get_openai_callback() as cb:
        generated_code = chain.invoke(input_data)
    logger.info("Total Tokens: %s", cb.total_tokens)
    logger.info("Prompt Tokens: %s", cb.prompt_tokens)
    logger.info("Completion Tokens: %s", cb.completion_tokens)
    logger.info("Total Cost (USD): $%s", cb.total_cost)
    if hasattr(generated_code, "content"):
        generated_code = generated_code.content
    logger.info("Test code generation complete.")
    return generated_code


if __name__ == "__main__":
    swagger_files = [
        "specs/dd_spec.yaml"
    ]
    scenario_file = "scenarios/dd_scenarios.txt"
    with open(scenario_file, "r") as sf:
        scenario_yaml = yaml.safe_load(sf)
    scenario_text = scenario_yaml.get("scenario", "")
    test_data = scenario_yaml.get("test_data", {})
    logger.info("Scenario file %s loaded.", scenario_file)
    test_data_str = json.dumps(test_data, indent=2)
    test_code = generate_test_code(swagger_files, scenario_text, test_data_str)
    output_file = "output/generated_tests_e2e.py"
    os.makedirs("output", exist_ok=True)
    with open(output_file, "w") as outf:
        outf.write(test_code)
    logger.info("Generated Python Test Code has been saved to: %s", output_file)
    print("Generated Python Test Code has been saved to:", output_file)
