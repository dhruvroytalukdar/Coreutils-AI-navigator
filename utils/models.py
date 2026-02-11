class Captured_Comment:
    def __init__(self, text: str, file_name: str) -> None:
        self.comment_text = text
        self.file_name = file_name

    def __str__(self):
        return f"Comment: {self.comment_text}\n"
    
    def get_content(self):
        return self.comment_text

    def get_metadata(self):
        return {
            "document_type": "comment",
            "file_name": self.file_name
        }


class Captured_Procedure:
    def __init__(self, file_name: str, body: str) -> None:
        self.file_name = file_name
        self.body = body
    
    def get_content(self) -> str:
        return self.body

    def get_metadata(self) -> dict:
        return {
            "file_name":self.file_name
        }

class Captured_Paragraph:
    def __init__(self, file_name: str, body: list[str]) -> None:
        self.file_name = file_name
        self.body = '\n'.join(body)
    
    def get_content(self) -> str:
        return self.body

    def get_metadata(self) -> dict:
        return {
            "file_name":self.file_name
        }
    
class Captured_Function:
    def __init__(self, name: str, body: str, called_functions: list, file_name: str, comment: str = None) -> None:
        self.function_name = name
        self.function_body = body
        self.called_functions = called_functions
        self.comment = comment
        self.file_name = file_name

    def __str__(self):
        return f"Function Name: {self.function_name}\nCalled Functions: {', '.join(self.called_functions)}\nFunction Body:\n{self.function_body}\nFunction Comment: {self.comment}\n"

    def get_content(self):
        return self.function_body

    def get_metadata(self):
        return {
            "function_name": self.function_name,
            "called_functions": self.called_functions,
            "document_type": "function_definition",
            "function_comment": self.comment,
            "file_name": self.file_name
        }

class Captured_Struct:
    def __init__(self, name: str, body: str, file_name: str, comment: str = None) -> None:
        self.struct_name = name
        self.struct_body = body
        self.comment = comment
        self.file_name = file_name

    def __str__(self):
        return f"Struct Name: {self.struct_name}\nStruct Body:\n{self.struct_body}\nStruct Comment: {self.comment}\nStruct File Name: {self.file_name}\n"
    
    def get_content(self):
        return self.struct_body

    def get_metadata(self):
        return {
            "struct_name": self.struct_name,
            "document_type": "struct_definition",
            "struct_comment": self.comment,
            "file_name": self.file_name
        }

class Captured_Enum:
    def __init__(self, name: str, body: str, file_name: str, comment: str = None) -> None:
        self.enum_name = name
        self.enum_body = body
        self.comment = comment
        self.file_name = file_name

    def __str__(self):
        return f"Enum Name: {self.enum_name}\nEnum Body:\n{self.enum_body}\nEnum Comment: {self.comment}\nEnum File Name: {self.file_name}\n"
    
    def get_content(self):
        return self.enum_body

    def get_metadata(self):
        return {
            "enum_name": self.enum_name,
            "document_type": "enum_definition",
            "enum_comment": self.comment,
            "file_name": self.file_name
        }