from langgraph.graph import StateGraph, START, END
from plaintext_codegeneration import generate_test_code, validate_and_improve_code
from typing import TypedDict, Annotated

class CodeGenerationInternalState(TypedDict):
    preprocessing_output: str
    generated_code: str
    improved_code: str

class CodeGenerationOutputState(TypedDict):
    code_generation_output: Annotated[str, "Improved test code output"]

def generate_code_node(state: CodeGenerationInternalState) -> dict:
    return {"generated_code": generate_test_code(state["preprocessing_output"])}

def improve_code_node(state: CodeGenerationInternalState) -> dict:
    return {"improved_code": validate_and_improve_code(state["generated_code"])}

def final_output_node(state: CodeGenerationInternalState) -> CodeGenerationOutputState:
    return {"code_generation_output": state["improved_code"]}

def build_code_generation_subgraph() -> StateGraph:
    builder = StateGraph(CodeGenerationInternalState, output=CodeGenerationOutputState)
    builder.add_node("generate_code", generate_code_node)
    builder.add_node("improve_code", improve_code_node)
    builder.add_node("final_output", final_output_node)
    builder.add_edge(START, "generate_code")
    builder.add_edge("generate_code", "improve_code")
    builder.add_edge("improve_code", "final_output")
    builder.add_edge("final_output", END)
    return builder.compile()