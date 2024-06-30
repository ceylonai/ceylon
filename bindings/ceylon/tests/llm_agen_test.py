import asyncio

from ceylon import AgentRunner, LLMAgent
from ceylon.llm_agent import LLMManager


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(LLMManager())
    runner.register_agent(LLMAgent(name="writer"))
    runner.register_agent(LLMAgent(name="researcher"))
    await runner.run({
        "title": "How to use AI for Machine Learning",
    })
    leader = runner.get_leader()
    print(leader.report)


if __name__ == '__main__':
    asyncio.run(main())
