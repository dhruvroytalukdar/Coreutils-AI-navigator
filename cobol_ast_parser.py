import os
from tree_sitter_language_pack import get_language, get_parser
from tree_sitter import Language, Parser
from utils.models import Captured_Paragraph, Captured_Procedure
from utils.vector_store import get_vector_store, get_vector_store_readme
import tree_sitter_cobol as ts_cobol

COBOL_LANGUAGE = Language(ts_cobol.language(), 'cobol')
parser = Parser(COBOL_LANGUAGE)

code = b"""
       IDENTIFICATION DIVISION.
       PROGRAM-ID. TEST.
       PROCEDURE DIVISION.
           EXEC CICS READ FILE('A') END-EXEC.
           DISPLAY "Hello World".
           STOP RUN.
"""

tree = parser.parse(code)
print(tree.root_node)

# cobol_lang = get_language('cobol')
# parser = get_parser('cobol')
# query_paragraph_section = """
#     (procedure_division) @proc_div
#     (ERROR) @error_node
#     """
# query_paragraph_header = Query(cobol_lang, query_paragraph_section)


# def read_cobol_code_from_file(file_path: str) -> bytes:
#     """
#     Read COBOL code from a file.
    
#     Args:
#         file_path: Path to the COBOL source file
#     Returns:
#         bytes: COBOL source code as bytes
#     """
#     with open(file_path, 'rb') as file:
#         return file.read()

# def parse_cobol_code(code: bytes):
#     """
#     The function parses COBOL code and returns the corresponding AST.
    
#     Args:
#         code: COBOL source code as bytes
#     Returns:
#         tree_sitter.Tree: The parsed syntax tree
#     """
#     # Parse the code
#     return parser.parse(code)

# def extract_procedure_division_from_ast(code: bytes, file_name: str) -> list:
#     ast = parser.parse(code)
#     cursor = QueryCursor(query_paragraph_header)
#     proc_nodes = cursor.matches(ast.root_node)
#     node_list = []
#     error_node = None
#     for proc in proc_nodes:
#         if proc[0] == 0:
#             # procedure_div node
#             node = proc[1]["proc_div"]
#         if proc[0] == 1:
#             # error_node
#             error_node = proc[1]["error_node"]
#             if error_node:
#                 print("Error node found")
#                 return None
#     if not node:
#         print("No procedure division found")
#         return None
#     proc_div_statements = "\n".join([node[0].text.decode("utf-8") for node in node_list])
#     captured_procedure = Captured_Procedure(file_name, proc_div_statements)
#     return captured_procedure

# def extract_paragraphs_from_ast(node) -> list:
#     """
#     Extract paragraph names from the AST root node.
    
#     Args:
#         root_node: The root AST node
#     Returns:
#         list: List of paragraph names
#     """

#     node = node["paragraph_name"]
#     paragraph_statements = []

#     paragraph_statements.append(node[0].text.decode("utf-8"))
#     next_node = node[0].next_named_sibling
#     # prev_node = node[0].prev_named_sibling
    
#     # Scan all statements in the paragraph
#     while next_node:
#         if next_node.type == "exit_statement":
#             paragraph_statements.append(next_node.text.decode("utf-8"))
#             break
#         if next_node.type in ['paragraph_header', 'section_header']:
#             break
#         paragraph_statements.append(next_node.text.decode("utf-8"))
#         next_node = next_node.next_named_sibling

#     # BUG IN THE PACKAGE COMMENTS STARTING FROM 7TH COLUMN ARE CAPTURED BUT WITHOUT ANY TEXT
#     # comment_for_paragraph = []

#     # Scan backwards for comments
#     # while prev_node:
#     #     if prev_node.type != "comment":
#     #         break
#     #     print(prev_node.text)
#     #     comment_for_paragraph.append(prev_node.text.decode("utf-8"))
#     #     prev_node = prev_node.prev_named_sibling
    
#     # if there is a comment for the paragraph, add it to the start of statements also reverse
#     # because we scanned backwards
#     # if len(comment_for_paragraph) > 0:
#     #     paragraph_statements = comment_for_paragraph[::-1] + paragraph_statements
    
#     return paragraph_statements


# def scan_for_paragraph(source_code: bytes, file_name: str = "test.cob") -> list[Captured_Paragraph]:
#     """
#     Recursively scan the AST to extract a paragraph.
#     Args:
#         root_node: The root AST node
#     Returns:
#         list: List of langchain documents for each paragraph
#     """
#     ast = parser.parse(source_code)
#     print(ast.root_node)
#     # cursor = QueryCursor(query_paragraph_header)

#     # para_nodes = cursor.matches(ast.root_node)

#     # paragraphs = []

#     # for para in para_nodes:
#     #     para_statements = extract_paragraphs_from_ast(para[1])
#     #     paragraph_object = Captured_Paragraph(file_name, body=para_statements)
#     #     paragraphs.append(paragraph_object)

#     # print(len(paragraphs))

#     # docs = []
#     # # docs = convert_to_langchain_docs(paragraphs, file_name)
#     # return docs

# if __name__ == "__main__":

#     # Store the list of files inside a specified folder name
#     folder_path = './cics-genapp/src'
#     file_names = []
#     for root, _, files in os.walk(folder_path):
#         for file in files:
#             if file.endswith('.cbl'):
#                 file_names.append(root+'/'+file)

#     total_docs = []

#     # file_names = ["test.cob"]

#     count = 0
#     error_count = 0
#     for file_name in file_names:
#         code = read_cobol_code_from_file(file_name)
#         captured_procedure = extract_procedure_division_from_ast(code=code, file_name=os.path.basename(file_name))
#         if captured_procedure:
#             total_docs.append(captured_procedure)
#         else:
#             print("Skipping file due to errors:", file_name)
#             error_count += 1
#         count += 1
    
#     print(f"Total files processed: {count}, with errors: {error_count}")
#     # get_vector_store(captured_items=total_docs, index_name="vector_db_index/cics_genapp_index_procedure")


#     # # Read and update the markdown files
#     # get_vector_store_readme(repo_path="./cics-genapp/docs", index_name="vector_db_index/cics_genapp_index_readme")
