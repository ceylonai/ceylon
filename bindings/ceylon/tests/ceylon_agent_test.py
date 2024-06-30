import asyncio
import random
import time

from ceylon.ceylon import AgentCore, MessageHandler, Processor, MessageType, AgentDefinition
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, position, is_leader, instructions, responsibilities):
        super().__init__(definition=AgentDefinition(
            id=None,
            is_leader=is_leader,
            name=name,
            position=position,
            instructions=instructions,
            responsibilities=responsibilities
        ), on_message=self, processor=self)

    async def on_message(self, agent_id, message):
        definition = await self.definition()
        name = definition.name
        id = definition.id
        print(f"{name} on_message", agent_id, message)
        if message.type == MessageType.MESSAGE:
            dt = bytes(message.data)
            print(id, name, dt.decode("utf-8"), message.originator_id, message.originator)

            ## Write to txt file
            with open(f"test_{name}.txt", "a") as f:
                f.write(dt.decode("utf-8") + "\n")

    async def run(self, inputs):
        definition = await self.definition()
        print(f"{definition.name} run", inputs)
        while True:
            await self.broadcast(bytes("Hi from " + definition.name + " at " + str(time.time()), "utf-8"))
            await asyncio.sleep(random.randint(1, 2))


#
async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(Agent(name="ceylon-ai-1", is_leader=True,
                                responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"],
                                position="leader"))
    runner.register_agent(Agent(name="ceylon-ai-2", is_leader=False, responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"], position="leader"))
    runner.register_agent(Agent(name="ceylon-ai-3", is_leader=False, responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"], position="leader"))

    for i in range(4, 50):
        runner.register_agent(Agent(name=f"ceylon-ai-{i}", is_leader=False, responsibilities=["writer", "researcher"],
                                    instructions=["How to use AI for Machine Learning"], position="leader"))

    await runner.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
