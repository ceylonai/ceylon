import pickle
from collections import deque

import networkx as nx
from langchain_core.tools import StructuredTool

from ceylon.ceylon import AgentCore, Processor, MessageHandler, AgentDefinition
from ceylon.runner import RunnerInput


class LLMAgent(AgentCore, MessageHandler, Processor):
    tools: list[StructuredTool]
    network_graph: nx.DiGraph
    queue: deque

    def __init__(self, name, position, instructions, responsibilities, llm, tools: list[StructuredTool] = None):
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
        dt = pickle.loads(data)
        print(definition.id, agent_id, dt, time)

    async def run(self, inputs):
        inputs: RunnerInput = pickle.loads(inputs)
        definition = await self.definition()

        print(f"Agent {definition.name} run", inputs)

        self._initialize_graph(inputs.network)

    def _initialize_graph(self, network):
        # Add nodes and edges based on the agents and their dependencies
        for agent, dependencies in network.items():
            self.network_graph.add_node(agent)
            for dependency in dependencies:
                self.network_graph.add_edge(dependency, agent)

        # Initialize the queue with nodes that have no dependencies (indegree 0)
        self.queue.extend([node for node in self.network_graph if self.network_graph.in_degree(node) == 0])

        print(self.queue)

    # def update_status(self, agent):
    #     if agent not in self.queue:
    #         print(f"Agent {agent} is not ready to execute or has already been executed.")
    #         return
    #
    #     self.queue.remove(agent)
    #     self.executed.append(agent)
    #     print(f"Executing {agent}")
    #
    #     # Remove the current agent and update the graph
    #     for successor in list(self.network_graph.successors(agent)):
    #         self.network_graph.remove_edge(agent, successor)
    #         if self.network_graph.in_degree(successor) == 0:
    #             self.queue.append(successor)
    #     self.network_graph.remove_node(agent)
    #
    #     if not self.network_graph.nodes:
    #         print("Workflow executed successfully.")
    #     elif not self.queue:
    #         print("Cycle detected in the workflow!")
