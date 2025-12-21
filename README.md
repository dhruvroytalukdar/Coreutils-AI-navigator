# C Language AST Parser using tree-sitter

This project demonstrates how to parse C code and generate Abstract Syntax Trees (AST) using the python-tree-sitter library.

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the parser:

```bash
python c_ast_parser.py
```

## Features

- **Parse C Code**: Convert C source code into an AST
- **Traverse Tree**: Recursively walk through the AST structure
- **Node Information**: Extract detailed information about AST nodes
- **Node Search**: Find specific node types (e.g., function definitions, variables)

## Key Functions

- `parse_c_code(code)`: Parse C code and return the syntax tree
- `traverse_tree(node)`: Print the entire AST structure
- `get_node_info(node)`: Get detailed information about a specific node
- `find_nodes_by_type(node, node_type)`: Find all nodes of a specific type

## Example Output

The script will parse a sample C program and display:
- Complete AST structure
- Root node information
- All function definitions found in the code

## Common Node Types

- `translation_unit`: Root node
- `function_definition`: Function declarations
- `declaration`: Variable declarations
- `compound_statement`: Code blocks
- `call_expression`: Function calls
- `identifier`: Variable/function names
- `number_literal`: Numeric values

## Customization

You can modify the example C code in the `main()` function or create functions to:
- Extract function signatures
- Find variable declarations
- Analyze control flow structures
- Extract comments
- And more!
