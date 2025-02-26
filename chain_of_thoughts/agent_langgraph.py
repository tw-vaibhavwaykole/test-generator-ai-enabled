#!/usr/bin/env python
# coding: utf-8

import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from IPython.display import Image, display
from typing import TypedDict, Annotated

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

# Initialize ChatOpenAI
chat_openai = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

# Define the overall agent state
class AgentState(TypedDict):
    plain_scenarios: Annotated[str, "Raw scenario input"]
    preprocessing_output: Annotated[str, "Refined scenario output"]
    code_generation_output: Annotated[str, "Improved test code output"]

# Import the compiled subgraphs
from preprocessing_subgraph import build_preprocessing_subgraph
from codegeneration_subgraph import build_code_generation_subgraph

# Build subgraphs
preprocessing_graph = build_preprocessing_subgraph()
code_generation_graph = build_code_generation_subgraph()

# Composite node wrappers
def preprocessing_composite_node(state: AgentState) -> dict:
    result = preprocessing_graph.invoke({"scenario": state["plain_scenarios"]})
    return {"preprocessing_output": result["preprocessing_output"]}

def code_generation_composite_node(state: AgentState) -> dict:
    result = code_generation_graph.invoke({"preprocessing_output": state["preprocessing_output"]})
    return {"code_generation_output": result["code_generation_output"]}

# Build the parent graph
parent_builder = StateGraph(AgentState, output=AgentState)
parent_builder.add_node("preprocessing", preprocessing_composite_node)
parent_builder.add_node("code_generation", code_generation_composite_node)
parent_builder.add_edge(START, "preprocessing")
parent_builder.add_edge("preprocessing", "code_generation")
parent_builder.add_edge("code_generation", END)
agent_graph = parent_builder.compile()

# Visualize the graph
display(Image(agent_graph.get_graph(xray=1).draw_mermaid_png()))

def run_graph():
    try:
        # Read the raw scenario
        with open("./input/plaintext_scenarios.txt", "r") as f:
            scenario = f.read()
        logger.info("Raw scenario loaded successfully.")

        # Initialize state
        initial_state: AgentState = {"plain_scenarios": scenario}

        # Invoke the graph
        final_state = agent_graph.invoke(initial_state)
        improved_code = final_state["code_generation_output"]
        logger.info("Graph completed processing.")

        # Save the output
        output_file = "./output/plaintext_generated_test_code.py"
        with open(output_file, "w") as f:
            f.write(improved_code)
        logger.info(f"Test code saved to {output_file}")

        # Display the result
        print("Improved Test Code:\n", improved_code)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    run_graph()