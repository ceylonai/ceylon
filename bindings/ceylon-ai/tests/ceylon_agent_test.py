import asyncio

from ceylon import *

print(version())


async def main():
    agent1 = Agent(name="ceylon-ai", is_leader=True)
    agent2 = Agent(name="ceylon-ai-2")

    await run_workspace([agent1, agent2], "test")


if __name__ == '__main__':
    asyncio.run(main())
