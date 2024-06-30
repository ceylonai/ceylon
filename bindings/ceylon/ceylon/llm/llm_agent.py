import asyncio
import pickle
import random

from langchain_core.tools import StructuredTool

from ceylon.ceylon import AgentCore, Processor, MessageHandler, AgentDefinition


class LLMAgent(AgentCore, MessageHandler, Processor):
    tools: list[StructuredTool]

    def __init__(self, name, position, instructions, responsibilities, llm, tools: list[StructuredTool] = None):
        self.llm = llm
        self.tools = tools
        super().__init__(definition=AgentDefinition(
            name=name,
            position=position,
            instructions=instructions,
            responsibilities=responsibilities
        ), on_message=self, processor=self)

    async def on_message(self, agent_id, data, time):
        definition = await self.definition()
        dt = pickle.loads(data)
        print(definition.id, agent_id, dt, time)

    async def run(self, inputs):
        definition = await self.definition()
        print(f"{definition.name} run", inputs)
        while True:
            await self.broadcast(pickle.dumps({
                "title": "How to use AI for Machine Learning",
                "sender": definition.name
            }))
            await asyncio.sleep(random.randint(1, 10))
