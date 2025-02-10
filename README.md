# API Test Scenario Generator

This project loads an OpenAPI specification, extracts API endpoints, and uses LangChain along with Pydantic to generate plain English test scenarios and test steps for each endpoint. The project provides both a command-line interface and a simple web UI built with Flask.

## Features

- **OpenAPI Parsing:** Validates and extracts API details using Pydantic models.
- **Scenario Generation:** Uses LangChain to produce natural language test scenarios.
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
   git clone <repository_url>
   cd ai-enabled-test-generator
   ```
2. **Install Dependencies and Create the Virtual Environment:**

```bash
pipenv install --dev
pipenv shell
```

3. **Running application**

```bash
python app.py
```


   
