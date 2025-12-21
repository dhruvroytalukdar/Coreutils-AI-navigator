from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_c as tsc
from utils.models import Captured_Struct, Captured_Enum, Captured_Function, Captured_Comment
from utils.query_schema import query_schema
from utils.vector_store import get_vector_store, get_top_comments, get_top_non_comments, get_top_functions
import os

# Initialize the C language
C_LANGUAGE = Language(tsc.language())
# Create a parser
parser = Parser(C_LANGUAGE)
# Create a query and cursor
query = Query(C_LANGUAGE, query_schema)
cursor = QueryCursor(query)

def parse_c_code(code: str):
    """
    The function parses C code and returns the corresponding AST.
    
    Args:
        code: C source code as a string
    
    Returns:
        tree_sitter.Tree: The parsed syntax tree
    """
    # Parse the code
    tree = parser.parse(bytes(code, "utf8"))
    return tree


def read_c_code_from_file(file_path: str) -> str:
    """
    Read C code from a file.
    
    Args:
        file_path: Path to the C source file
    Returns:
        str: C source code as a string
    """
    with open(file_path, 'r') as file:
        return file.read()

def capture_objects_from_file(file_path: str) -> tuple:
    """
    Extract and capture objects from a C source file.
    
    Args:
        file_path: Path to the C source file
    Returns:
        list: Lists of captured functions, structs, enums, and comments
    """

    # Example C code
    c_code = read_c_code_from_file(file_path)

    # Parse the code
    tree = parse_c_code(c_code)

    # Get root node
    root_node = tree.root_node

    # Execute the query
    captures = cursor.matches(root_node)

    captured_functions = []
    captured_structs = []
    captured_enums = []
    captured_comments = []

    for capture in captures:
        # Capture struct definitions
        if capture[0] == 0:
            # check for comment node before struct
            curr_node = capture[1]["struct"][0]
            prev_node = curr_node.prev_sibling
            comment_text = None

            if prev_node and prev_node.type == "comment":
                comment_text = prev_node.text.decode('utf8')
            
            if "struct_name" not in capture[1].keys():
                struct_name = "STRUCT_WITH_NO_NAME"
            else:
                struct_name = capture[1]["struct_name"][0].text.decode('utf8')
            
            struct_body = capture[1]["struct"][0].text.decode('utf8')
            captured_struct = Captured_Struct(struct_name, struct_body, file_path, comment_text)
            captured_structs.append(captured_struct)
        # Capture enum definitions
        elif capture[0] == 1:
            # check for comment node before enum
            curr_node = capture[1]["enum"][0]
            prev_node = curr_node.prev_sibling
            comment_text = None
            if prev_node and prev_node.type == "comment":
                comment_text = prev_node.text.decode('utf8')
            
            if "enum_name" not in capture[1].keys():
                enum_name = "ENUM_WITH_NO_NAME"
            else:
                enum_name = capture[1]["enum_name"][0].text.decode('utf8')

            enum_body = capture[1]["enum"][0].text.decode('utf8')
            captured_enum = Captured_Enum(enum_name, enum_body, file_path, comment_text)
            captured_enums.append(captured_enum)
        # Capture function definitions
        elif capture[0] == 2:
            # check for comment node before function
            curr_node = capture[1]["func_body"][0]
            prev_node = curr_node.prev_sibling
            comment_text = None
            if prev_node and prev_node.type == "comment":
                comment_text = prev_node.text.decode('utf8')

            func_name = capture[1]["func_name"][0].text.decode('utf8')
            func_body = capture[1]["func_body"][0].text.decode('utf8')
            called_funcs = []
            if "called_func" in capture[1].keys():
                for called_func_capture in capture[1]["called_func"]:
                    called_func_name = called_func_capture.text.decode('utf8')
                    if called_func_name not in called_funcs:
                        called_funcs.append(called_func_name)
            captured_function = Captured_Function(func_name, func_body, called_funcs, file_path, comment_text)
            captured_functions.append(captured_function)
        # Capture comments
        elif capture[0] == 3:
            comments = capture[1]["comments"]
            for comment in comments:
                comment_text = comment.text.decode('utf8')
                captured_comment = Captured_Comment(comment_text, file_path)
                captured_comments.append(captured_comment)

    return captured_functions, captured_structs, captured_enums, captured_comments


def main():
    # Store the list of files inside a specified folder name
    folder_path = './coreutils/src'
    # file_names = ["test_lookup.c"]
    file_names = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.c') or file.endswith('.h'):
                file_names.append(root+'/'+file)
            
    list_of_captured_functions = []
    list_of_captured_structs = []
    list_of_captured_enums = []
    list_of_captured_comments = []

    for file_name in file_names:
        captured_functions, captured_structs, captured_enums, captured_comments = capture_objects_from_file(file_name)
        list_of_captured_functions.extend(captured_functions)
        list_of_captured_structs.extend(captured_structs)
        list_of_captured_enums.extend(captured_enums)
        list_of_captured_comments.extend(captured_comments)

    print("\n\n" + str(len(list_of_captured_functions)) + " functions captured.")
    print(str(len(list_of_captured_structs)) + " structs captured.")
    print(str(len(list_of_captured_enums)) + " enums captured.")
    print(str(len(list_of_captured_comments)) + " comments captured.\n\n")

    get_vector_store(
        list_of_captured_comments,
        index_name="vector_db_index/coreutils_index_comments",
    )

    get_vector_store(
        list_of_captured_functions + list_of_captured_structs + list_of_captured_enums,
        index_name="vector_db_index/coreutils_index_functions",
    )

if __name__ == "__main__":
    main()
