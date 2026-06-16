# FirmwareForge

An autonomous AI agent that helps you go from a plain-English idea to a working ESP32/Arduino firmware project. Describe what you want to build, and the agent researches the hardware, designs the wiring and failsafes, writes the code, and saves it to disk — all powered by Claude through the Anthropic API.

> A personal project exploring agentic AI architecture (LangChain + Claude) applied to embedded systems firmware generation.

---

## What It Does

You describe a hardware project in plain English:

```
Describe your hardware project:
Write code for an ESP32 Weather Station Web Server
```

From there, the agent works through the request on its own:

1. Researches the real hardware specs it needs — ESP32 pinouts, sensor I2C addresses, library syntax — using live web search and Wikipedia.
2. Designs the system: which components are needed, how they should be wired pin-by-pin, and a failsafe strategy for handling sensor or network failures without crashing.
3. Writes fully commented, compilable Arduino C++ code. Not boilerplate — actual project-specific firmware with real error handling (NaN checks, WiFi reconnect logic, sensor recovery loops).
4. Saves the finished `.ino` sketch to disk.
5. Validates its own final answer against a strict JSON schema before printing a structured summary: components, assembly steps, and Arduino IDE deployment instructions.

This isn't a fixed script that runs the same steps every time. The agent decides at each point whether it needs more research or is ready to write code, and calls its tools accordingly rather than following a hardcoded sequence.

---

## How It Works

```
═══════════════════════════════════════════
  SETUP PHASE (runs once, before any input)
═══════════════════════════════════════════

class ESP32CodeResponse(BaseModel)
app.py
Defines the required output shape: project_name,
components_needed, required_libraries, circuit_diagram_
explanation, assembly_steps, failsafe_strategy,
arduino_code, deployment_guide
        │
        ▼
parser = PydanticOutputParser(pydantic_object=ESP32CodeResponse)
app.py
Creates a parser that knows how to validate text
against the schema above, and can generate format
instructions describing that schema to the LLM
        │
        ▼
system_prompt = """..."""
app.py
Defines the agent's role (Senior Embedded Systems
Engineer), architectural rules (defensive programming,
no placeholder code), and the mandatory JSON-only
output format
        │
        ▼
promptTemplate = ChatPromptTemplate.from_messages([...])
app.py
Assembles the system_prompt, a {input} placeholder for
the user's request, and a MessagesPlaceholder for
agent_scratchpad (where tool call history goes) into
one reusable prompt structure
        │
        ▼
toolsList = [search_tool, wiki_tool, save_tool]
app.py — imported from tools.py
Gathers the three available tools into a single list
the agent can choose from
        │
        ▼
agentCore = create_tool_calling_agent(llm, toolsList, promptTemplate)
app.py
Binds the LLM, tools, and prompt template together
into an agent that knows how to reason about when
to call which tool
        │
        ▼
agent_executor = AgentExecutor(agent=agentCore, tools=toolsList, ...)
app.py
Wraps agentCore in a runtime loop that actually
executes tool calls, feeds results back to the LLM,
and repeats until the agent produces a final answer


═══════════════════════════════════════════
  EXECUTION PHASE (runs every time you ask)
═══════════════════════════════════════════

user_query = input("Describe your hardware project: ")
app.py
Captures the plain-English request, e.g.
"Write code for an ESP32 reading a DHT22 sensor"
        │
        ▼
formatted_input = {"input": user_query, "format_instructions": ...}
app.py
Packages the user's request together with the
schema instructions (from parser.get_format_instructions())
into the dict the prompt template expects
        │
        ▼
raw_result = agent_executor.invoke(formatted_input)
app.py
Kicks off the actual agent loop — this is where all
the tool-calling and reasoning below happens
        │
        ├──► hardwareSearch
        │    tools.py — search_tool
        │    DuckDuckGo web search (pinouts, datasheets, library docs)
        │
        ├──► wiki_tool
        │    tools.py — wiki_tool
        │    Wikipedia lookups for background concepts
        │
        └──► SaveCodeToFile
             tools.py — save_tool
             Writes the final .ino sketch to ProjectOutput/
        │
        ▼
output = raw_result["output"]
app.py
Extracts the agent's final text response (sometimes
a list of content blocks, flattened to one string)


═══════════════════════════════════════════
  VALIDATION + OUTPUT PHASE
═══════════════════════════════════════════

cleaned_output = extractJsonBlock(output)
app.py
Strips markdown fences and any stray lead-in sentence
the LLM added despite instructions not to
        │
        ▼
parsed_response = parser.parse(cleaned_output)
app.py
Validates the cleaned text against ESP32CodeResponse —
raises an error here if the JSON doesn't match the schema
        │
        ▼
print(f"PROJECT ARCHITECTURE: {parsed_response.project_name}") ...
app.py — __main__ block
Prints the structured summary: components, failsafe
strategy, assembly steps, and deployment guide
```

**Bug 1: stray text breaking JSON parsing.** Even with clear instructions not to, the model sometimes added a sentence before its JSON, like *"The code has been saved. Now compiling the final structured JSON response."* That extra text broke strict JSON parsing every time. Instead of endlessly tweaking the prompt to stop it, I added `extractJsonBlock()`, a small function that strips away anything outside the JSON itself, so the parser only ever sees the actual data.

**Bug 2: empty output when a tool call fails.** A different error showed up later: `Expecting value: line 1 column 1 (char 0)`. This one meant the parser received an empty string, not bad text. Looking at the logs, a Wikipedia search call had failed mid-run, and the agent stopped without ever producing a final answer. I added a quick check that catches this case and prints a clear message ("a tool call failed, try re-running") instead of that confusing error.

---

## Tech Stack

- Python 3
- LangChain (`langchain`, `langchain-core`, `langchain-classic`, `langchain-community`)
- Claude (Anthropic API) via `langchain-anthropic`
- Pydantic for structured output validation
- DuckDuckGo Search (`ddgs`) for live hardware research
- Wikipedia API for background reference lookups

---

## Project Structure

```
FirmwareForge/
├── app.py               # Agent pipeline, output schema, JSON cleanup, CLI entry point
├── tools.py              # Tool definitions: search, Wikipedia, file save
├── requirements.txt      # Python dependencies
├── .env                  # API key (not committed)
├── README.md             # This file
└── ProjectOutput/        # Generated .ino sketches (created automatically)
    ├── esp32_project_20260613_145552.ino
    └── esp32_project_20260616_213822.ino
```

---

## Setup & Installation

Clone the repository and move into the project folder:

```bash
git clone https://github.com/<your-username>/FirmwareForge.git
cd FirmwareForge
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_key_here
```

---

## Usage

Run the agent from the terminal:

```bash
python3 app.py
```

You'll be prompted to describe your project:

```
Describe your hardware project: Create a wind speed reader using an ESP32 and an anemometer
```

The agent researches, designs, and writes the firmware, prints a structured breakdown of the project, and saves the generated `.ino` file to `ProjectOutput/`.

---

## Example Output

```
(venv) seungwooshin@Seungwoos-MacBook-Pro ESP-AI-ARCHITECT % python3 app.py
=== ESP32 Firmware Architect Agent Initialized ===
Ask for any firmware project (e.g., 'Write code for an ESP32 reading a DHT22 sensor and save it')
Describe your hardware project:
Write code for an ESP32 Weather Station Web Server and save it
[System] Invoking autonomous agent execution pipeline...
> Entering new AgentExecutor chain...
```

The agent then researches pinouts and library syntax across several search calls, writes the full firmware, saves it to `ProjectOutput/`, and finishes with a structured summary like:

```
==================================================
PROJECT ARCHITECTURE: ESP32 BME280 Weather Station Web Server
==================================================

[Components Required]:
 ['ESP32 Development Board', 'BME280 Environmental Sensor Module', ...]

[Failsafe Strategy Implemented]:
 1. BME280 INIT FAILURE: If bme.begin() fails, the server still starts
    and broadcasts a sensor_error event while attempting recovery every
    10 seconds...
 2. WIFI DROPOUT: The main loop monitors connection state and triggers
    an automatic reconnect, rebooting cleanly if recovery fails...
```

---

## Known Limitations

- **Search reliability.** Web search runs through an unauthenticated DuckDuckGo backend, and I've seen occasional request timeouts during testing. A weak or unstable WiFi connection can also trigger this. There's no automatic retry yet — if a tool call fails mid-run, the script now raises a clear "agent returned an empty response" message instead of a cryptic JSON error, but the fix is still the same: re-run the script.
- **JSON parsing isn't bulletproof.** Final output reliability depends on the LLM correctly following the JSON-only formatting instructions in the system prompt. I added `extractJsonBlock()` to clean up stray text the model sometimes adds anyway, but this is a mitigation, not a guarantee — malformed output can still fail validation in rare cases.
- **One file per run.** A single `.ino` file is generated per request; multi-file projects (for example, a separate config header) aren't supported yet.
- **Runtime is a bit slow.** A full run can take a few minutes. This isn't a bottleneck in the code itself — it's the agent making multiple live web searches and Wikipedia lookups to ground its answer in real specs before writing anything.

---

## Acknowledgments

Built as a learning project to explore agentic AI architecture in a hardware and embedded-systems context. Implementation and debugging were assisted by Gemini and Claude — I designed the schema, the tool architecture, and the prompt strategy, and personally diagnosed and fixed the JSON-parsing failure described above.
