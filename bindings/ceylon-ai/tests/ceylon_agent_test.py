import asyncio

from ceylon import *

print(version())


async def main():
    agent1 = AgentCore(name="ceylon-ai-1", is_leader=True, id="ceylon-ai-1", workspace_id="ceylon-ai")
    agent2 = AgentCore(name="ceylon-ai-2", is_leader=False, id="ceylon-ai-2", workspace_id="ceylon-ai")

    await run_workspace([agent1, agent2])


if __name__ == '__main__':
    asyncio.run(main())
