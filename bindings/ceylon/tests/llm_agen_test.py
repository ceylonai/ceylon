import asyncio
import datetime
import os
import uuid

from duckduckgo_search import DDGS
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import StructuredTool

from ceylon import AgentRunner
from ceylon.llm.agent import LLMAgent

os.environ.setdefault("SERPER_API_KEY", "866312803646d82919ddd409469c9ad106c0d3c1")


def search_query(keywords: str, ):
    """Searches the given keywords on duckduckgo
        Valid parameters: 'keywords'
    """
    results = DDGS().text(keywords, safesearch='off', timelimit='y', max_results=10)
    return results


def publish_content(content: str, ):
    """Publishes the given content
        Valid parameters: 'content'
    """
    # Write to text file
    # name should be unique
    name = f"content-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.txt"
    with open(name, "w") as f:
        f.write(content)
    return f"Published {content}"


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    ollama_llama3 = ChatOllama(model="llama3")
    # runner.register_agent(LLMManager(ollama_llama3))
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
    #
    runner.register_agent(LLMAgent(
        name="editor",
        position="Content Editor",
        llm=ollama_llama3,
        responsibilities=[
            "Review and refine content to ensure it meets quality standards and aligns with the editorial guidelines."],
        instructions=[
            "Check for grammatical errors, clarity, and coherence.",
            "Ensure the content is engaging and maintains the intended tone and style.",
            "Provide constructive feedback to the writer."
        ]
    ))
    #
    runner.register_agent(LLMAgent(
        name="publisher",
        position="Content Publisher",
        llm=ollama_llama3,
        responsibilities=[
            "Publish the finalized content on the designated platform and ensure proper formatting and SEO optimization."],
        instructions=[
            "Format the content according to platform guidelines.",
            "Optimize for SEO by including relevant keywords, meta descriptions, and tags.",
            "Ensure all links are functional and images are properly placed."
        ],
        tools=[
            StructuredTool.from_function(publish_content)
        ]
    ))

    await runner.run(
        {
            "request": "I want to create a blog post",
            "title": "How to use AI for Machine Learning",
            "tone": "informal",
            "length": "short",
            "style": "creative"
        },
        network={
            "researcher": [],
            "writer": ["researcher"],
            "editor": ["writer"],
            "publisher": ["editor"]
        }
    )
    leader = runner.leader()


if __name__ == '__main__':
    asyncio.run(main())
