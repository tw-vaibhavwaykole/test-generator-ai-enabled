#!/usr/bin/env python3
"""
generate_scenarios.py

This script loads an OpenAPI specification using the parser defined in openapi_parser.py,
extracts all endpoints, and then generates plain English API test scenarios for each endpoint
using LangChain’s latest chaining style (using the pipe operator).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, root_validator

# Import the parser functions from your existing openapi_parser.py
from openapi_parser import load_api_spec, endpoints

# ---------------------------------------------------------------------------
# Import LangChain components for chat-based models
# ---------------------------------------------------------------------------
from langchain.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_community.chat_models import ChatOpenAI

# Define the Pydantic model for a single test scenario.
class TestScenario(BaseModel):
    test_scenario: str
    test_steps: List[str]

# Define a container model that can accept either a single TestScenario or a list.
class TestScenarioOutput(BaseModel):
    scenarios: List[TestScenario]

    @root_validator(pre=True)
    def unwrap_input(cls, values: Any) -> Any:
        # If the input is already a list, use it.
        if isinstance(values, list):
            if not values:
                raise ValueError("Received an empty list; expected a valid object or non-empty list.")
            return {"scenarios": values}
        # If the input is a dict, wrap it in a list.
        elif isinstance(values, dict):
            return {"scenarios": [values]}
        else:
            raise ValueError("Invalid input type for TestScenarioOutput; expected a dict or list.")

# -----------------------------------------------------------------------------
# Configure Logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Generate Test Scenarios Using LangChain Chaining Style
# -----------------------------------------------------------------------------
def generate_test_scenario_for_endpoint(endpoint: Dict[str, Any]) -> List[dict]:
    """
    Generate a plain English API test scenario for a single endpoint.

    Uses LangChain's chaining style (pipe operator) to compose a prompt, query the LLM,
    and then parse its output into one or more TestScenario objects.

    Args:
        endpoint (Dict[str, Any]): Dictionary with details of an endpoint.

    Returns:
        List[dict]: A list of dictionaries, each representing a TestScenario.
    """
    # Updated prompt template.
    prompt_template = (
        "Generate plain English ONLY one API test scenario for the following endpoint details:\n\n"
        "Method: {method}\n"
        "Path: {path}\n"
        "Summary: {summary}\n"
        "Description: {description}\n"
        "Parameters: {parameters}\n"
        "Responses: {responses}\n\n"
        "Please output your answer as valid JSON in the following format:\n"
        "{{\n"
        '  "test_scenario": "<a plain English description>",\n'
        '  "test_steps": ["<a detailed list of test steps>"]\n'
        "}}\n"
    )

    # Create a chat prompt template using the chat-based prompt components.
    chat_prompt = ChatPromptTemplate.from_messages([
        HumanMessagePromptTemplate.from_template(prompt_template)
    ])

    # Initialize the chat-based LLM using ChatOpenAI with GPT-4o Mini.
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)

    # Initialize the output parser so that the JSON output is parsed into TestScenarioOutput.
    output_parser = PydanticOutputParser(pydantic_object=TestScenarioOutput)

    # Chain the prompt, LLM, and output parser.
    chain = chat_prompt | llm | output_parser

    # Invoke the chain with endpoint details.
    scenario_output = chain.invoke({
        "method": endpoint.get("method", ""),
        "path": endpoint.get("path", ""),
        "summary": endpoint.get("summary", ""),
        "description": endpoint.get("description", ""),
        "parameters": json.dumps(endpoint.get("parameters", []), indent=2),
        "responses": json.dumps(endpoint.get("responses", []), indent=2)
    })

    # Return the list of TestScenario dictionaries.
    return [scenario.dict() for scenario in scenario_output.scenarios]

def generate_test_scenarios_for_all(endpoints_list: List[Dict[str, Any]]) -> Dict[str, List[dict]]:
    """
    Generate plain English test scenarios for all endpoints.

    Args:
        endpoints_list (List[Dict[str, Any]]): List of endpoint dictionaries.

    Returns:
        Dict[str, List[dict]]: A mapping from an endpoint identifier (e.g. "GET /pet/{petId}")
                               to its generated test scenarios (as a list of dictionaries).
    """
    scenarios = {}
    for endpoint in endpoints_list:
        key = f"{endpoint.get('method', '')} {endpoint.get('path', '')}"
        try:
            scenario = generate_test_scenario_for_endpoint(endpoint)
            scenarios[key] = scenario
            logger.info(f"Generated test scenario for endpoint: {key}")
        except Exception as e:
            logger.error(f"Failed to generate scenario for {key}", exc_info=True)
            scenarios[key] = [{"error": str(e)}]
    return scenarios

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
def main():
    load_dotenv()

    """
    Main function to:
      - Load the API specification using openapi_parser.py.
      - Extract endpoints from the specification.
      - Generate plain English test scenarios for each endpoint using LangChain chaining.
      - Print the resulting test scenarios in JSON format.
    """
    # Update this path as needed. The spec file can be in YAML or JSON.
    spec_file_path = Path("specs/dd_spec.yaml")
    try:
        # Load and validate the API spec.
        api_spec = load_api_spec(spec_file_path)
        # Extract the endpoints from the API spec.
        endpoints_list = endpoints(api_spec)
        logger.info(f"Extracted {len(endpoints_list)} endpoints from the API specification.")
        # Generate test scenarios for all endpoints.
        test_scenarios = generate_test_scenarios_for_all(endpoints_list)
        print("=== Generated API Test Scenarios ===")
        print(json.dumps(test_scenarios, indent=4))
    except Exception as e:
        logger.error("Failed to generate test scenarios", exc_info=True)

if __name__ == "__main__":
    main()
