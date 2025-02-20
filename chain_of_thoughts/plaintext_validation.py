import asyncio
import re
import yaml
import logging
import json
import jsonref  # New import for dereferencing schemas
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
chat_openai = ChatOpenAI(model="gpt-4o-mini")

def to_camel_case(s: str) -> str:
    """
    Converts an underscore-separated string to lowerCamelCase.
    For example:
      "CLIENT_CODE" -> "clientCode"
      "PROPERTY_CODE" -> "propertyCode"
      "correlation_id" -> "correlationId"
    """
    parts = s.split('_')
    return parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])

def convert_params_to_camel(endpoint: str) -> str:
    """
    Finds placeholders in the endpoint (anything in curly braces)
    and converts the parameter name to lowerCamelCase.
    """
    def replacer(match):
        param = match.group(1)
        return "{" + to_camel_case(param) + "}"
    return re.sub(r"\{([^}]+)\}", replacer, endpoint)

def load_openapi_spec(spec_path: str) -> dict:
    """
    Loads and parses the OpenAPI specification from a YAML file and dereferences all $ref pointers.

    Args:
        spec_path (str): Path to the OpenAPI YAML file.

    Returns:
        dict: Dereferenced OpenAPI spec.
    """
    with open(spec_path, "r") as f:
        spec = yaml.safe_load(f)
    # Convert to JSON string and then load with jsonref to dereference $ref
    spec = jsonref.loads(json.dumps(spec))
    return spec

def extract_relevant_spec_details(spec: dict, test_code: str) -> str:
    """
    Extracts only the parts of the OpenAPI spec that are relevant to a pre-defined list of endpoints.
    This function uses a static list of endpoints to search for in spec['paths'] and, for each endpoint,
    includes only the HTTP method specified in the static definition. If multiple static endpoints refer
    to the same path (with different HTTP methods), their details are merged.

    Args:
        spec (dict): The full OpenAPI spec.
        test_code (str): The generated test code (unused in this static approach).

    Returns:
        str: A YAML string with only the relevant parts of the spec.
    """
    static_endpoints = [
        "POST /api/v1/decisiondelivery/requests/{clientCode}/{propertyCode}",
        "POST /api/v1/decisiondelivery/dailybars/{clientCode}/{propertyCode}/{correlationId}",
        "PATCH /api/v1/decisiondelivery/requests/{clientCode}/{propertyCode}/{correlationId}",
        "GET /api/v1/decisiondelivery/requests/{clientCode}/{propertyCode}/{correlationId}"
    ]

    relevant = {}
    paths = spec.get("paths", {})

    for endpoint in static_endpoints:
        try:
            method, target_path = endpoint.split(" ", 1)
        except ValueError:
            continue
        method_lower = method.lower()
        # Look for an exact match of the target_path in the spec.
        if target_path in paths:
            details = paths[target_path]
            if method_lower in details:
                if target_path not in relevant:
                    relevant[target_path] = {}
                relevant[target_path][method_lower] = details[method_lower]
    return yaml.dump(relevant, sort_keys=False)

def print_token_usage(cb) -> None:
    """
    Prints the token usage details for an LLM call.

    Args:
        cb: The callback object containing token usage details.
    """
    logger.info("LLM token usage details:")
    logger.info("  Total Tokens: %s", cb.total_tokens)
    logger.info("  Prompt Tokens: %s", cb.prompt_tokens)
    logger.info("  Completion Tokens: %s", cb.completion_tokens)
    logger.info("  Total Cost (USD): $%.5f", cb.total_cost)

async def run_chain(template_str: str, input_vars: dict, escape_keys: list = None) -> str:
    """
    Runs a prompt chain with the given template and input variables.
    Optionally escapes curly braces for specified keys.

    Args:
        template_str (str): The prompt template string.
        input_vars (dict): Input variables for the prompt.
        escape_keys (list, optional): Keys whose values should have curly braces escaped.

    Returns:
        str: Generated content from the LLM.
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
            print_token_usage(cb)
        return result.content

    return await asyncio.to_thread(sync_invoke)

async def validate_test_code(generated_code: str, openapi_details: str) -> str:
    """
    Uses the LLM to review and update the generated test code based on the relevant OpenAPI details.
    If any mandatory payload fields, headers, or other required elements are missing, the updated code
    will include them along with inline comments explaining the changes referencing the OpenAPI spec.

    Args:
        generated_code (str): The original generated Python test script.
        openapi_details (str): The relevant OpenAPI spec details as a string.

    Returns:
        str: The improved Python test script.
    """
    template_str = (
        "Review the following Python test script against the provided OpenAPI specification details. "
        "The OpenAPI snippet includes only the relevant endpoints and required fields (such as mandatory payload properties, headers, and parameters) for validation. "
        "Your task is to update the test script by ensuring that any missing mandatory elements are included. "
        "This includes verifying that each API call contains all required headers as defined in the spec, and that the request bodies are correctly structured. "
        "If a mandatory element or header is missing, attempt to insert a default value based on the context provided in the OpenAPI snippet. "
        "If no explicit default value is specified, use your best possible guess to determine an appropriate value. "
        "For each modification, insert clear inline comments that reference the corresponding OpenAPI details and explain your reasoning behind the chosen value. "
        "Return the updated test script as plain executable Python code without any markdown formatting.\n\n"
        "OpenAPI Relevant Details:\n{openapi_details}\n\n"
        "Original Test Code:\n{generated_code}"
    )

    improved_code = await run_chain(template_str,
                                    {"openapi_details": openapi_details, "generated_code": generated_code},
                                    escape_keys=["openapi_details", "generated_code"])
    return improved_code

async def main():
    try:
        # Step 1: Load the previously generated test code.
        with open("./output/plaintext_generated_test_code.py", "r") as f:
            generated_code = f.read()
        logger.info("Loaded generated test code from file.")

        # Step 2: Load the OpenAPI spec.
        spec = load_openapi_spec("specs/dd_spec.yaml")
        logger.info("Loaded OpenAPI specification.")

        # Step 3: Extract only the relevant details from the spec based on the static endpoints.
        openapi_details = extract_relevant_spec_details(spec, generated_code)
        logger.debug("Extracted relevant OpenAPI details:\n%s", openapi_details)

        # Step 4: Validate and improve the test code using the extracted OpenAPI details.
        improved_code = await validate_test_code(generated_code, openapi_details)
        logger.info("Validated and improved the test code using OpenAPI reference.")

        # Step 5: Write the improved test code back to file.
        output_file = "./output/plaintext_validated_test_code.py"
        with open(output_file, "w") as f:
            f.write(improved_code)
        logger.info("Improved test code has been saved to %s", output_file)
    except Exception as e:
        logger.error("An error occurred during OpenAPI validation: %s", e)

if __name__ == "__main__":
    asyncio.run(main())
