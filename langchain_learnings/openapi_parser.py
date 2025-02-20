#!/usr/bin/env python3
"""
openapi_parser.py

A boilerplate OpenAPI (Swagger 2.0) specification parser that extracts a structured summary
of API details for subsequent processing (e.g. by an LLM to generate API Test Scenarios).

This version is updated to extract additional fields from the spec:
  - Extended API metadata (termsOfService, contact, license)
  - Global tags, security definitions, and external docs
  - Operation-level fields: tags, consumes, produces, and security

"""

import json
import yaml
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ValidationError, field_validator

# -----------------------------------------------------------------------------
# Configure logging
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Pydantic Models for OpenAPI Specification (Swagger 2.0)
# -----------------------------------------------------------------------------

class Contact(BaseModel):
    email: Optional[str] = None

class License(BaseModel):
    name: str
    url: Optional[str] = None

class Info(BaseModel):
    title: str
    version: str
    description: Optional[str] = None
    termsOfService: Optional[str] = None
    contact: Optional[Contact] = None
    license: Optional[License] = None

class Tag(BaseModel):
    name: str
    description: Optional[str] = None
    externalDocs: Optional[Dict[str, Any]] = None

class Parameter(BaseModel):
    name: str
    in_: str = Field(..., alias="in")
    description: Optional[str] = None
    required: Optional[bool] = False
    type: Optional[str] = None

class Response(BaseModel):
    description: str
    schema: Optional[Dict[str, Any]] = None  # capture schema if needed

class Operation(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    tags: Optional[List[str]] = None
    consumes: Optional[List[str]] = None
    produces: Optional[List[str]] = None
    security: Optional[List[Dict[str, List[str]]]] = None
    parameters: Optional[List[Parameter]] = []
    responses: Optional[Dict[str, Response]] = {}

    # Ensure response keys (typically status codes) are strings
    @field_validator("responses", mode="before")
    @classmethod
    def convert_response_keys_to_str(cls, value):
        if isinstance(value, dict):
            return {str(k): v for k, v in value.items()}
        return value

class APISpec(BaseModel):
    swagger: Optional[str] = None  #
    info: Info
    host: Optional[str] = None
    basePath: Optional[str] = None
    schemes: Optional[List[str]] = []
    tags: Optional[List[Tag]] = None
    paths: Dict[str, Dict[str, Operation]]
    securityDefinitions: Optional[Dict[str, Any]] = None
    definitions: Optional[Dict[str, Any]] = None
    externalDocs: Optional[Dict[str, Any]] = None

# -----------------------------------------------------------------------------
# Functions for Loading and Parsing the Specification
# -----------------------------------------------------------------------------

def load_api_spec(file_path: Path) -> APISpec:
    """
    Load and validate an OpenAPI specification from a YAML (or JSON) file.

    Args:
        file_path (Path): Path to the OpenAPI spec file.

    Returns:
        APISpec: A validated API specification object.

    Raises:
        FileNotFoundError: If the spec file does not exist.
        ValidationError: If the spec does not conform to the APISpec model.
    """
    logger.info(f"Loading API specification from {file_path}")
    if not file_path.exists():
        raise FileNotFoundError(f"Spec file {file_path} not found.")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            spec_dict = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error("Error loading YAML file", exc_info=True)
        raise e

    try:
        # Use model_validate per Pydantic V2 best practices
        api_spec = APISpec.model_validate(spec_dict)
    except ValidationError as ve:
        logger.error("Validation error in API specification", exc_info=True)
        raise ve

    logger.info("API specification loaded and validated successfully")
    return api_spec

def extract_api_details(api_spec: APISpec) -> Dict[str, Any]:
    """
    Extract key API details into a structured dictionary.

    The structure includes:
      - API metadata (title, version, description, termsOfService, contact, license)
      - Global tags (if available)
      - A list of endpoints, each with:
          - path, method, summary, description
          - tags, consumes, produces, security (if provided)
          - parameters (name, location, description, required, type)
          - responses (status_code and description)

    Args:
        api_spec (APISpec): The validated OpenAPI specification.

    Returns:
        Dict[str, Any]: A dictionary containing structured API information.
    """
    details = {
        "api_title": api_spec.info.title,
        "version": api_spec.info.version,
        "description": api_spec.info.description or "",
        "termsOfService": api_spec.info.termsOfService or "",
        "contact": api_spec.info.contact.dict() if api_spec.info.contact else {},
        "license": api_spec.info.license.dict() if api_spec.info.license else {},
        "host": api_spec.host or "",
        "basePath": api_spec.basePath or "",
        "schemes": api_spec.schemes or [],
        "global_tags": [tag.dict() for tag in api_spec.tags] if api_spec.tags else [],
        "endpoints": []
    }

    for path, methods in api_spec.paths.items():
        for method, operation in methods.items():
            endpoint_info = {
                "path": path,
                "method": method.upper(),
                "summary": operation.summary or "",
                "description": operation.description or "",
                "tags": operation.tags or [],
                "consumes": operation.consumes or [],
                "produces": operation.produces or [],
                "security": operation.security or [],
                "parameters": [],
                "responses": []
            }
            if operation.parameters:
                for param in operation.parameters:
                    endpoint_info["parameters"].append({
                        "name": param.name,
                        "in": param.in_,
                        "description": param.description or "",
                        "required": param.required,
                        "type": param.type or ""
                    })
            if operation.responses:
                for status_code, response in operation.responses.items():
                    endpoint_info["responses"].append({
                        "status_code": status_code,
                        "description": response.description
                    })
            details["endpoints"].append(endpoint_info)
    return details

def endpoints(api_spec: APISpec) -> List[Dict[str,Any]]:
    """
        Return a list of endpoints extracted from the API specification.

        Args:
            api_spec (APISpec): The validated API specification.

        Returns:
            List[Dict[str, Any]]: A list of endpoint dictionaries.
        """
    details = extract_api_details(api_spec)
    return details.get("endpoints", [])

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

def main():
    """
    Main function to load an OpenAPI specification and print the extracted API details.

    The extracted details are intended to be used as input for an LLM to generate API
    test scenarios in plain English.
    """
    # Update this path as needed
    spec_file_path = Path("spec/swagger_spec.yaml")  # Can be YAML or JSON
    try:
        api_spec = load_api_spec(spec_file_path)
        api_details = extract_api_details(api_spec)
        print("=== Structured API Details ===")
        print(json.dumps(api_details, indent=4))
    except Exception as e:
        logger.error("Failed to process the API specification", exc_info=True)

if __name__ == "__main__":
    main()
