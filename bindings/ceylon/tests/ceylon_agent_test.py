import asyncio
import random
import time

from ceylon import *

print(version())


class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, id, name, is_leader, workspace_id):
        super().__init__(id=id, name=name, is_leader=is_leader, workspace_id=workspace_id, on_message=self,
                         processor=self)

    async def on_message(self, agent_id, message):
        print(f"{self.name()} Received message from = '{agent_id}' message= {message}", agent_id, message)

    async def run(self):
        while True:
            await self.broadcast("Hi from " + self.name() + " at " + str(time.time()))
            print(f"{self.name()} Broadcasted message")
            await asyncio.sleep(random.randint(1, 5))


async def main():
    uniffi_set_event_loop(asyncio.get_event_loop())
    agent1 = Agent(name="ceylon-ai-1", is_leader=True, id="ceylon-ai-1", workspace_id="ceylon-ai")
    agent2 = Agent(name="ceylon-ai-2", is_leader=False, id="ceylon-ai-2", workspace_id="ceylon-ai")
    agent3 = Agent(name="ceylon-ai-3", is_leader=False, id="ceylon-ai-3", workspace_id="ceylon-ai")
    agent4 = Agent(name="ceylon-ai-4", is_leader=False, id="ceylon-ai-4", workspace_id="ceylon-ai")

    await run_workspace([agent1, agent2, agent3, agent4])


if __name__ == '__main__':
    asyncio.run(main())
