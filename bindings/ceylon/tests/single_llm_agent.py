import asyncio

from langchain_community.chat_models import ChatOllama

from ceylon import AgentRunner
from ceylon.llm.llm_agent import LLMAgent


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    llm_lib = ChatOllama(model="llama3:instruct")
    # llm_lib = ChatOpenAI(model="gpt-4o")
    runner.register_agent(LLMAgent(
        name="writer",
        position="Assistant Writer",
        llm=llm_lib,
        responsibilities=["Create high-quality, original content that matches the audience's tone and style."],
        instructions=[
            "Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."]
    ))
    runner.register_agent(LLMAgent(
        name="resercher",
        position="Assistant Writer",
        llm=llm_lib,
        responsibilities=["Create high-quality, original content that matches the audience's tone and style."],
        instructions=[
            "Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."]
    ))

    await runner.run(
        {
            "request": "I want to create a blog post",
            "title": "How to use AI for Machine Learning",
            "tone": "informal",
            "length": "large",
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
