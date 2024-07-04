import asyncio
import pickle
import random
from collections import deque
from typing import List

from langchain_core.tools import StructuredTool, BaseTool
from pydantic.dataclasses import dataclass

from ceylon.ceylon import AgentCore, Processor, MessageHandler, AgentDefinition, uniffi_set_event_loop
from ceylon.llm.llm_caller import process_agent_request
from ceylon.llm.task_manager import TaskManager
from ceylon.runner import RunnerInput


@dataclass
class LLMAgentResponse:
    agent_id: str
    agent_name: str
    response: str


class LLMAgent(AgentCore, MessageHandler, Processor):
    tools: list[StructuredTool]
    queue: deque
    original_goal = None

    agent_replies: List[LLMAgentResponse] = []

    task_manager = TaskManager()

    def __init__(self, name, position, instructions, responsibilities, llm, tools: list[BaseTool] = None):
        super().__init__(definition=AgentDefinition(
            name=name,
            position=position,
            instructions=instructions,
            responsibilities=responsibilities
        ), on_message=self, processor=self)
        self.llm = llm
        self.tools = tools

        # Initialize the queue and executed agents
        self.queue = deque()

    async def on_message(self, agent_id, data, time):
        definition = await self.definition()
        dt: LLMAgentResponse = pickle.loads(data)
        print(f"{definition.name} Received message from = '{dt.agent_name}")

        # next_agent = self.get_next_agent()
        # if next_agent == dt.agent_name:
        #     self.agent_replies.append(dt)
        #     await self.update_status(dt.agent_name)
        #
        # next_agent = self.get_next_agent()
        # if next_agent == definition.name:
        #     dependencies = list(self.network_graph_original.predecessors(next_agent))
        #     print("Dependencies are:", dependencies, "for", next_agent)
        #
        #     only_dependencies = {dt.agent_name: dt for dt in self.agent_replies if dt.agent_name in dependencies}
        #
        #     if len(only_dependencies) == len(dependencies):
        #         print("Executing", definition.name)
        #         await self.execute(self.original_goal)
        #
        #     await self.execute({
        #         "original_request": self.original_goal,
        #         **only_dependencies,
        #         dt.agent_name: dt.response
        #     })

    async def run(self, inputs):
        print(" Running LLMAgent")
        inputs: RunnerInput = pickle.loads(inputs)
        self.original_goal = inputs.request
        await self.stop()

    async def execute(self, input):
        definition = await self.definition()
        next_agent = self.get_next_agent()
        if next_agent == definition.name:
            print("Executing", definition.name)

            result = process_agent_request(self.llm, input, definition, tools=self.tools)
            # result = f"{definition.name} executed successfully"
            response = LLMAgentResponse(agent_id=definition.id, agent_name=definition.name, response=result)
            await asyncio.sleep(random.randint(1, 10))

            await self.broadcast(pickle.dumps(response))

            await self.update_status(next_agent)

            next_agent = self.get_next_agent()
            print("Next agent will be:", next_agent)
        else:
            print("Not executing", definition.name, "as it is not the next agent in the queue.")

    async def start(self, topic: "str", url: "str", inputs: "bytes") -> None:
        return await super().start(topic, url, inputs)
