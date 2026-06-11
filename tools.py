import os
from datetime import datetime
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import Tool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


def saveCodeToFile(codeContent: str) -> str:
    try:
        os.makedirs("ProjectOutput", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ProjectOutput/esp32_project_{timestamp}.ino"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(codeContent)

        return f"Successfully saved code to local workspace path: {filename}"
    
    except Exception as e:
        return f"Failed to save file due to error: {str(e)}"

save_tool = Tool(
    name="SaveCodeToFile",
    func=saveCodeToFile,
    description="Use this tool to save the final generated Arduino C++ code sketch to the local disk workspace."
)

ddgSearch = DuckDuckGoSearchRun()

search_tool = Tool(
    name="hardwareSearch",
    func=ddgSearch.run,
    description="Search the web for ESP32 pinouts, sensor datasheets, or library syntax definitions."
)

wiki_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=1000)
wiki_tool = WikipediaQueryRun(api_wrapper=wiki_wrapper)

