import asyncio

from ceylon import AgentRunner, LLMAgent


async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(LLMAgent(name="writer", is_leader=True, ))
    await runner.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
