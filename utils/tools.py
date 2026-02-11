from langchain_core.tools import tool
import streamlit as st
from utils.vector_store import get_vector_store


@st.cache_resource
def load_vector_stores():
    """Load and return all vector stores."""

    f_stores = get_vector_store(
        index_name="vector_db_index/cics_genapp_index_procedure_with_summary",
        load_from_disk=True
    )

    # c_stores = get_vector_store(
    #     index_name="vector_db_index/coreutils_index_comments",
    #     load_from_disk=True
    # )

    r_stores = get_vector_store(
        index_name="vector_db_index/cics_genapp_index_readme",
        load_from_disk=True
    )

    return {
        "main_store": f_stores,
        # "comment_store": c_stores,
        "readme_store": r_stores
    }

stores = load_vector_stores()
main_store = stores["main_store"]
# comment_store = stores["comment_store"]
readme_store = stores["readme_store"]

@tool
def search_concepts(query: str) -> str:
    """
    Useful for understanding the codebase.
    Searches user-defined documentation (READMEs).
    Use this to find explanations, behavior summaries, design notes defined in the documentation.
    """
    print(f"   [Concept Tool] Searching for: '{query}'...")
    
    # Retrieve top matches from both sources
    readmes = readme_store.similarity_search(query, k=3)
    # comments = comment_store.similarity_search(query, k=5)
    
    results = []
    results.append(f"### CONCEPTUAL SEARCH RESULTS FOR: '{query}' ###\n")

    # Format README results
    if readmes:
        results.append("--- SOURCE: PROJECT DOCUMENTATION (READMEs) ---")
        for doc in readmes:
            source = doc.metadata.get("file_name", "unknown_file")
            results.append(f"[{source}]: {doc.page_content}\n")
            
    if not readmes:
        return "No relevant documentation found."

    return "\n".join(results)


@tool
def search_cobol_logic(query: str) -> str:
    """
    Useful for finding BUSINESS LOGIC, PROCEDURES, and CONTROL FLOW.
    Use this to find specific paragraphs or sections of code.
    
    Auto-filters to only show 'PARAGRAPH' or 'SECTION' types.
    """
    print(f"   [Logic Tool] Searching for: '{query}'...")
    
    filter_dict = {"type": ["PARAGRAPH", "SECTION"]}
    
    # Search the MAIN store
    try:
        results = main_store.similarity_search(query, k=4, filter=filter_dict)
    except Exception as e:
        print(f"Error in search cobol logic: {e}")
        raw_results = main_store.similarity_search(query, k=10)
        results = [doc for doc in raw_results if doc.metadata.get("type") in ["PARAGRAPH", "SECTION"]][:4]

    if not results:
        return "No matching logic found."

    output = [f"### LOGIC SEARCH RESULTS FOR: '{query}' ###\n"]
    
    for doc in results:
        meta = doc.metadata
        
        # Extract fields from your procedure summary builder
        file_name = meta.get("file_name", "unknown")
        para_name = meta.get("div_name", "unknown")
        line_num = meta.get("line_number", "?")
        intent = meta.get("intent_raw", "N/A")
        raw_code = meta.get("original_code", "[CODE MISSING]")
        action = meta.get("action_raw", "N/A") 
        
        entry = (
            f"File: {file_name} (Line {line_num})\n"
            f"Type: {meta.get('type', 'PARAGRAPH')}: {para_name}\n"
            f"Intent: {intent}\n"
            f"Action: {action}\n"
            f"Code:\n{raw_code}\n"
            f"{'-'*40}\n"
        )
        output.append(entry)

    return "\n".join(output)

# --- Tool 3: Data Structure Search (Linkage/Layouts) ---
@tool
def search_cobol_data(query: str, target_type: str = "ALL") -> str:
    """
    Useful for finding DATA DEFINITIONS, RECORD LAYOUTS, and LINKAGE SECTIONS.
    
    Args:
        query: The search query (e.g. "Customer Record layout").
        target_type: 
            - "LINKAGE_SECTION": Search only Linkage Sections (Inputs/Outputs).
            - "DATA_LAYOUT": Search only Record Layouts.
            - "ALL": Search both.
    """
    print(f"   [Data Tool] Searching for: '{query}' (Filter: {target_type})...")
    
    # Construct Filter list based on request
    valid_types = []
    if target_type == "LINKAGE_SECTION":
        valid_types = ["LINKAGE_SECTION"]
    elif target_type == "DATA_LAYOUT":
        valid_types = ["DATA_LAYOUT"]
    else:
        valid_types = ["LINKAGE_SECTION", "DATA_LAYOUT"]
    
    raw_results = main_store.similarity_search(query, k=10)
    
    filtered_docs = [
        doc for doc in raw_results 
        if doc.metadata.get("type") in valid_types
    ][:4] # Return top 3 matches

    if not filtered_docs:
        return f"No data structures found for type '{target_type}'."

    output = [f"### DATA STRUCTURE RESULTS FOR: '{query}' ###\n"]

    for doc in filtered_docs:
        meta = doc.metadata
        
        # Extract fields from your data summarizer builder
        struct_name = meta.get("div_name")
        struct_type = meta.get("type", "Unknown")
        raw_code = meta.get("original_code", "[CODE MISSING]")
        description = doc.page_content
        
        entry = (
            f"Structure: {struct_name}\n"
            f"Type: {struct_type}\n"
            f"Summary: {description.splitlines()[0] if description else 'N/A'}\n"
            f"Definition:\n{raw_code}\n"
            f"{'-'*40}\n"
        )
        output.append(entry)

    return "\n".join(output)