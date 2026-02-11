
# For now:
# Ignoring the typedef and storage class specifiers for structs and enums
# For functions I have considered pointer return and normal return types

query_schema = """
    (struct_specifier
        name: (type_identifier)? @struct_name
        body: (field_declaration_list)
    ) @struct
    (enum_specifier
        name: (type_identifier)? @enum_name
        body: (enumerator_list)
    ) @enum
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
    (comment) @comments
    """