# 🐧 GNU Coreutils AI Navigator

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/frontend-streamlit-red)
![LangGraph](https://img.shields.io/badge/orchestration-langgraph-orange)
![License](https://img.shields.io/badge/license-MIT-green)

**An autonomous AI agent for navigating, analyzing, and explaining the GNU Coreutils C codebase.**

The **Coreutils AI Navigator** is an agentic AI application. It leverages a **ReAct (Reason + Act)** workflow to trace function calls, inspect structs, and synthesize explanations for legacy system code.

---

## 🚀 Key Features

* **LLM used:** OpenAI GPT-OSS-20B (finetuned for code reasoning tasks).
* **Embedding model:** Hugging Face SentenceTransformer model (all-mpnet-base-v2).
* **Codebase:** GNU Coreutils C source code (over 500,000 lines of code).
* **Orchestration framework:** Langgraph and Langchain.
* **Monitoring:** Integrated with LangSmith for trace analysis, latency monitoring, and cost tracking.
* **Production Guardrails:**
    * **Topic Filtering:** Rejects unrelated queries (e.g., cooking recipes) before execution.
    * **Loop Protection:** Hard limits on reasoning steps to prevent infinite loops and cost overruns.
* **Resilient UI:** Streamlit interface with persistent thread memory and real-time thought process visualization.
* **Vector Database:** FAISS for efficient retrieval of relevant code snippets.
* **Providers:** Embedding models from Hugging Face & LLMs from Groq.

## Code Extraction and Storing in Vector DB

**python-tree-sitter** is used to parse the GNU Coreutils C codebase to extract functions. These extracted components are then stored in a FAISS vector database after generating embeddings using Hugging Face models. Query schema is defined in [./utils/query_schema.py].

### Struct Extraction:

```python
(struct_specifier
    name: (type_identifier)? @struct_name
    body: (field_declaration_list)
) @struct
```
- **Target Node:** struct_specifier
- **Captures:**
    - `@struct_name`: Name of the struct. The _?_ indicates this is optional (handles anonymous structs).
    - `@struct`: Captures the entire struct definition node, including the keyword `struct`, the name, and the body.

### Enum Extraction:

```python
(enum_specifier
    name: (type_identifier)? @enum_name
    body: (enumerator_list)
) @enum
```

- **Target Node:** enum_specifier
- **Captures:**
    - `@enum_name`: Name of the enum. The _?_ indicates this is optional (handles anonymous enums).
    - `@enum`: Captures the entire enum definition node, including the keyword `enum`, the name, and the body.

### Function Extraction:

```python
(function_definition
    declarator: [
        (function_declarator
           declarator: (identifier) @func_name)
        (pointer_declarator
           declarator: (function_declarator
               declarator: (identifier) @func_name))
    ]
    body: (compound_statement
        (expression_statement
            (call_expression
                function: (identifier) @called_func
            )
        )*
    )
) @func_body
```
- **Target Node:** function_definition
- **Declarator Logic:**
    - Used to capture function of both regular `int main(...)` and pointer function declarations `char *get_name(...)`.
- **Captures:**
    - `@func_name`: Name of the function being defined.
    - `@called_func`: Names of functions that are called within the body of the function.
    - `@func_body`: Captures the entire function definition node, including the return type, name, parameters, and body.

### Comment Extraction:

```python
(comment) @comments
```

- **Target Node:** comment
- **Captures:**
    - `@comments`: Captures all single-line and multi-line comments in the code.


## 🛠️ Architecture

The application is built on the **LangGraph** framework, utilizing a directed cyclic graph (DAG) to manage state.

![Langgraph Architecture](./imgs/graph.png)

- _START_: The entry point where the user's query initializes the state graph.
- _Agent_: The central reasoning engine (LLM) that analyzes the state and decides whether to call a tool or finish.
- _Tools_: The execution node that runs the retrieval functions and passes results back to the Agent.
- _Finalizer_: A safety node that forces a summary response if the Agent exceeds the maximum number of allowed loop steps (considered 5 in this case).
- _END_: The termination point where the workflow stops and returns the final answer to the application.

## Tools [./utils/tools.py]:

- **search_concepts**: It performs semantic similarity searches across high-level documentation (READMEs) and inline developer comments. It is best used for answering questions about software behavior, design philosophy, or error handling logic without needing to read raw C code. It retrieves most similar documents with respect to the query from the vector database storing READMEs[./vector_db_index/coreutils_index_readmes] and comments[./vector_db_index/coreutils_index_comments].

- **search_implementations**: It retrieves the actual source code definitions for C functions, structs, and enums. It is ideal for deep dives into specific implementations, understanding function interactions, and tracing data structures within the codebase. It retrieves most similar documents with respect to the query from the vector database storing functions, structs and enums [./vector_db_index/coreutils_index_functions_structs_enums].

## Installation and setup 

### Clone the repository
```bash
git clone https://github.com/dhruvroytalukdar/Coreutils-AI-navigator.git
cd Coreutils-AI-navigator
```

### Create and activate a virtual environment and install dependencies
```bash
uv init .
uv pip install -r pyproject.toml
```

### Secrets Setup
Create a `.env` file in the root directory and paste the contents.

### Run the Streamlit application
```bash
streamlit run reAct_agent.py
```
