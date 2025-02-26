#!/usr/bin/env python
# coding: utf-8

# In[31]:


# %%capture --no-stderr
# %pip install --quiet -U langchain_openai langchain_core langgraph


# In[32]:


import os, getpass

def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")

_set_env("OPENAI_API_KEY")
    


# In[33]:


# Import your preprocessing and code generation functions.
from plaintext_preprocessing import get_refined_scenario
from plaintext_codegeneration import generate_test_code, validate_and_improve_code


# In[34]:


_set_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "AI Test Generator"


# In[35]:


# import nest_asyncio
# nest_asyncio.apply()
import os
import logging
# import asyncio
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_core.tools import tool


# In[36]:


# Load environment variables (make sure your API keys are set in your .env file)
load_dotenv()

# Configure logging to display INFO-level messages.
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize the LLM (using GPT-4o-mini as an example)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


# In[42]:


# %% [code]
# Define a tool to preprocess the raw scenario text.
@tool
def preprocess_scenario(scenario: str) -> str:
    """
    Preprocess the raw scenario text to extract and merge global variables and test steps,
    returning a refined scenario.
    """
    try:
        refined = get_refined_scenario(scenario)
        return refined
    except Exception as e:
        return f"Error during preprocessing: {e}"
    
# Define a tool to generate test code based on the refined scenario.
@tool
def generate_test(scenario: str) -> str:
    """
    Generate a Python test script (using pytest and requests) based on the refined scenario.
    """
    try:
        code = generate_test_code(scenario)
        return code
    except Exception as e:
        return f"Error during code generation: {e}"

# Define a tool to validate and improve the generated test code.
@tool
def validate_test(generated_code: str) -> str:
    """
    Validate and improve the generated Python test code, returning an updated version.
    """
    try:
        improved = validate_and_improve_code(generated_code)
        return improved
    except Exception as e:
        return f"Error during code validation: {e}"    


# In[43]:


# %% [code]
# List all custom tools. The agent will see their names and descriptions.
tools = [ generate_test, validate_test,preprocess_scenario]

# Pull a ReAct prompt template from the LangChain Hub.
# This template instructs the agent to alternate between reasoning and acting.
prompt = hub.pull("hwchase17/react")

# Create the ReAct agent using the LLM, tools, and prompt.
agent = create_react_agent(llm, tools, prompt)

# Instantiate an AgentExecutor to run the agent with verbose output.
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


# In[44]:


raw_scenario = """
# Scenario: Test Decision Delivery flow

baseurl = "https://decision-delivery-internal.stage.ideasrms.com"
clientCode = "client1234"
propertyCode = "property123"

Step1:
  - Create a decision delivery POST request with endpoint /api/v1/decisiondelivery/requests/{clientCode}/{propertyCode}.
    Payload is: {
      "decisionUploadType": "FULL",
      "decisionType": "Approval",
      "clientEnvironmentUrl": "https://abc.com"
    }
  - Get the response and verify that the status is 200.
  - Store the correlation id from the response (e.g., response.content.get("correlationId")).

Step2:
  - Post daily bars using endpoint POST /api/v1/decisiondelivery/dailybars/${clientCode}/${propertyCode}/${correlationId}
    Payload is: {
           [{
              "occupancyDate": "2020-11-20",
              "rateCode": "BAR",
              "currencyCode": "USD",
              "roomTypeCode": "NSK",
              "singleRate": 100,
              "doubleRate": 120,
              "additionalAdultRate": 30,
              "additionalChildRate": 30,
              "taxExcluded": true
           }, {
              "occupancyDate": "2020-11-21",
              "rateCode": "BAR",
              "currencyCode": "USD",
              "roomTypeCode": "NSK",
              "singleRate": 100,
              "doubleRate": 120,
              "additionalAdultRate": 30,
              "additionalChildRate": 30,
              "taxExcluded": true
           }]
        }
   - Verify the status response to 200.

Step3:
  - PATCH the decision delivery request using endpoint '/api/v1/decisiondelivery/requests/${clientCode}/${propCode}/${correlationId}'
  - Verify the status as 204.

Step4:
  - GET the decision delivery status using endpoint '/api/v1/decisiondelivery/requests/${clientCode}/${propCode}/${correlationId}'
  - Fetch the requestStatus from the response json and print the status.
"""


# In[46]:


if __name__ == "__main__":
   response = agent_executor.invoke({"input": raw_scenario})
   print("code generated.. refer the output above")


# In[ ]:




