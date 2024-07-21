import asyncio
import pickle
import random
from collections import deque
from typing import List

import networkx as nx
from langchain_core.tools import StructuredTool, BaseTool
from pydantic.dataclasses import dataclass

from ceylon.ceylon import AgentCore, Processor, MessageHandler, AgentDefinition
from ceylon.llm.llm_caller import process_agent_request
from ceylon.runner import RunnerInput


@dataclass
class LLMAgentResponse:
    agent_id: str
    agent_name: str
    response: str


class LLMAgent(AgentCore, MessageHandler, Processor):
    tools: list[StructuredTool]
    network_graph: nx.DiGraph
    network_graph_original: nx.DiGraph
    queue: deque
    original_goal = None

    agent_replies: List[LLMAgentResponse] = []

    def __init__(self, name, position, instructions, responsibilities, llm, tools: list[BaseTool] = None):
        super().__init__(definition=AgentDefinition(
            name=name,
            position=position,
            instructions=instructions,
            responsibilities=responsibilities
        ), on_message=self, processor=self)
        self.llm = llm
        self.tools = tools
        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()

        # Initialize the queue and executed agents
        self.queue = deque()

    async def on_message(self, agent_id, data, time):
        definition = await self.definition()
        dt: LLMAgentResponse = pickle.loads(data)
        print(f"{definition.name} Received message from = '{dt.agent_name}")

        next_agent = self.get_next_agent()
        if next_agent == dt.agent_name:
            self.agent_replies.append(dt)
            await self.update_status(dt.agent_name)

        next_agent = self.get_next_agent()
        if next_agent == definition.name:
            dependencies = list(self.network_graph_original.predecessors(next_agent))
            print("Dependencies are:", dependencies, "for", next_agent)

            only_dependencies = {dt.agent_name: dt for dt in self.agent_replies if dt.agent_name in dependencies}

            if len(only_dependencies) == len(dependencies):
                print("Executing", definition.name)
                await self.execute(self.original_goal)

            await self.execute({
                "original_request": self.original_goal,
                **only_dependencies,
                dt.agent_name: dt.response
            })

    async def run(self, inputs):
        inputs: RunnerInput = pickle.loads(inputs)
        self._initialize_graph(inputs.network)

        self.original_goal = inputs.request

        await self.execute(inputs.request)


        await self.stop()

    def _initialize_graph(self, network):
        # Add nodes and edges based on the agents and their dependencies
        for agent, dependencies in network.items():
            print(agent)
            self.network_graph.add_node(agent)
            for dependency in dependencies:
                self.network_graph.add_edge(dependency, agent)

        self.network_graph_original = self.network_graph.copy()

        # Initialize the queue with nodes that have no dependencies (indegree 0)
        self.queue.extend([node for node in self.network_graph if self.network_graph.in_degree(node) == 0])



    def get_next_agent(self):
        if not self.queue:
            print("No more agents to execute.")
            return None
        return self.queue[0]

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

    async def update_status(self, agent):
        if agent not in self.queue:
            print(f"Agent {agent} is not ready to execute or has already been executed.")
            return

        self.queue.remove(agent)
        print(f"Executing {agent}")

        # Remove the current agent and update the graph
        for successor in list(self.network_graph.successors(agent)):
            self.network_graph.remove_edge(agent, successor)
            if self.network_graph.in_degree(successor) == 0:
                self.queue.append(successor)
        self.network_graph.remove_node(agent)

        if not self.network_graph.nodes:
            print("Workflow executed successfully.")
            await self.stop()
        elif not self.queue:
            print("Cycle detected in the workflow!")

