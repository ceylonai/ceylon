import asyncio
import pickle
import random

from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentDefinition
from ceylon.runner import AgentRunner


class Agent(AgentCore, MessageHandler, Processor):
    def __init__(self, name, position, instructions, responsibilities):
        super().__init__(definition=AgentDefinition(
            id=None,
            name=name,
            position=position,
            instructions=instructions,
            responsibilities=responsibilities
        ), on_message=self, processor=self)

    async def on_message(self, agent_id, data, time):
        definition = await self.definition()
        dt = pickle.loads(data)
        print(definition.id, agent_id, dt, time)

        ## Write to txt file
        # with open(f"test_{name}.txt", "a") as f:
        #     f.write(dt.decode("utf-8") + "\n")

    async def run(self, inputs):
        definition = await self.definition()
        while True:
            await self.broadcast(pickle.dumps({
                "title": "How to use AI for Machine Learning",
                "sender": definition.name
            }))
            await asyncio.sleep(random.randint(1, 10))


#
async def main():
    runner = AgentRunner(workspace_name="ceylon-ai")
    runner.register_agent(Agent(name="ceylon-ai-1",
                                responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"],
                                position="leader"))
    runner.register_agent(Agent(name="ceylon-ai-2", responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"], position="leader"))
    runner.register_agent(Agent(name="ceylon-ai-3", responsibilities=["writer", "researcher"],
                                instructions=["How to use AI for Machine Learning"], position="leader"))

    for i in range(4, 5):
        runner.register_agent(Agent(name=f"ceylon-ai-{i}", responsibilities=["writer", "researcher"],
                                    instructions=["How to use AI for Machine Learning"], position="leader"))

    await runner.run({
        "title": "How to use AI for Machine Learning",
    })


if __name__ == '__main__':
    asyncio.run(main())
