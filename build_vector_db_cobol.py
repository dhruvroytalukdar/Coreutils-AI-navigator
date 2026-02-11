import json
from typing import List
import os
import ollama
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from tqdm import tqdm
from pydantic import BaseModel, Field

# --- 1. DEFINE STRICT SCHEMA (The Pydantic Class) ---
class CobolSummary(BaseModel):
    """
    A structured representation of a COBOL code segment's logic, designed to bridge the 
    semantic gap between business queries and legacy syntax for vector retrieval.

    This model enforces a strict schema for LLM extraction, ensuring that every 
    code segment is broken down into three distinct semantic layers:
    1. Intent (Why this code exists).
    2. Action (What the code technically does).
    3. Expansion (Synonyms for better search hits).

    Attributes:
        business_intent (str): A concise, high-level explanation of the business rule 
            or logic being applied (e.g., "Calculates monthly policy premium"). 
            It abstracts away variable names and syntax to focus on the 'Why'.
            
        technical_action (str): A description of the specific technical operation 
            performed (e.g., "DB2 Select Statement", "CICS Send Map", "VSAM Write"). 
            Useful for filtering search results by technology type.
            
        keywords (List[str]): A list of 5-8 domain-specific search terms, synonyms, 
            or concepts (e.g., ["Error Handling", "SQLCODE", "Validation"]). 
            These act as 'synonym expansion' to help the vector database match 
            user queries that might use different vocabulary than the raw code.
    """
    business_intent: str = Field(
        description="A concise, 2-3-sentence explanation of the BUSINESS rule being applied (e.g., 'Validates customer date of birth'). Avoid mentioning variable names."
    )
    technical_action: str = Field(
        description="The specific technical operation. (e.g., 'DB2 Select Statement', 'CICS Send Map', 'File Write')."
    )
    keywords: List[str] = Field( 
        description="A list of 5-8 relevant search terms, synonyms, or concepts for retrieval (e.g., 'Error Handling', 'SQLCODE', 'Validation')."
    )

class DataStructureSummary(BaseModel):
    """
    A structured semantic representation of a COBOL Data Division element, used to 
    map technical data layouts to their business purpose.

    This model captures the 'what' and 'why' of a data structure, abstracting away 
    complex hierarchy (like 05/10 levels) into a searchable summary. It is specifically 
    designed to facilitate vector retrieval of data definitions (e.g., "Find the 
    customer policy record").

    Attributes:
        structure_name (str): The exact identifier of the root record or section from the 
            COBOL source (e.g., 'CUSTOMER-RECORD', 'LINKAGE SECTION', 'LGCMAREA').
            
        description (str): A high-level, natural language explanation of the business 
            entity or logical grouping this structure represents. It should describe 
            the *content* rather than just the syntax.
            
        key_fields (List[str]): A curated list of significant field names contained 
            within the structure. This acts as a 'keyword index' for the structure, 
            prioritizing business-relevant fields (e.g., 'POLICY-ID') over technical 
            fillers (e.g., 'FILLER', 'WS-rsv').
    """
    structure_name: str = Field(
        ...,
        description="The name of the root record or section (e.g., 'CUSTOMER-RECORD' or 'LINKAGE SECTION')."
    )
    description: str = Field(
        ...,
        description="A concise, 1-sentence explanation of what this data represents (e.g., 'Holds insurance policy details including ID and type')."
    )
    key_fields: List[str] = Field(
        ...,
        description="Extract 5-10 critical field names (business relevant) found inside this structure (e.g., ['POLICY-ID', 'EXP-DATE']). Ignore filler fields."
    )

# --- CONFIGURATION ---
JSON_SOURCE = "cobol_segments.json"
DB_PATH = "cics_genapp_index_procedure_with_summary"
OLLAMA_MODEL = "llama3"

# --- 1. THE SUMMARIZER ---
def generate_summary_with_ollama(code_content):
    """
    Sends COBOL code to local Ollama instance and gets a plain English summary.
    """
    prompt = f"""
    You are a Mainframe Modernization Architect. Your goal is to generate a search-optimized summary for the following COBOL code segment.
    
    Analyze the provided COBOL code segment. 
    Extract the business intent, technical action, and search specific keywords.
    
    Rules:
    1. Do not simply describe the syntax (e.g., avoid "Moves A to B").
    2. Identify specific CICS commands (SEND MAP, LINK) or SQL operations (SELECT, UPDATE).
    3. If the code handles errors (SQLCODE != 0), explicitly mention "Error Handling".
    4. Keep the "business_intent" explanative (2-3 sentences).
    
    COBOL CODE:
    {code_content}
    
    
    SUMMARY:
    """

    try:
        # We tell Ollama to force JSON mode if possible, or just parse the text
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            format=CobolSummary.model_json_schema() 
        )
        summary_content = CobolSummary.model_validate_json(response['message']['content'])
        return summary_content
    except Exception as e:
        print(f"Ollama Error: {e}")
        return CobolSummary(
            business_intent="Legacy COBOL Logic",
            technical_action="Unknown Operation",
            keywords=["COBOL", "Legacy"]
        )

def generate_data_summary(structure_name: str, cobol_code: str) -> DataStructureSummary:
    """
    Sends COBOL Data Division code to Ollama to understand WHAT data is being stored.
    """
    
    prompt = f"""
    You are a Data Architect analyzing legacy COBOL systems.
    Analyze the following COBOL Data Structure (Data Layout or Linkage Section).
    
    Your GOAL:
    Extract name of the data layout or linkage section, understand and summarize 2-3 line description about the section and extract important keywords from the section.
    
    COBOL CODE:
    {cobol_code}
    """

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            format=DataStructureSummary.model_json_schema() # Enforce strict schema
        )
        
        return DataStructureSummary.model_validate_json(response['message']['content'])

    except Exception as e:
        print(f"Error processing {structure_name}: {e}")
        # Fallback
        return DataStructureSummary(
            structure_name=structure_name,
            description="Legacy data structure.",
            key_fields=[]
        )


def build_database():
    if not os.path.exists(JSON_SOURCE):
        print(f"Error: {JSON_SOURCE} not found. Run the Java extractor first.")
        return

    # Load data extracted by Java
    with open(JSON_SOURCE, "r") as f:
        data = json.load(f)

    data_with_summary = []
    documents = []
    print(f"Processing {len(data)} segments with {OLLAMA_MODEL}...")

    # Initialize Embedding Model (Runs locally)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    for item in tqdm(data):
        doc = {}
        data_item = item.copy()
        if "LINKAGE_SECTION" in item["type"] or "DATA_LAYOUT" in item["type"]:
            summary = generate_data_summary(item['name'], item['content'])
        
            # Create the "Text Template" for Vector Search
            # This string is what you will embed into FAISS/Chroma
            vector_text = (
                f"Below is a \"{item['name']}\" in the file \"{item['fileName']}\"\n"
                f"Structure: {summary.structure_name}\n"
                f"Description: {summary.description}\n"
                f"Fields: {', '.join(summary.key_fields)}"
            )
            doc = Document(
                page_content=vector_text,
                metadata={
                    "original_code": item['content'],
                    "file_name": item["fileName"],
                    "div_name": item["name"],
                    "type": item["type"]
                }
            )
            data_item["summary"] = vector_text
        else:
            raw_code = item["content"]

            # Optimization: Skip tiny/useless paragraphs (e.g., just "EXIT.")
            if len(raw_code.split('\n')) < 3 and "EXIT" in raw_code:
                continue

            # A. Generate the Summary (This takes time!)
            summary = generate_summary_with_ollama(raw_code)

            vector_search_text = (
                f"The below code segment is a \"{item['type']}\" named \"{item['name']}\" which is in the file \"{item['fileName']}\" at line number \"{item['lineNumber']}\"\n"
                f"Business Intent: {summary.business_intent}\n"
                f"Technical Action: {summary.technical_action}\n"
                f"Keywords: {', '.join(summary.keywords)}"
            )

            doc = Document(
                page_content=vector_search_text,
                metadata={
                    "file_name": item["fileName"],
                    "div_name": item["name"],
                    "type": item["type"],
                    "line_number": item["lineNumber"],
                    "original_code": raw_code,
                    "intent_raw": summary.business_intent,
                    "action_raw": summary.technical_action
                }
            )
            data_item["summary"] = vector_search_text
        documents.append(doc)
        data_with_summary.append(data_item)

    # D. Save to FAISS
    if documents:
        print(f"Embedding {len(documents)} documents into FAISS...")
        vector_db = FAISS.from_documents(documents, embeddings)
        vector_db.save_local(DB_PATH)
        print(f"Success! Database saved to '{DB_PATH}'")
    else:
        print("No documents were processed.")

    with open("cobol_segments_summary.json", "w") as outfile:
        json.dump(data_with_summary, outfile)
        

if __name__ == "__main__":
    build_database()