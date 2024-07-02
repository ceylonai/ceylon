import unittest
from typing import Any, Type, Optional
from unittest.mock import patch, mock_open, Mock

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool


class FilePublisherSchema(BaseModel):
    """Input for SendMessageTool."""

    file_content: str = Field(
        ...,
        description="The file content to be published. This should be a string containing the text or data that needs to be published.",
    )
    file_name: str = Field(
        ...,
        description="The file name to be created. This should be a string containing the name of the file to be created.",
    )


class FilePublisherTool(BaseTool):
    name = "File Publisher"
    description: str = (
        """
        Use this tool to publish content in a file. use the `file_content` and `file_name` parameters
         to define the content and the name of the file to be created.
         parameters:
         file_content (str): The content to be published. This should be a string containing the text or data that needs to be published.
         file_name (str): The name of the file to be created. This should be a string containing the name of the file to be created.
        """
    )

    args_schema: Type[FilePublisherSchema] = FilePublisherSchema

    def _run(self,
             file_content: str,
             file_name: str,
             run_manager: Optional[CallbackManagerForToolRun] = None, ) -> str:
        """
       Publishes the given content.

       Parameters:
       file_content (str): The content to be published. This should be a string containing the text or data that needs to be published.
       file_name (str): The name of the file to be created. This should be a string containing the name of the file to be created.

       Returns:
       None
   """
        print(f"Publishing content")
        name = f"content-{file_name}.txt"

        try:
            # Open the file in write mode
            with open(name, "a", encoding="utf-8") as f:
                f.write(file_content)
            return f"Published {file_content} in {name}"
        except Exception as e:
            return f"An error occurred: {e}"

    async def _arun(self, *args: Any, **kwargs: Any, ) -> Any:
        return self._run(*args, **kwargs)
