# API Test Scenario Generator

This project loads an OpenAPI specification, extracts API endpoints, and uses LangChain along with Pydantic to generate
plain English test scenarios and test steps for each endpoint. The project provides both a command-line interface and a
simple web UI built with Flask.

## Features

- **OpenAPI Parsing:** Validates and extracts API details using Pydantic models.
- **Scenario Generation:** Uses LangChain to produce natural language test scenarios.
- **Automated Test Generation**: Generates automation api test scripts in Python for the generated scenarios.
- **Web UI:** A Flask-based interface for uploading API specs and viewing generated scenarios.
- **Dependency Management:** Uses Pipenv to lock dependencies.

## Requirements

- Python 3.8 or higher
- [Pipenv](https://pipenv.pypa.io/en/latest/) (optional) or a virtual environment created with `venv`
- The dependencies are listed in both `Pipfile` and `requirements.txt`.

## Setup

### Using Pipenv

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/tw-vaibhavwaykole/test-generator-ai-enabled.git 
   cd ai-enabled-test-generator
   ```
2. **Create Python3 Virtual Environment and Install Dependencies**

```bash
   # Install Virtual environment
   python3 -m venv venv
 
   # Activate the Virtual environment
   source venv/bin/activate
   
   # Install pipenv
   pip install pipenv
   
   # Install dependencies from pipfile   
   pipenv install --dev
   
  # Activate the pipenv shell
   pipenv shell
   
  # To deactivate the virtual environment
   deactivate   
   ```

3. **Add .env file in root directory**

```bash

#This file is added to .gitignore to prevent sensitive information from being pushed to the repository.
# Add the following environment variables to the .env file
OPENAPI_KEY=your_openai_key

```

4.**Running application**

```bash
# Run the web application to generate scenarios
 python app.py

# Run the command line interface to generate scenarios and testcases
 python generate_testcases.py 
```
