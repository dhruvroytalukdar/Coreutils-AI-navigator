from langchain_core.tools import tool
import streamlit as st
from utils.vector_store import get_vector_store


@st.cache_resource
def load_vector_stores():
    """Load and return all vector stores."""

    f_stores = get_vector_store(
        index_name="vector_db_index/coreutils_index_functions_structs_enums",
        load_from_disk=True
    )

    c_stores = get_vector_store(
        index_name="vector_db_index/coreutils_index_comments",
        load_from_disk=True
    )

    r_stores = get_vector_store(
        index_name="vector_db_index/coreutils_index_readmes",
        load_from_disk=True
    )

    return {
        "function_store": f_stores,
        "comment_store": c_stores,
        "readme_store": r_stores
    }

stores = load_vector_stores()
function_store = stores["function_store"]
comment_store = stores["comment_store"]
readme_store = stores["readme_store"]

# --- 2. Tool A: The "Concept" Search (Readme + Comments) ---

@tool
def search_concepts(query: str) -> str:
    """
    Useful for understanding WHAT the code does. 
    Searches high-level documentation (READMEs) and developer comments.
    Use this to find explanations, behavior summaries, or design notes.
    """
    print(f"   [Concept Tool] Searching for: '{query}'...")
    
    # Retrieve top matches from both sources
    readmes = readme_store.similarity_search(query, k=2)
    comments = comment_store.similarity_search(query, k=5)
    
    results = []
    results.append(f"### CONCEPTUAL SEARCH RESULTS FOR: '{query}' ###\n")

    # Format README results
    if readmes:
        results.append("--- SOURCE: PROJECT DOCUMENTATION (READMEs) ---")
        for doc in readmes:
            source = doc.metadata.get("file_name", "unknown_file")
            results.append(f"[{source}]: {doc.page_content}\n")

    # Format Comment results
    if comments:
        results.append("--- SOURCE: DEVELOPER COMMENTS ---")
        for doc in comments:
            source = doc.metadata.get("file", "unknown_file")
            results.append(f"[{source}]: {doc.page_content}\n")
            
    if not readmes and not comments:
        return "No relevant documentation or comments found."

    return "\n".join(results)


# --- 3. Tool B: The "Implementation" Search (Functions + Call Graph) ---

@tool
def search_implementations(query: str) -> str:
    """
    Useful for understanding HOW the code works.
    Searches for actual C function definitions, structs, and enums.
    Returns the requested code along with metadata in the following format:
    Type: function_definition/struct_definition/enum_definition
    Name: <name>
    File: <file_name>
    Calls functions: [<called_function_1>, <called_function_2>, ...]
    Comment: <developer_comment>
    Code: <code_body>
    """
    print(f"   [Code Tool] Searching for: '{query}'...")
    
    # Retrieve top matches from function store
    functions = function_store.similarity_search(query, k=3)
    
    results = []
    results.append(f"### CODE IMPLEMENTATION RESULTS FOR: '{query}' ###\n")

    if not functions:
        return "No matching functions or structs found."

    for doc in functions:
        meta = doc.metadata
        name = meta.get("function_name", "unknown_symbol")
        file = meta.get("file_name", "unknown_file")
        type_ = meta.get("document_type", "unknown_file")
        function_comment = meta.get("function_comment", "No comment available.")

        # --- KEY FEATURE: EXPOSING YOUR CALL LIST METADATA ---
        # Since you stored 'calls' in metadata, we format it here for the Agent.
        # This allows the Agent to see "Relationships" without a graph database.
        calls_list = meta.get("called_functions", []) # Expecting a list of strings
        if isinstance(calls_list, str):    # Handle if stored as string representation
             calls_list = calls_list.replace("[", "").replace("]", "").replace("'", "")
        
        calls_str = str(calls_list) if calls_list else "None"

        entry = (
            f"Type: {type_}\n"
            f"Name: {name}\n"
            f"File: {file}\n"
            f"Calls functions: {calls_str}\n" # <--- The Agent sees the graph here
            f"Comment: {function_comment}\n"
            f"Code:\n{doc.page_content}\n"
            f"{'-'*40}\n"
        )
        results.append(entry)

    return "\n".join(results)