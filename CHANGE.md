# Changelog

All notable changes to the **GNU Coreutils AI Navigator** project will be documented in this file.

### [0.9]
- Broken down `search_concepts` logic into two parts `search_cobol_logic` and `search_cobol_data`

### [0.8]
Used ANTLR parser in Java to parse COBOL code.
#### Problems
- The current parser is not able to parse copybooks and some files which are running code from a BMS file. (Possible Assembly)
#### Fix
- So for now skipping those file.

- Storing only the code segments in the vector database is not working properly because the user query will be in natural language and similarity search will not be able to match natural language with code.
#### Fix
- Using Ollama to generate summary for the code segment locally and then storing the contents in vector database.

### [0.7]
Tried to implement a parser for COBOL language in tree-sitter and tested over the cics-genapp repository.
#### Problems
- Tree-sitter is not able to parse non-COBOL commands like EXEC CICS/SQL


### [0.6]
#### Added
- Updated the README.md to reflect the latest features and architecture of the project.
- Added CHANGE.md to document the changelog of the project.

### [0.5]
#### Problems
- The agent was crashing when the API request limit was exceeded.
#### Added
- Added additional variables `terminate` and `terminate_message` to the agent state to handle API request limit exceedance gracefully. When the limit is exceeded, the agent sets `terminate` to `True` and provides a user-friendly message in `terminate_message`, allowing the UI to inform the user without crashing.

### [0.4]
#### Problems
- The agent was answering unrelated queries (e.g., cooking recipes) leading to wasted compute and poor user experience.
- There was a minor bug in the implementation of `finalize` node causing it to not return the final answer properly.

#### Added
- Did some prompt engineering to make the agent reject unrelated queries before execution by modifying the system prompt.
- I was updating the `loop_step` variable in the wrong place in the code. When max number of reasoning steps were exceeded the agent was moving to the finalize node but the `loop_step` variable was not being reset to `0` because I was returning
```json
{
    "messages": [],
    "loop_step": 0
}
```
I discovered state variables cannot be updated this way because I used a reducer `operator.add` on this variable. To fix this I removed the reducer (`operator.add`) and manually increment the `loop_step` variable in the agent state.

### [0.3]
#### Problems
- The agent was occasionally exceeding the context window due to large C files, leading to incomplete responses.
- The agent was forgetting previous interactions in long threads, causing loss of context.
- While using the LLM model `qwen-7b`, the model was involving in too many reasoning steps, leading to high latency and cost.

#### Added
- Implemented **Long Term Memory** where a list of recent interactions is stored and prepended to each new user query to provide immediate context.
- Added **loop_step** variable to agent state to keep track of the number of reasoning steps taken by the agent. If the number exceeds a predefined threshold (e.g., 5), the agent will terminate further reasoning, move to `finalize` node and provide the best possible answer based on the information gathered so far.
- Implemented UI using Streamlit.


### [0.2]
#### Problems
- Similarity search was returning only comments, ignoring functions and structs. Possible reason might be that comments are lot similar to the user queries compared to functions/structs.
#### Added
- Stored comments in a separate vectorstore.
- Stored functions, enums and structs in another vectorstore.
- Read and stored contents from markdown files in another vectorstore for better conceptual understanding of the codebase. 
- Wrote the initial structure of Agent using LangGraph.
    - Added `search_concepts` tool to search in comments vectorstore and readme vectorstore.
    - Added `search_implementations` tool to search in functions/structs/enums vectorstore.
    - Added `agent` node to reason and call the above tools.
    - Added `tools` node to execute the retrieval functions.


### [0.1]
#### Added
- Used python-tree-sitter to parse GNU Coreutils codebase and extract comments, functions, structs, and enums.
- Created FAISS vector database to store embeddings of extracted code components.
- Stored everything in a single vector DB index for initial prototyping.
