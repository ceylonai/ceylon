import asyncio
import os

from duckduckgo_search import DDGS
from langchain_community.chat_models import ChatOllama
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
    ollama_llama3 = ChatOllama(model="llama3")
    runner.register_agent(LLMManager(ollama_llama3))
    runner.register_agent(LLMAgent(
        name="writer",
        position="Assistant Writer",
        llm=ollama_llama3,
        responsibilities=["Create high-quality, original content that matches the audience's tone and style."],
        instructions=[
            "Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."]
    ))

    runner.register_agent(LLMAgent(
        name="researcher",
        position="Content Researcher",
        llm=ollama_llama3,
        responsibilities=["Conducting thorough and accurate research to support content creation."],
        instructions=[
            "Find credible sources, verify information, and provide comprehensive and relevant "
            "data while ensuring ethical "
            "standards and privacy are maintained.",
            "summarize content"],
        tools=[
            StructuredTool.from_function(search_query)
        ]
    ))

    await runner.run(
        {
            "request": "I want to create a blog post",
            "title": "How to use AI for Machine Learning",
            "tone": "informal",
            "length": "short",
            "style": "creative"
        }
    )
    leader = runner.leader()


if __name__ == '__main__':
    asyncio.run(main())
