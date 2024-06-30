import asyncio
import datetime

from duckduckgo_search import DDGS
from langchain_community.chat_models import ChatOllama, ChatOpenAI
from langchain_community.llms.openai import OpenAI
from langchain_core.tools import StructuredTool

from ceylon import AgentRunner
from ceylon.llm.llm_agent import LLMAgent


def search_query(keywords: str, ):
    """
        Searches the given keywords on DuckDuckGo and returns the search results.
    Parameters:
    keywords (str): The keywords to search for. This should be a string containing the search terms.

    Returns:
    list: A list of dictionaries, where each dictionary contains the following keys:
        - title (str): The title of the search result.
        - href (str): The URL of the search result.
        - body (str): A brief description of the search result.
   """
    print(f"Searching for {keywords}")
    results = DDGS().text(keywords, safesearch='off', timelimit='y', max_results=10)
    return results


def publish_content(content: str, name: str):
    """
        Publishes the given content.

        Parameters:
        content (str): The content to be published. This should be a string containing the text or data that needs to be published.
        name (str): The name of the file to be created. This should be a string containing the name of the file to be created.

        Returns:
        None
    """
    print(f"Publishing content")
    name = f"content-{name}.txt"

    try:
        # Open the file in write mode
        with open(name, "a", encoding="utf-8") as f:
            f.write(content)
        return f"Published {content} in {name}"
    except Exception as e:
        return f"An error occurred: {e}"


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    llm_lib = ChatOllama(model="phi3:instruct")
    llm_lib = ChatOpenAI(model="gpt-4o")
    runner.register_agent(LLMAgent(
        name="writer",
        position="Assistant Writer",
        llm=llm_lib,
        responsibilities=["Create high-quality, original content that matches the audience's tone and style."],
        instructions=[
            "Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."]
    ))
    runner.register_agent(LLMAgent(
        name="name_chooser",
        position="Select File name",
        llm=llm_lib,
        responsibilities=["Create high-quality, SEO friendly file name."],
        instructions=[
            "Easy to read and understand."
        ]
    ))

    runner.register_agent(LLMAgent(
        name="researcher",
        position="Content Researcher",
        llm=llm_lib,
        responsibilities=[
            "Conducting thorough and accurate research to support content creation.",

        ],
        instructions=[
            "Must only Find the most relevant 2 or 3 sources."
            "Find credible sources, verify information, and provide comprehensive and relevant "
            "data while ensuring ethical "
            "standards and privacy are maintained.",
            "Must  summarize output without source references."
        ],
        tools=[
            StructuredTool.from_function(search_query)
        ]
    ))
    #
    runner.register_agent(LLMAgent(
        name="editor",
        position="Content Editor",
        llm=llm_lib,
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
        llm=llm_lib,
        responsibilities=[
            "Publish the finalized content using the publishing tools and platforms specified by the writer.",
        ],
        instructions=[
            "Publish it as finalized and polished content",
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
            "name_chooser": [],
            "researcher": [],
            "writer": ["researcher"],
            "editor": ["writer"],
            "publisher": ["editor", "name_chooser"]
        }
    )


if __name__ == '__main__':
    asyncio.run(main())
