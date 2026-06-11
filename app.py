from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from tools import search_tool, wiki_tool, save_tool

load_dotenv()

class ESP32CodeResponse(BaseModel):
    project_name: str = Field(description = "The formal engineering name of the project")
    components_needed: list[str] = Field(description = "List of all hardware modules, resistors, and sensors required")
    required_libraries: list[str] = Field(description = "List of all Arduino IDE libraries needed to compile this sketch")
    circuit_diagram_explanation: str = Field(description = "Pin-by-pin mapping explanation of the hardware connections to the ESP32")
    assembly_steps: list[str] = Field(description = "A sequential, step-by-step instruction list for the user to safely build the hardware circuit")
    failsafe_strategy: str = Field(description = "Explanation of how the firmware handles hardware failure or disconnected sensors safely")
    arduino_code: str = Field(description = "The complete, fully commented Arduino C++ source code sketch (.ino format) with integrated exception handling/sensor check loops")
    deployment_guide: str = Field(description = "Step-by-step instructions for the user on how to configure the Arduino IDE, select the partition scheme, and upload the sketch to the ESP32 board")


llm = ChatAnthropic(model = "claude-sonnet-4-6", temperature = 0.1)

parser = PydanticOutputParser(pydantic_object=ESP32CodeResponse)

system_prompt = """You are an expert Senior Embedded Systems Engineer and Firmware Architect specializing in ESP32 microcontrollers.
Your task is to analyze user requests and engineer highly reliable production-grade hardware systems.

CRITICAL ARCHITECTURAL RULES:
1. Always implement defensive programming. The 'arduino_code' field MUST check if sensor initializations fail and implement your stated failsafe strategy.
2. Never write placeholder comments (like '// add your code here'). Write fully realized, compilable C++ code.
3. You MUST format your final response string strictly as a JSON instance that matches this structural blueprint layout:
{format_instructions}"""

promptTemplate = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

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
    
    user_query = input("Describe your hardware project: ")
    
    formatted_input = {
        "input": user_query,
        "format_instructions": parser.get_format_instructions()
    }
    
    try:
        print("\n[System] Invoking autonomous agent execution pipeline...\n")
        
        raw_result = agent_executor.invoke(formatted_input)

        output = raw_result["output"]
        if isinstance(output, list):
            output = "".join(
                block.get("text", "") for block in output if isinstance(block, dict)
            )

        parsed_response = parser.parse(output)

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