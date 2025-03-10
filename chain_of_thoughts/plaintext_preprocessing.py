import logging
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
# Configure logging to show INFO-level messages and above
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

    # Invoke synchronously
    return sync_invoke()


def extract_globals(scenario: str) -> str:
    """
    Extracts all global variables (key-value pairs) from the scenario text in JSON or key-value format.

    Args:
        scenario (str): Raw scenario text.

    Returns:
        str: Extracted global variables.
    """
    template_str = (
        "Extract all the global variables from the following scenario text. "
        "Return only the key-value pairs in JSON format.\n\n"
        "Scenario:\n{scenario}"
    )
    logger.info("Extracting global variables from the scenario text...")
    result = run_chain(template_str, {"scenario": scenario}, escape_keys=["scenario"])
    return result


def extract_steps(scenario: str) -> str:
    """
    Extracts all test steps (including any provided test data) from the scenario text.
    The output should be a numbered list of steps.

    Args:
        scenario (str): Raw scenario text.

    Returns:
        str: Extracted test steps.
    """
    template_str = (
        "Extract all the test steps from the following scenario text.\n"
        "Test steps are delineated by 'StepX:' or similar formatting.\n"
        "Include any test data provided and combine them to form the test.\n"
        "Return the steps as a numbered list and ensure that all scenarios are covered.\n"
        "Scenario:\n{scenario}"
    )
    logger.info("Extracting test steps from the scenario text...")
    result = run_chain(template_str, {"scenario": scenario}, escape_keys=["scenario"])
    return result


def merge_globals_and_steps(globals_text: str, steps_text: str) -> str:
    """
    Merges the global variables and test steps into a single refined scenario.

    Args:
        globals_text (str): Extracted global variables.
        steps_text (str): Extracted test steps.

    Returns:
        str: Refined scenario.
    """
    template_str = (
        "Merge the following global variables and test steps into a single refined scenario. "
        "Integrate the global variables into the test steps where appropriate and provide detailed steps.\n\n"
        "Global Variables:\n{globals_text}\n\n"
        "Test Steps:\n{steps_text}"
    )
    logger.info("Merging global variables and test steps...")
    result = run_chain(template_str, {"globals_text": globals_text, "steps_text": steps_text})
    return result


def get_refined_scenario(scenario: str) -> str:
    """
    Processes the raw scenario text to extract global variables and test steps, then merges them
    into a refined scenario.

    Args:
        scenario (str): Raw scenario text.

    Returns:
        str: Refined scenario text.
    """
    try:
        logger.debug("<<<Reading Scenarios....(in-progress)")
        globals_text = extract_globals(scenario)
        logger.debug("Extracted Global Variables:\n%s", globals_text)
        steps_text = extract_steps(scenario)
        logger.debug("Extracted Test Steps:\n%s", steps_text)
        refined_scenario = merge_globals_and_steps(globals_text, steps_text)
        logger.debug("<<<Merged Refined Scenario:\n%s", refined_scenario)
        return refined_scenario
    except Exception as e:
        logger.error("An error occurred during scenario processing: %s", e)
        raise


def main():
    try:
        # Read the scenario from file
        with open("./input/plaintext_scenarios.txt", "r") as f:
            scenario = f.read()

        # Get the refined scenario by processing the raw scenario text
        refined_scenario = get_refined_scenario(scenario)
        print("Refined Scenario:")
        print(refined_scenario)
    except Exception as e:
        logger.error("An error occurred in main: %s", e)


if __name__ == "__main__":
    main()
