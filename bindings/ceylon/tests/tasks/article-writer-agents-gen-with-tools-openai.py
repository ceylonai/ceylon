from typing import Optional, Type

from langchain.pydantic_v1 import BaseModel, Field
from langchain.runnables.openai_functions import OpenAIFunction
from langchain_community.chat_models import ChatOllama
from langchain_community.llms.openai import OpenAIChat, OpenAI
from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain_openai import ChatOpenAI
from loguru import logger

from ceylon.llm import Task, SpecializedAgent, TaskManager


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

    llm = ChatOpenAI(model="gpt-4o-mini")
    tool_llm = ChatOpenAI(model="gpt-4o-mini")

    # llm = ChatOllama(model="llama3.1:latest")
    # tool_llm = OllamaFunctions(model="llama3.1:latest", format="json")

    # Create specialized agents
    agents = [
        SpecializedAgent(
            name="research",
            role="Online search things",
            context="Can search for facts and points on the internet in a variety of ways.",
            skills=[
                "Search online",
                "Keyword Research",
                "Online Research",
                "Research",
                "Researching",
                "Researcher",
            ],
            tools=[],
            llm=llm,
            tool_llm=tool_llm
        ),
        SpecializedAgent(
            name="image_generation",
            role="Image Generation",
            context="Can generate images from text.",
            skills=[
                "Image Generation",
            ],
            tools=[
                ImageGenerationTool()
            ],
            llm=llm,
            tool_llm=tool_llm
        ),

        SpecializedAgent(
            name="writing",
            role="Content Strategist & Writer",
            context="Deep understanding of various writing styles, content formats, "
                    "and audience engagement strategies. Knowledgeable about "
                    "SEO-friendly writing, storytelling techniques, and brand voice "
                    "development. Familiar with content management systems and digital publishing platforms.",
            skills=[
                "Creative Writing",
                "Technical Writing",
                "Copywriting",
                "Content Strategy",
                "Storytelling",
                "SEO Writing",
                "Editing and Proofreading",
                "Brand Voice Development",
                "Audience Analysis",
                "Multimedia Content Creation"
            ],
            tools=[],
            llm=llm
        ),

        SpecializedAgent(
            name="seo_optimization",
            role="SEO Strategist",
            context="Comprehensive understanding of search engine algorithms,"
                    " ranking factors, and SEO best practices. Proficient in technical SEO,"
                    " content optimization, and link building strategies. Familiar with local SEO,"
                    " mobile optimization, and voice search optimization.",
            skills=[
                "Keyword Research",
                "On-Page SEO",
                "Off-Page SEO",
                "Technical SEO",
                "Content Optimization",
                "Link Building",
                "Local SEO",
                "Mobile SEO",
                "Voice Search Optimization",
                "SEO Analytics and Reporting"
            ],
            tools=[],
            llm=llm
        ),

        SpecializedAgent(
            name="web_publishing",
            role="Digital Content Manager",
            context="Extensive knowledge of web publishing platforms, "
                    "content management systems, and digital asset management. "
                    "Proficient in HTML, CSS, and basic JavaScript. Familiar with web accessibility standards, "
                    "responsive design principles, and UX/UI best practices.",
            skills=[
                "CMS Management",
                "HTML/CSS",
                "Content Scheduling",
                "Digital Asset Management",
                "Web Accessibility",
                "Responsive Design",
                "Version Control",
                "A/B Testing",
                "Web Analytics",
                "User Experience Optimization"
            ],
            tools=[],
            llm=llm
        )
    ]

    task_manager = TaskManager(tasks, agents, tool_llm=tool_llm, llm=llm)
    tasks = task_manager.do(inputs=b"")

    for t in tasks:
        print(t.final_answer)
