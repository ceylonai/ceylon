import asyncio

from ceylon import *

print(version())


async def main():
    agent = Agent(name="ceylon-ai")

    print(agent.name)
    print(agent.id)
    print(agent.workspace_id)

    agent_runner = AgentRunner(agent, "ceylon-ai-article-writer")

    await agent_runner.connect("http://localhost:8080")
    await agent_runner.start()


if __name__ == '__main__':
    asyncio.run(main())
