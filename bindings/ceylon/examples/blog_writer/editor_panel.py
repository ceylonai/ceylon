import asyncio
from typing import Optional, Type

from langchain.pydantic_v1 import BaseModel, Field
from langchain_community.chat_models import ChatOllama
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from loguru import logger

from ceylon import Task, SpecializedAgent, TaskManager
from ceylon.llm.tools.search_tool import SearchTools


class QueryInput(BaseModel):
    prompt: str = Field(description="Input prompt")


class ImageGenerationTool(BaseTool):
    name = "ImageGenerationTool"
    description = "Useful for when you need to generate an image. Input should be a description of what you want to generate."
    args_schema: Type[BaseModel] = QueryInput
    return_direct: bool = True

    def _run(
            self, query: str, run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Use the tool."""
        logger.info(f"Processing query: {query}")
        # This is a simple example. You can replace this with more complex logic.
        return f"https://cdn.pixabay.com/photo/2024/01/02/10/33/stream-8482939_1280.jpg"

    async def _arun(
            self,
            query: str,
            run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool asynchronously."""
        # For this example, we're delegating to the sync implementation.
        # If the processing is expensive, you might want to implement a truly
        # asynchronous version or remove this method entirely.
        return self._run(query, run_manager=run_manager.get_sync() if run_manager else None)


# Example usage
if __name__ == "__main__":
    # Create a task with initial subtasks
    article_task = Task(name="Write Article",
                        description="Write an article about AI advancements. The final output should strictly include only the title and the content and cover image, without any additional sections or formatting.")

    tasks = [
        article_task
    ]

    # llm_lib = ChatOpenAI(model="gpt-4o-mini")
    # llm_tool = ChatOpenAI(model="gpt-4o")

    llm_lib = ChatOllama(model="llama3.1:latest")
    llm_tool = OllamaFunctions(model="llama3.1:latest", format="json")

    # Create specialized agents
    agents = [
        SpecializedAgent(
            name="researcher",
            role="Research Specialist",
            context="Searches for relevant information on the web to gather data for content creation.",
            skills=[
                "Online Research",
                "Keyword Research",
                "Information Retrieval",
                "Fact-Checking",
                "Source Verification",
                "Research"
            ],
            tools=[
                SearchTools.search_internet
                # Add any additional tools here, e.g., WikipediaQueryRun
            ],
            llm=llm_lib,
            tool_llm=llm_tool
        ),
        SpecializedAgent(
            name="illustrator",
            role="Illustrator ",
            context="Creates images from text descriptions. The final output should strictly include only the title and the content and cover image, without any additional sections or formatting.",
            skills=[
                "Image Generation",
                "Captioning",
                "Image Manipulation",
                "Image Editing",
            ],
            tools=[
                ImageGenerationTool()
                # Add any additional tools here, e.g., WikipediaQueryRun
            ],
            llm=llm_lib,
            tool_llm=llm_tool
        ),

        SpecializedAgent(
            name="writer",
            role="Content Writer",
            context="Simplifies technical concepts with metaphors and creates narrative-driven content while ensuring scientific accuracy.",
            skills=[
                "Creative Writing",
                "Technical Writing",
                "Storytelling",
                "Content Strategy",
                "SEO Writing",
                "Editing and Proofreading"
            ],
            tools=[],
            llm=llm_lib,
            tool_llm=llm_tool
        ),
    ]

    task_manager = TaskManager(tasks, agents, tool_llm=llm_tool, llm=llm_lib)
    tasks = asyncio.run(task_manager.async_do(inputs=b""))

    for t in tasks:
        print(t.final_answer)
