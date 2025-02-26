import logging
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from plaintext_preprocessing import get_refined_scenario  # Assumes a function that returns refined scenario text

# Configure logging: INFO-level messages will be displayed; debug messages will be hidden by default.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize ChatOpenAI
chat_openai = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)


def run_chain(template_str: str, input_vars: dict, escape_keys: list = None) -> str:
    """
    Helper method to run a prompt chain with the given template and input variables.
    Optionally escapes curly braces for specified keys.

    Args:
        template_str (str): The prompt template string.
        input_vars (dict): Dictionary of input variables for the prompt.
        escape_keys (list, optional): List of keys whose values should have curly braces escaped.

    Returns:
        str: The generated content from the chain.
    """
    if escape_keys:
        for key in escape_keys:
            if key in input_vars:
                input_vars[key] = input_vars[key].replace("{", "{{").replace("}", "}}")
    prompt = PromptTemplate(input_variables=list(input_vars.keys()), template=template_str)
    chain = prompt | chat_openai

    def sync_invoke():
        with get_openai_callback() as cb:
            result = chain.invoke(input_vars)
            logger.debug("Token usage details:")
            logger.debug("  Total Tokens: %s", cb.total_tokens)
            logger.debug("  Prompt Tokens: %s", cb.prompt_tokens)
            logger.debug("  Completion Tokens: %s", cb.completion_tokens)
            logger.debug("  Total Cost (USD): $%.5f", cb.total_cost)
        return result.content

    return sync_invoke()


def generate_test_code(refined_scenario: str) -> str:
    """
    Generate a Python test script using pytest and requests based on the refined scenario.

    The generated script will:
      - Import pytest and requests.
      - Import any additional standard libraries (e.g., logging, time) if needed.
      - Define a single test function (e.g., test_scenario) that combines all test steps into one executable test case with a Google style docstring.
      - Set up any required global variables and endpoints as indicated in the scenario.
      - Construct the API request (for example, POST, PUT, PATCH or any other request) based on the scenario.
      - Add a default timer of 10 seconds for all the API requests (using a timeout parameter) and include that parameter in all test steps.
      - Include robust error handling (e.g., try/except blocks) around the API call to handle potential exceptions gracefully.
      - Assert the responses wherever applicable to validate the expected behavior, including checking status codes and response content (such as JSON keys).
      - Add meaningful inline comments and docstrings for clarity and maintainability.
      - Optionally include a pytest fixture for any common setup or teardown logic if relevant.
      - Configure the logger to only output warnings and errors (e.g., set the logging level to WARNING) to reduce clutter.
      - Ensure the script is self-contained, modular, and can be directly executed (e.g., include a main block that calls pytest.main() if run as __main__).

    Args:
        refined_scenario (str): The refined scenario text which includes test steps and global variables.

    Returns:
        str: The generated Python test script.
    """
    template_str = (
        "Using Google style formatting, generate a fully executable Python test script that uses pytest and the requests "
        "library to test the following scenario. Do not include any markdown formatting (e.g., triple backticks) in your output; "
        "return plain executable Python code only.\n\n"
        "The generated script should:\n"
        "- Import pytest and requests\n"
        "- Import any additional standard libraries (e.g., logging, time) if needed\n"
        "- Define a single test function (e.g., test_scenario) that combines all test steps into one executable test case with a Google style docstring\n"
        "- Set up any required global variables and endpoints as indicated in the scenario\n"
        "- Construct the API request (for example, POST, PUT, PATCH or any other request) based on the scenario\n"
        "- Add a default timer of 10 seconds for all the API requests (using a timeout parameter) and include that parameter in all test steps\n"
        "- Include robust error handling (e.g., try/except blocks) around the API call to handle potential exceptions gracefully\n"
        "- Assert the responses wherever applicable to validate the expected behavior, including checking status codes and response content (such as JSON keys)\n"
        "- Add meaningful inline comments and docstrings for clarity and maintainability\n"
        "- Optionally include a pytest fixture for any common setup or teardown logic if relevant\n"
        "- Configure the logger to only output warnings and errors (e.g., set the logging level to WARNING) to reduce clutter\n"
        "- Ensure the script is self-contained, modular, and can be directly executed (e.g., include a main block that calls pytest.main() if run as __main__)\n\n"
        "Refined Scenario: {refined_scenario}"
    )

    result = run_chain(template_str, {"refined_scenario": refined_scenario}, escape_keys=["refined_scenario"])
    return result


def validate_and_improve_code(generated_code: str) -> str:
    """
    Validates the generated Python code for potential errors or improvements and returns an updated version.

    The LLM should review the code and provide an improved version that fixes errors and implements enhancements,
    while preserving the original functionality. The output should be plain executable Python code.

    Args:
        generated_code (str): The original generated Python code.

    Returns:
        str: The improved Python code.
    """
    template_str = (
        "Review the following Python test script for potential errors and areas for improvement. "
        "Return an updated version of the code that corrects any errors and incorporates enhancements, "
        "while preserving its original functionality. Do not include any markdown formatting (e.g., triple backticks); "
        "return plain executable Python code only. Additionally, insert clear inline comments that explicitly indicate where and what improvements have been made.\n\n"
        "Original Code:\n{generated_code}"
    )

    improved_code = run_chain(template_str, {"generated_code": generated_code}, escape_keys=["generated_code"])
    return improved_code


def main():
    try:
        # Step 1: Read scenario from file
        with open("./input/plaintext_scenarios.txt", "r") as f:
            scenario = f.read()

        # Step 2: Get the refined scenario from the preprocessing module.
        refined_scenario = get_refined_scenario(scenario)
        logger.debug("<<<Obtained refined scenario from preprocessing module.\n")

        # Step 3: Generate the test code based on the refined scenario.
        test_code = generate_test_code(refined_scenario)
        logger.debug("<<<Generated test code successfully.\n%s", test_code)

        # Step 4: Validate and improve the generated code.
        improved_test_code = validate_and_improve_code(test_code)
        logger.debug("<<<Validated and improved the generated test code.\n")

        # Step 5: Write the improved test code to a file.
        output_file = "./output/plaintext_generated_test_code.py"
        with open(output_file, "w") as f:
            f.write(improved_test_code)
        logger.info("Test code has been saved to %s", output_file)
    except Exception as e:
        logger.error("An error occurred: %s", e)


if __name__ == "__main__":
    main()
