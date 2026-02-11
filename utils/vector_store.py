import os
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language


# --- Step 2: Initialize Embeddings ---
# We use the open-source 'all-MiniLM-L6-v2' model via Hugging Face
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def get_vector_store(captured_items: list = [], index_name: str = None, load_from_disk: bool = False) -> FAISS:

    if load_from_disk:
        print("Loading index from disk...")
        vector_store = FAISS.load_local(index_name, embeddings, allow_dangerous_deserialization=True)
        return vector_store

    docs = []
    for item in captured_items:
        content = item.get_content()
        metadata = item.get_metadata()
        doc = Document(page_content=content, metadata=metadata)
        docs.append(doc)
    
    print("Building index...")
    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(index_name)
    return vector_store


def get_vector_store_readme(
    repo_path: str,
    index_name: str = "vector_db_index/coreutils_index_readmes",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    load_from_disk: bool = False,
) -> List[Document]:
    """
    Scans the directory for README files, reads them, and splits them
    using Markdown-specific separators.
    """

    if load_from_disk:
        print("Loading index from disk...")
        vector_store = FAISS.load_local(index_name, embeddings, allow_dangerous_deserialization=True)
        return vector_store
    
    # 1. Initialize the Splitter
    # We use 'from_language' to load standard Markdown separators:
    # ["\n#{1,6} ", "```\n", "\n\n", "\n", " ", ""]
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=Language.MARKDOWN,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    documents = []

    # 2. Walk the directory tree
    for root, _, files in os.walk(repo_path):
        for file in files:
            # 3. Filter for README files
            # Coreutils has files like: README, README-hacking, README.md
            if "readme" in file.lower():
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        
                    # Skip empty files
                    if not content.strip():
                        continue

                    # 4. Split the content
                    # The splitter returns a list of strings
                    chunks = splitter.split_text(content)
                    
                    # 5. Wrap in Document objects with Metadata
                    for chunk in chunks:
                        doc = Document(
                            page_content=chunk,
                            metadata={
                                "source": file_path,
                                "file_name": file,
                                "type": "readme_documentation"
                            }
                        )
                        documents.append(doc)
                        
                except Exception as e:
                    print(f"Skipping {file_path}: {e}")

    vector_store = FAISS.from_documents(documents, embeddings)
    vector_store.save_local(index_name)
    return vector_store

def get_top_readme_docs(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        filter={"type": "readme_documentation"}
    )
    return results

def get_top_comments(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        filter={"document_type": "comment"}
    )
    return results

def get_top_functions(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        filter={"document_type": ["function_definition"]}
    )
    return results

def get_top_structs(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        filter={"document_type": "struct_definition"}
    )
    return results

def get_top_enums(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        filter={"document_type": "enum_definition"}
    )
    return results

def get_top_non_comments(vector_store: FAISS, query: str, k: int = 2, fetch_k: int = 10):
    results = vector_store.similarity_search(
        query,
        k=k,
        fetch_k=fetch_k,
        # filter={"document_type": ["function_definition", "struct_definition", "enum_definition"]}
    )
    return results
