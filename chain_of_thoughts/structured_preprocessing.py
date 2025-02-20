import sys
import json
import yaml
import copy
import logging
from prance import ResolvingParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recursive_merge(default: dict, override: dict) -> dict:
    """
    Recursively merge two dictionaries.
    Values in override take precedence over default.
    If override is None, treat it as an empty dict.
    """
    if override is None:
        override = {}
    result = copy.deepcopy(default)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = recursive_merge(result[key], value)
        else:
            result[key] = value
    return result

def ensure_required_fields(merged_payload: dict, schema: dict) -> dict:
    """
    Ensure that all required fields in the schema are present in the merged_payload.
    For any required field missing, insert a placeholder value ("<value>").
    """
    required_fields = schema.get("required", [])
    for key in required_fields:
        if key not in merged_payload:
            logger.info(f"Inserting placeholder for missing required field: {key}")
            merged_payload[key] = "<value>"
    return merged_payload

def apply_global_overrides_to_payload(merged_payload: dict, global_overrides: dict, schema: dict) -> dict:
    """
    Update merged_payload by applying global variable overrides,
    but only for keys defined in the schema's properties.
    For any key in global_overrides that is missing or set to "<value>",
    update with the global value.
    """
    properties = schema.get("properties", {}) if schema else {}
    for key, value in global_overrides.items():
        if key in properties:
            if key not in merged_payload or merged_payload[key] == "<value>":
                logger.info(f"Applying global payload override for {key}: {value}")
                merged_payload[key] = value
    return merged_payload

def apply_global_overrides(merged_dict: dict, global_overrides: dict) -> dict:
    """
    Update merged_dict by applying global overrides.
    For any key in global_overrides that is missing or has a placeholder,
    update with the global value.
    """
    if global_overrides is None:
        global_overrides = {}
    for key, value in global_overrides.items():
        if key not in merged_dict or merged_dict[key] == "<value>":
            logger.info(f"Applying global override for {key}: {value}")
            merged_dict[key] = value
    return merged_dict

def extract_default_query_params(parameters: list) -> dict:
    """
    Extract default query parameters from the parameters list.
    If a query parameter has a default value in its schema, add it.
    """
    defaults = {}
    for param in parameters:
        if param.get("in") == "query":
            schema = param.get("schema", {})
            if "default" in schema:
                defaults[param["name"]] = schema["default"]
    return defaults

def load_yaml_file(file_path: str) -> dict:
    """Load a YAML file and return the parsed dictionary."""
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        logger.info(f"Loaded YAML file: {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {str(e)}")
        sys.exit(1)

def load_openapi_spec(spec_path: str) -> dict:
    """Load and resolve the OpenAPI spec using Prance."""
    try:
        parser = ResolvingParser(spec_path, lazy=True, strict=False)
        parser.parse()
        spec = parser.specification
        logger.info(f"Loaded and resolved OpenAPI spec: {spec_path}")
        return spec
    except Exception as e:
        logger.error(f"Error loading OpenAPI spec {spec_path}: {str(e)}")
        sys.exit(1)

def extract_base_url(spec: dict) -> str:
    """Extract base URL from the 'servers' section of the OpenAPI spec."""
    try:
        servers = spec.get("servers", [])
        if servers:
            base_url = servers[0].get("url", "")
            logger.info(f"Extracted base URL: {base_url}")
            return base_url
        else:
            logger.warning("No servers defined in the spec; base URL is empty.")
            return ""
    except Exception as e:
        logger.error(f"Error extracting base URL: {str(e)}")
        return ""

def get_endpoint_details(spec: dict, endpoint: str, method: str = "post") -> dict:
    """
    Given an endpoint path and HTTP method, extract the static details from the spec.
    """
    try:
        paths = spec.get("paths", {})
        endpoint_details = paths.get(endpoint)
        if not endpoint_details:
            raise ValueError(f"Endpoint {endpoint} not found in the spec.")
        method_details = endpoint_details.get(method.lower())
        if not method_details:
            raise ValueError(f"HTTP method {method.upper()} not found for endpoint {endpoint}.")
        return method_details
    except Exception as e:
        logger.error(f"Error extracting endpoint details for {endpoint}: {str(e)}")
        sys.exit(1)

def process_test_step(step: dict, spec: dict, global_base_url: str = "",
                      global_vars: dict = {}, global_headers: dict = {},
                      global_query_params: dict = {}, global_path_params_override: dict = {}) -> dict:
    """
    Process a single test step: merge static details from spec with dynamic overrides.
    Returns a dictionary representing the merged step.
    """
    # Extract static details for the given endpoint and method
    endpoint = step.get("endpoint")
    method = step.get("method", "POST")  # default to POST if not provided
    static_details = get_endpoint_details(spec, endpoint, method)

    # Get default base URL from spec if not overridden globally
    base_url = global_base_url if global_base_url else extract_base_url(spec)

    # Extract default headers from static details or use standard defaults
    default_headers = static_details.get("default_headers", {
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    # Extract request body schema for application/json content
    content = static_details.get("requestBody", {}).get("content", {}).get("application/json", {})
    schema = content.get("schema", {}) if content.get("schema") else {}
    default_payload = schema.get("default", {}) if schema else {}

    # Extract default query parameters from the parameters list
    parameters = static_details.get("parameters", [])
    default_query_params = extract_default_query_params(parameters)

    # Merge dynamic overrides provided by the user
    dynamic_path_params = step.get("path_params_override", {}) or {}
    dynamic_payload = step.get("payload_override", {}) or {}
    dynamic_headers = step.get("headers_override", {}) or {}
    dynamic_query_params = step.get("query_params_override", {}) or {}

    # Merge global path parameters override with step-specific dynamic path params
    merged_path_params = recursive_merge(global_path_params_override, dynamic_path_params)

    merged_payload = recursive_merge(default_payload, dynamic_payload)
    merged_payload = ensure_required_fields(merged_payload, schema)
    merged_payload = apply_global_overrides_to_payload(merged_payload, global_vars, schema)

    merged_headers = recursive_merge(default_headers, dynamic_headers)
    merged_headers = recursive_merge(merged_headers, global_headers)

    merged_query_params = recursive_merge(default_query_params, dynamic_query_params)
    merged_query_params = recursive_merge(merged_query_params, global_query_params)

    merged_step = {
        "service": step.get("service"),
        "endpoint": endpoint,
        "method": method.upper(),
        "static_details": {
            "base_url": base_url,
            "tags": static_details.get("tags", []),
            "summary": static_details.get("summary", ""),
            "description": static_details.get("description", ""),
            "operationId": static_details.get("operationId", ""),
            "parameters": parameters,
            "requestBody": static_details.get("requestBody", {}),
            "default_headers": default_headers,
            "responses": static_details.get("responses", {})
        },
        "dynamic_overrides": {
            "base_url": step.get("base_url_override", ""),
            "path_params": dynamic_path_params,
            "payload": dynamic_payload,
            "headers": dynamic_headers,
            "query_params": dynamic_query_params
        },
        "merged_path_params": merged_path_params,
        "merged_payload": merged_payload,
        "merged_headers": merged_headers,
        "merged_query_params": merged_query_params
    }
    return merged_step

def process_scenario(scenario: dict, spec: dict) -> dict:
    """
    Process the entire scenario by merging global overrides and each test step.
    """
    global_base_url = scenario.get("base_url_override", "") or extract_base_url(spec)
    global_vars = scenario.get("global_variables_override", {}) or {}
    global_headers = scenario.get("global_headers_override", {}) or {}
    global_query_params = scenario.get("global_query_parameters_override", {}) or {}
    global_path_params_override = scenario.get("global_path_params_override", {}) or {}

    final_output = {
        "base_url": global_base_url,
        "test_name": scenario.get("test_name"),
        "description": scenario.get("description"),
        "global_path_params_override": global_path_params_override,
        "global_variables_override": global_vars,
        "global_headers_override": global_headers,
        "global_query_parameters_override": global_query_params,
        "steps": []
    }

    for step in scenario.get("steps", []):
        merged_step = process_test_step(
            step, spec, global_base_url, global_vars, global_headers,
            global_query_params, global_path_params_override
        )
        if not merged_step["dynamic_overrides"].get("path_params"):
            merged_step["dynamic_overrides"]["path_params"] = global_path_params_override
        final_output["steps"].append(merged_step)

    return final_output

def main():
    # File paths (update these paths as necessary)
    scenario_file_path = "input/scenario_reduced.yaml"
    openapi_spec_path = "specs/dd_spec.yaml"
    output_file_path = "output/structured_preprocessing.json"

    # Load inputs
    scenario = load_yaml_file(scenario_file_path)
    openapi_spec = load_openapi_spec(openapi_spec_path)

    # Process the scenario and merge details with the OpenAPI spec
    final_json = process_scenario(scenario, openapi_spec)

    # Save the final merged JSON structure to a file with indentation
    with open(output_file_path, 'w') as outfile:
        json.dump(final_json, outfile, indent=2)

    print(f"Formatted JSON output has been saved to {output_file_path}")

    # Output the final merged JSON structure
    print(json.dumps(final_json, indent=2))

if __name__ == "__main__":
    main()
