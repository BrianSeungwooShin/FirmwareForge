#IMPORTS
import re
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from tools import search_tool, wiki_tool, save_tool

load_dotenv()

#Defensive cleanup for LLM output.
#Strips markdown code fences if present, then extracts the outermost {...} JSON object even if the model added stray sentences before or after it (e.g. 'Here is the JSON:').

def extractJsonBlock(rawText: str) -> str:
    text = rawText.strip()
 
    # Strip ```json ... ``` or ``` ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
 
    # Find the first '{' and the matching last '}' in the string
    start = text.find("{")
    end = text.rfind("}")
 
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
 
    # Fallback: return as-is if no braces found (will fail parsing
    # with a clear error rather than silently returning garbage)
    return text

#DEFINING THE EXPECTED OUTPUT STRUCTURE FOR THE AGENT'S RESPONSE
class ESP32CodeResponse(BaseModel):
    project_name: str = Field(description = "The formal engineering name of the project")
    components_needed: list[str] = Field(description = "List of all hardware modules, resistors, and sensors required")
    required_libraries: list[str] = Field(description = "List of all Arduino IDE libraries needed to compile this sketch")
    circuit_diagram_explanation: str = Field(description = "Pin-by-pin mapping explanation of the hardware connections to the ESP32")
    assembly_steps: list[str] = Field(description = "A sequential, step-by-step instruction list for the user to safely build the hardware circuit")
    failsafe_strategy: str = Field(description = "Explanation of how the firmware handles hardware failure or disconnected sensors safely")
    arduino_code: str = Field(description = "The complete, fully commented Arduino C++ source code sketch (.ino format) with integrated exception handling/sensor check loops")
    deployment_guide: str = Field(description = "Step-by-step instructions for the user on how to configure the Arduino IDE, select the partition scheme, and upload the sketch to the ESP32 board")

#CREATING THE AI MODEL AND PARSER INSTANCES FOR THE AGENT
llm = ChatAnthropic(model = "claude-sonnet-4-6", temperature = 0.1)

parser = PydanticOutputParser(pydantic_object=ESP32CodeResponse)


#THE SYSTEM PROMPT DEFINES THE AGENT'S ROLE, TASK, AND CRITICAL ARCHITECTURAL RULES TO ENSURE THE OUTPUT IS SAFE, RELIABLE, AND PRODUCTION-GRADE. THE PROMPT TEMPLATE STRUCTURES THE CONVERSATION FLOW AND INCLUDES PLACEHOLDERS FOR TOOL INTERACTIONS AND FINAL RESPONSE FORMATTING.
system_prompt = """You are an expert Senior Embedded Systems Engineer and Firmware Architect specializing in ESP32 microcontrollers.
Your task is to analyze user requests and engineer highly reliable production-grade hardware systems.
 
CRITICAL ARCHITECTURAL RULES:
1. Always implement defensive programming. The 'arduino_code' field MUST check if sensor initializations fail and implement your stated failsafe strategy.
2. Never write placeholder comments (like '// add your code here'). Write fully realized, compilable C++ code.
 
FINAL OUTPUT FORMAT — THIS IS MANDATORY:
Your final message must contain ONLY a single JSON object and NOTHING else.
- Do NOT wrap it in markdown code fences (no ```json or ```).
- Do NOT include any explanation, summary, headers, tables, or commentary before or after the JSON.
- Do NOT include any lead-in sentence like "Here is the JSON" or "The code has been saved. Now compiling..." — go straight into the JSON object.
- Do NOT repeat the JSON in a different format afterward.
- The JSON must match this exact structure:
{format_instructions}"""

#BUILDING THE PROMPT TEMPLATE FOR THE AGENT, INCORPORATING THE SYSTEM PROMPT AND PLACEHOLDERS FOR USER INPUT AND TOOL INTERACTIONS
promptTemplate = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

#SETTING UP THE AGENT WITH THE LLM, TOOLS, AND PROMPT TEMPLATE. THE AGENT WILL BE ABLE TO CALL THE SEARCH AND WIKIPEDIA TOOLS AS NEEDED TO GATHER INFORMATION ABOUT ESP32 PINOUTS, SENSOR DATASHEETS, OR LIBRARY SYNTAX DEFINITIONS TO INFORM ITS CODE GENERATION. THE SAVE TOOL CAN BE CALLED TO SAVE THE FINAL GENERATED CODE TO A LOCAL FILE. THE AGENT EXECUTOR MANAGES THE INTERACTIONS AND EXECUTION FLOW.
toolsList = [search_tool, wiki_tool, save_tool]

agentCore = create_tool_calling_agent(llm, toolsList, promptTemplate)

agent_executor = AgentExecutor(
    agent=agentCore,
    tools=toolsList,
    verbose=True,
    handle_parsing_errors=True
)

#USER INTERACTION AND EXECUTION PIPELINE
if __name__ == "__main__":
    print("\n=== ESP32 Firmware Architect Agent Initialized ===")
    print("Ask for any firmware project (e.g., 'Write code for an ESP32 reading a DHT22 sensor and save it')\n")
    
    print("Describe your hardware project:")
    user_query = input()
    
    formatted_input = {
        "input": user_query,
        "format_instructions": parser.get_format_instructions()
    }
    
    try:
        print("\n[System] Invoking autonomous agent execution pipeline...\n")
        
        raw_result = agent_executor.invoke(formatted_input)
 
        output = raw_result["output"]
 
        if isinstance(output, list):
            text_pieces = []
            for block in output:
                if isinstance(block, dict):
                    text_pieces.append(block.get("text", ""))
            output = "".join(text_pieces)
 
        # If a tool call fails mid-run (e.g. a Wikipedia or search request
        # error), the agent can return an empty final response. Catch that
        # case here with a clear message instead of a cryptic JSON error.
        if not output.strip():
            raise ValueError(
                "Agent returned an empty response, likely because a tool call "
                "(search or wikipedia) failed mid-run and the agent never reached "
                "a final answer. Try re-running the script."
            )
 
        # Defensive cleanup: strip any stray prose/fences around the JSON
        # before handing it to the strict Pydantic parser.
        cleaned_output = extractJsonBlock(output)
        parsed_response = parser.parse(cleaned_output)
 
        print("\n" + "="*50)
        print(f"PROJECT ARCHITECTURE: {parsed_response.project_name}")
        print("="*50)
        print(f"\n[Components Required]:\n {parsed_response.components_needed}")
        print(f"\n[Failsafe Strategy Implemented]:\n {parsed_response.failsafe_strategy}")
        print(f"\n[Assembly Steps]:\n")
        for step in parsed_response.assembly_steps:
            print(f" - {step}")
        print(f"\n[Deployment Guidelines]:\n {parsed_response.deployment_guide}")
        print("\n" + "="*50)
        print("[System Execution Completed Successfully]")
        
    except Exception as e:
        print(f"\n[Fatal Error during parser validation]: {str(e)}")
