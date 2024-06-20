import asyncio
import os

from duckduckgo_search import DDGS
from langchain_core.tools import StructuredTool

from ceylon.llm.agent import LLMAgent
from ceylon.llm.manger import LLMManager
from ceylon.llm.runner import AgentLLMRunner

os.environ.setdefault("SERPER_API_KEY", "866312803646d82919ddd409469c9ad106c0d3c1")


def search_query(keywords: str, ):
    """Searches the given keywords on duckduckgo
        Valid parameters: 'keywords'
    """
    results = DDGS().text(keywords, safesearch='off', timelimit='y', max_results=10)
    return results


async def main():
    runner = AgentLLMRunner(workspace_name="ceylon-ai")
    runner.register_agent(LLMManager())
    # runner.register_agent(LLMAgent(
    #     name="writer",
    #     position="Assistant Writer",
    #     responsibilities=["Create high-quality, original content that matches the audience's tone and style."],
    #     instructions=[
    #         "Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."]
    # ))

    runner.register_agent(LLMAgent(
        name="researcher",
        position="Content Researcher",
        responsibilities=["Conducting thorough and accurate research to support content creation."],
        instructions=[
            "Find credible sources, verify information, and provide comprehensive and relevant data while ensuring ethical standards and privacy are maintained."],
        tools=[
            StructuredTool.from_function(search_query)
        ]
    ))

    await runner.run(
        {"title": "How to use AI for Machine Learning", "tone": "informal", "length": "short", "style": "creative"}
    )
    leader = runner.leader()


if __name__ == '__main__':
    asyncio.run(main())
