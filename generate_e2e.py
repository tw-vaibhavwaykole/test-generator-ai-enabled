import os
import json
import yaml
from typing import List
from dotenv import load_dotenv
import logging

from langchain_community.callbacks import get_openai_callback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# New chat prompt modules
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
# Import ChatOpenAI from the updated package.
from langchain_openai import ChatOpenAI

# Community utility to reduce an OpenAPI spec.
from langchain_community.agent_toolkits.openapi.spec import reduce_openapi_spec

# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set in the environment.")
logger.info("Environment variables loaded successfully.")

def load_swagger_spec(file_path: str) -> dict:
    """
    Load the Swagger/OpenAPI specification from a YAML or JSON file.
    """
    logger.info(f"Loading specification from {file_path}")
    with open(file_path, "r") as f:
        if file_path.endswith((".yaml", ".yml")):
            spec = yaml.safe_load(f)
        elif file_path.endswith(".json"):
            spec = json.load(f)
        else:
            raise ValueError("Unsupported file format. Use YAML or JSON.")
    return spec

def load_and_reduce_spec(file_path: str) -> str:
    """
    Load a swagger spec and reduce it to its key components.
    If the spec is in Swagger 2.0 format (without "servers"), add a default "servers" field.
    Returns the reduced spec as a YAML string.
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

def combine_and_maybe_summarize_specs(file_paths: List[str], llm: ChatOpenAI, token_limit: int = 3000) -> str:
    """
    Given a list of swagger file paths, load and reduce each one,
    then combine them into a single string. If the combined text exceeds
    an approximate token limit, summarize it using a chain.
    """
    logger.info("Combining specifications from files.")
    specs = [load_and_reduce_spec(path) for path in file_paths]
    combined_spec = "\n".join(specs)
    # Rough heuristic: assume ~4 characters per token.
    if len(combined_spec) > token_limit * 4:
        logger.info("Combined spec is too long; summarizing...")
        summary_prompt_template = (
            "You are an expert in API documentation summarization. "
            "The text below is a concatenation of reduced Swagger/OpenAPI specifications. "
            "Summarize the key endpoints, required parameters, and response structures concisely. "
            "Only output the concise summary.\n\nText:\n{text}"
        )
        summary_chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template("You are an expert summarizer for API documentation."),
            HumanMessagePromptTemplate.from_template(summary_prompt_template)
        ])
        # Create the summary chain using the pipe operator and invoke it.
        summary_chain = llm | summary_chat_prompt
        summary_input = summary_chat_prompt.format(text=combined_spec)
        summarized = summary_chain.invoke(summary_input)
        # Log the output of the invoke method and convert to string if needed.
        if hasattr(summarized, 'content'):
            summarized_content = summarized.content
        else:
            summarized_content = str(summarized)  # Ensure it's a string
        logger.info("Summarization complete. Output:\n%s", json.dumps(summarized_content, indent=4, ensure_ascii=False))
    else:
        logger.info("No summarization needed for combined spec.")
    return combined_spec

# Define a chat prompt for generating the test code.
chat_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are an expert test automation engineer who generates end-to-end API test code in Python."
    ),
    HumanMessagePromptTemplate.from_template(
        "Using the following combined API specification and scenario description, generate complete, runnable Python code for an end-to-end test.\n\n"
        "Requirements:\n"
        "  - Organize the code into functions (one per API call).\n"
        "  - Use the 'requests' library to perform API calls.\n"
        "  - Include proper assertions and error handling for the tests generated.\n"
        "  - Output the complete Python function code without any Markdown formatting.\n"
        "  - Ensure that the generated code is complete and does not end abruptly or with partial tokens.\n"
        "  - Follow best practices for modularity and readability.\n"
        "  - Fetch endpoints, methods, parameters from the spec.\n" 
        "  - Generate testdata as per the schema.\n"
        "  - Ensure to add Google style documentation but keep it minimal.\n\n"
        "Combined API Specification:\n{combined_spec}\n\n"
        "Scenario Description:\n{scenario}\n"
    )
])

# Create a ChatOpenAI instance with the API key.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=2048)
logger.info("ChatOpenAI instance created.")

# Create the main chain using the pipe operator.
# Note: The correct chain order is prompt first, then the LLM.
chain = chat_prompt | llm


def generate_test_code(swagger_files: List[str], scenario_text: str) -> str:
    """
    Generate Python test code given multiple swagger files and a scenario description.
    The swagger files are reduced and combined (and summarized if needed) to fit within token limits.
    Uses the pipe operator and explicit invocation to pass input data into the chain.
    """
    logger.info("Generating test code...")

    # Combine and optionally summarize the swagger specs
    combined_spec = combine_and_maybe_summarize_specs(swagger_files, llm)
    input_data = {"combined_spec": combined_spec, "scenario": scenario_text}

    # Use the callback manager to track token usage for this invocation.
    with get_openai_callback() as cb:
        generated_code = chain.invoke(input_data)

    # Log the token usage details
    logger.info(f"Total Tokens: {cb.total_tokens}")
    logger.info(f"Prompt Tokens: {cb.prompt_tokens}")
    logger.info(f"Completion Tokens: {cb.completion_tokens}")
    logger.info(f"Total Cost (USD): ${cb.total_cost}")

    # If the generated output has a 'content' attribute, use that; otherwise use the raw output.
    if hasattr(generated_code, 'content'):
        logger.info("Summarization complete")
        generated_code = generated_code.content
    else:
        logger.info("Summarization complete")

    logger.info("Test code generation complete.")
    return generated_code

if __name__ == "__main__":
    # Hard-coded file paths for Swagger specifications and the scenario file.
    swagger_files = [
        "specs/dd_spec.yaml"
        # Add more swagger file paths here if needed.
    ]
    scenario_file = "scenarios/dd_scenarios.txt"

    # Read the scenario text from the file.
    with open(scenario_file, "r") as sf:
        scenario_text = sf.read()
    logger.info(f"Scenario file {scenario_file} loaded.")

    # Generate the test code.
    test_code = generate_test_code(swagger_files, scenario_text)

    # Output the generated code to /output/generated_tests_e2e.py
    output_file = "output/generated_tests_e2e.py"
    os.makedirs("output", exist_ok=True)
    with open(output_file, "w") as outf:
        outf.write(test_code)
    logger.info(f"Generated Python Test Code has been saved to: {output_file}")
    print("Generated Python Test Code has been saved to:", output_file)
