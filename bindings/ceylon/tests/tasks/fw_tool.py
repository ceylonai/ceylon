from typing import Optional, Type
from pydantic import BaseModel
from langchain.tools.file_management.write import WriteFileTool
import json
from json import JSONDecodeError


class FixedWriteFileTool(WriteFileTool):
    description = (
        "Write file to disk. "
        "Provide the file path and the text content as a JSON-formatted string. "
        "Example input: {\"file_path\": \"test.txt\", \"text\": \"This is some test text.\"}"
    )
    args_schema: Optional[Type[BaseModel]] = None

    def _run(self, file_path_and_text: str) -> str:
        try:
            data = json.loads(file_path_and_text)
            if "file_path" not in data or "text" not in data:
                return "Invalid input: missing 'file_path' or 'text' key."
            return super()._run(data["file_path"], data["text"])
        except Exception as e:
            print(e)
            print("Invalid JSON input.", file_path_and_text)
            return "Failed to write file: Invalid JSON input."
        return super()._run(data["file_path"], data["text"])

    @staticmethod
    def is_valid_json(input_string):
        try:
            json.loads(input_string)
            return True
        except JSONDecodeError:
            return False

    # def _run(self, file_path_and_text: str) -> str:
    #     print()
    #     print(file_path_and_text)
    #     file_path_and_text = "{\"" + file_path_and_text + "\"}"
    #     print()
    #     print(file_path_and_text)
    #     file_path_and_text_json = None
    #     if FixedWriteFileTool.is_valid_json(file_path_and_text):
    #         file_path_and_text_json = json.loads(file_path_and_text)
    #         return super()._run(file_path_and_text_json["file_path"], file_path_and_text_json["text"])
    #     else:
    #         return "Failed to write file."
    #
    #     return super().run(file_path_and_text_json["file_path"], file_path_and_text_json["text"])
