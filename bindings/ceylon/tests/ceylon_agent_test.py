import asyncio
import random
import time

from ceylon import AgentCore, MessageHandler, Processor, uniffi_set_event_loop, Workspace, WorkspaceConfig



class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, is_leader):
        super().__init__(name=name, is_leader=is_leader, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        print(f"{self.name()} Received message from = '{agent_id}' message= {message}", agent_id, message)

    async def run(self):
        while True:
            await self.broadcast("Hi from " + self.name() + " at " + str(time.time()))
            print(f"{self.name()} Broadcast message")
            await asyncio.sleep(random.randint(1, 5))


#
async def main():
    uniffi_set_event_loop(asyncio.get_event_loop())
    agent1 = Agent(name="ceylon-ai-1", is_leader=True, )
    agent2 = Agent(name="ceylon-ai-2", is_leader=False, )
    agent3 = Agent(name="ceylon-ai-3", is_leader=False, )
    agent4 = Agent(name="ceylon-ai-4", is_leader=False, )

    LLMAgent(name="ceylon-ai-1", is_leader=True, on_message=agent1, processor=agent1)

    workspace = Workspace(agents=[agent1, agent2, agent3, agent4],
                          config=WorkspaceConfig(
                              name="ceylon-ai",
                              host="/ip4/0.0.0.0/tcp",
                              port=8888
                          ))
    await workspace.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
