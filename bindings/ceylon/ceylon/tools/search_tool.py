from typing import Any, Type, Optional

from duckduckgo_search import DDGS
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic.v1 import BaseModel, Field


class SearchToolInputSchema(BaseModel):
    """Input for SearchTool."""

    query: str = Field(
        ...,
        description="The query to search for. This should be a string containing the search terms.",
    )


class SearchTool(BaseTool):
    name = "Search"
    description: str = (
        "Use this tool to search on DuckDuckGo. Use the `query` parameter to define the search terms. its a string containing the search terms. "
    )

    args_schema: Type[SearchToolInputSchema] = SearchToolInputSchema

    def _run(self, query: str,
             run_manager: Optional[CallbackManagerForToolRun] = None, ):
        """
            Searches the given keywords on DuckDuckGo and returns the search results.
            Parameters:
            query (str): The keywords to search for. This should be a string containing the search terms.

            Returns:
            list: A list of dictionaries, where each dictionary contains the following keys:
                - title (str): The title of the search result.
                - href (str): The URL of the search result.
                - body (str): A brief description of the search result.
        """
        print(f"Searching for {query}")
        results = DDGS().text(query, safesearch='off', timelimit='y', max_results=10)
        return results

    async def _arun(self, *args: Any, **kwargs: Any, ) -> Any:
        return self._run(*args, **kwargs)
