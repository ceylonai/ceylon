import asyncio
import json
import random
import time

from ceylon.ceylon import AgentCore, MessageHandler, Processor, MessageType
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, is_leader):
        super().__init__(name=name, is_leader=is_leader, on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        if message.type == MessageType.MESSAGE:
            dt = bytes(message.data)
            print(self.id(), self.name(), dt.decode("utf-8"), message.originator_id, message.originator)
        # message = json.loads(str(message, "utf-8"))
        # if message and message.get("type") == "Message":
        #     print(self.name(), message["from"])
        #     if self.name() == message["from"]:
        #         print("Invalid message")
        #     # print(f" {self.name()} test {data}")

    async def run(self, inputs):
        print(f"{self.name()} run", inputs)
        while True:
            await self.broadcast(bytes("Hi from " + self.name() + " at " + str(time.time()), "utf-8"))
            # print(f"{self.name()} Broadcast message")
            await asyncio.sleep(random.randint(1, 5))


#
async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(Agent(name="ceylon-ai-1", is_leader=True, ))
    runner.register_agent(Agent(name="ceylon-ai-2", is_leader=False, ))
    runner.register_agent(Agent(name="ceylon-ai-3", is_leader=False, ))
    runner.register_agent(Agent(name="ceylon-ai-4", is_leader=False, ))

    await runner.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
