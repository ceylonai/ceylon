import asyncio

from ceylon import *

print(version())


async def main():
    agent1 = Agent(name="ceylon-ai", is_leader=True)
    agent2 = Agent(name="ceylon-ai-2")

    agent_runner1 = AgentRunner(agent1, "ceylon-ai-article-writer")

    await agent_runner1.connect("http://localhost:8080")
    await agent_runner1.start()

    agent_runner2 = AgentRunner(agent2, "ceylon-ai-article-writer")

    await agent_runner2.connect("http://localhost:8080")
    await agent_runner2.start()


if __name__ == '__main__':
    asyncio.run(main())
