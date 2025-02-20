#!/usr/bin/env python3
"""
generate_testcases.py

This module generates complete Python API test functions using LLM chains.
It does the following:
  - Loads an OpenAPI specification via openapi_parser.py.
  - Extracts endpoints from the specification.
  - Generates plain English test scenarios for each endpoint using LangChain (as defined in generate_scenarios.py).
  - Uses an LLM chain to convert each plain English scenario into a complete Python test function.
  - Writes the generated test functions to an output file (default: output/generated_tests.py).

Usage:
    $ python generate_testcases.py

Dependencies:
  - Python standard libraries (os, json, re, logging, pathlib)
  - LangChain (LLM chains using the pipe operator)
  - dotenv (for environment variables)
  - Modules: openapi_parser and generate_scenarios (adjust import paths as needed)
"""

import os
import json
import re
import logging
from pathlib import Path
from typing import Union, List

from dotenv import load_dotenv

# Import chat-based LLM and prompt components.
from langchain_community.chat_models import  ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate, HumanMessagePromptTemplate

# Import the API spec loader and endpoint extractor.
from langchain_learnings.openapi_parser import load_api_spec, endpoints
# Import the scenario generator that uses LLM chaining (from your generate_scenarios.py).
from generate_scenarios import generate_test_scenarios_for_all

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestCaseGenerator:
    def __init__(self,
                 output_file: str = "output/generated_tests.py",
                 base_url: str = None):
        """
        Initialize the TestCaseGenerator.

        Args:
            output_file (str): Path for the output test file.
            base_url (str): Base URL for the API; if not provided, uses environment variable API_BASE_URL.
        """
        load_dotenv()  # Load environment variables from .env file, if available.
        self.output_file = Path(output_file)
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:8000")

    @staticmethod
    def sanitize_function_name(name: str) -> str:
        """
        Sanitize a string to be a valid Python function name.
        Replaces non-alphanumeric characters with underscores.
        """
        sanitized = re.sub(r"\W+", "_", name)
        sanitized = re.sub(r"^[^a-zA-Z_]+", "", sanitized)
        return sanitized.lower()

    def generate_test_function_llm(self, endpoint_key: str, scenario:Union[dict, List[dict]]) -> str:
        """
        Use an LLM chain to generate a complete Python test function based on the test scenario.

        Args:
            endpoint_key (str): A string like "GET /users".
            scenario (dict): Dictionary with keys "test_scenario" and "test_steps".

        Returns:
            str: The complete Python test function code.
        """
        try:
            method, path = endpoint_key.split(" ", 1)
        except ValueError:
            method, path = "GET", endpoint_key

        func_name = f"test_{method.lower()}_{self.sanitize_function_name(path)}"

        # Construct a prompt template for generating the test function.
        prompt_template = (
            "You are an expert Python Test Engineer. "
            "Generate a complete and fully executable Python test function using the requests library for API testing. "
            "The test function should use the following details:\n\n"
            "Endpoint: {endpoint_key}\n"
            "Base URL: {base_url}\n"
            "Test Scenario: {test_scenario}\n"
            "Test Steps:\n{test_steps}\n\n"
            "The generated function should include proper imports, initialize the URL, and "
            "implement each test step as code. The function name should be '{func_name}'. "
            "Output only the complete Python function code, including the function definition. "
            "Output only the complete Python function code without any Markdown formatting or code fences."
            "Ensure that the generated code is complete and does not end abruptly or with partial tokens."
        )

        # Create a chat prompt template from the prompt text.
        chat_prompt = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(prompt_template)
        ])

        # Initialize the chat-based LLM using ChatOpenAI with GPT-4o Mini.
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_tokens=1024)

        # Compose the chain using the pipe operator style.
        chain = chat_prompt | llm

        #Use the first scenario if multiple scenarios predicted by LLM
        if isinstance(scenario, list) :
            scenario = scenario[0]

        # Prepare test steps and scenario description.
        test_steps = "\n".join(scenario.get("test_steps", []))
        test_scenario = scenario.get("test_scenario", "")

        # Invoke the chain with the provided parameters.
        generated_code = chain.invoke({
            "endpoint_key": endpoint_key,
            "base_url": self.base_url,
            "test_scenario": test_scenario,
            "test_steps": test_steps,
            "func_name": func_name
        })

        logger.info("Generated test function for endpoint: %s", endpoint_key)
        return generated_code.content.strip()

    def generate_test_file_content_from_scenarios(self, scenarios: dict) -> str:
        """
        Generate the complete content of the test file from the provided test scenarios.

        Args:
            scenarios (dict): Dictionary mapping an endpoint key (e.g., "GET /users")
                              to its generated test scenario.

        Returns:
            str: The complete content of the test file.
        """
        header = f'''"""
Auto-generated test cases from API test scenarios.
This file is generated automatically and contains executable tests.
"""

import requests
import pytest

BASE_URL = "{self.base_url}"
'''
        functions_code = ""
        for endpoint_key, scenario in scenarios.items():
            # If there was an error generating the scenario, skip test generation.
            if "error" in scenario:
                logger.warning("Skipping test generation for %s due to error: %s", endpoint_key, scenario["error"])
                continue
            functions_code += self.generate_test_function_llm(endpoint_key, scenario) + "\n\n"
        return header + "\n\n" + functions_code

    def write_test_file_content(self, content: str):
        """
        Write the generated test file content to the output file.
        """
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        with self.output_file.open("w", encoding="utf-8") as f:
            f.write(content)
        logger.info("Generated test cases have been written to '%s'.", self.output_file)


# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
def main():
    load_dotenv()

    """
    Main function to:
      - Load the API specification using openapi_parser.py.
      - Extract endpoints from the specification.
      - Generate plain English test scenarios for each endpoint using an LLM chain.
      - Convert the scenarios into complete Python test functions.
      - Write the generated test cases to the output file.
    """
    # Update this path as needed. The spec file can be YAML or JSON.
    spec_file_path = Path("specs/dd_spec.yaml")
    try:
        # Load and validate the API spec.
        api_spec = load_api_spec(spec_file_path)
        # Extract endpoints from the API spec.
        endpoints_list = endpoints(api_spec)
        logger.info("Extracted %d endpoints from the API specification.", len(endpoints_list))
        # Generate plain English test scenarios for all endpoints.
        test_scenarios = generate_test_scenarios_for_all(endpoints_list)
        print("=== Generated API Test Scenarios ===")
        print(json.dumps(test_scenarios, indent=4))
        # Create a TestCaseGenerator instance.
        generator = TestCaseGenerator()
        # Generate the complete test file content from the test scenarios.
        test_file_content = generator.generate_test_file_content_from_scenarios(test_scenarios)
        # Write the generated test cases to the output file.
        generator.write_test_file_content(test_file_content)
    except Exception as e:
        logger.exception("Failed to generate test cases: %s", e)


if __name__ == "__main__":
    main()
