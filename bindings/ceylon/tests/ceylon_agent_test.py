import asyncio
import json
import pickle
import random
import time

from ceylon.ceylon import AgentCore, MessageHandler, Processor, MessageType
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, is_leader):
        super().__init__(name=name, is_leader=is_leader, on_message=self, processor=self, meta=None)

    async def on_message(self, agent_id, message):
        print(self.name(), message.message, message.type)
        # print({
        #     "self_name": self.name(),
        #     "self_id": self.id(),
        #     "to": message.to_id,
        #     "from_id": message.originator_id,
        #     "from_name": message.originator,
        #     "message_type": message.type.name
        # })

    async def run(self, inputs):
        print(f"{self.name()} run", inputs)
        await asyncio.sleep(random.randint(1, 100))
        # while True:
        await self.broadcast(pickle.dumps({
            "type": "Message",
            "from": self.name(),
            "data": "Hi from " + self.name() + " at " + str(time.time()),
        }), f"ceylon-ai-{random.randint(1, 24)}")
        #     # print(f"{self.name()} Broadcast message")
        #     await asyncio.sleep(random.randint(1, 10))


#
async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(Agent(name="ceylon-ai-1", is_leader=True, ))
    runner.register_agent(Agent(name="ceylon-ai-2", is_leader=False, ))
    # runner.register_agent(Agent(name="ceylon-ai-3", is_leader=False, ))
    # runner.register_agent(Agent(name="ceylon-ai-4", is_leader=False, ))

    await runner.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
