import asyncio

from ceylon import AgentRunner, LLMAgent
from ceylon.llm_agent import LLMManager


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(LLMManager())
    runner.register_agent(LLMAgent(
        name="writer",
        responsibility="Create high-quality, original content that matches the audience's tone and style.",
        instructions="Ensure clarity, accuracy, and proper formatting while respecting ethical guidelines and privacy."
    ))

    runner.register_agent(LLMAgent(
        name="researcher",
        responsibility="Conducting thorough and accurate research to support content creation.",
        instructions="Find credible sources, verify information, and provide comprehensive and relevant data while ensuring ethical standards and privacy are maintained."
    ))

    await runner.run(
        {"title": "How to use AI for Machine Learning", "tone": "informal", "length": "short", "style": "creative"}
    )
    leader = runner.leader()


if __name__ == '__main__':
    asyncio.run(main())
