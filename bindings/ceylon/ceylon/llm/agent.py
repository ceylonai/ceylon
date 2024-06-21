import pickle
from collections import deque
from typing import Dict
import networkx as nx
from langchain_core.tools import StructuredTool

from ceylon.ceylon import AgentCore, MessageHandler, AgentHandler, AgentDefinition, AgentConfig, Processor
from ceylon.runner import RunnerInput


class LLMAgent(AgentCore, MessageHandler, AgentHandler, Processor):
    tools: list[StructuredTool]
    joined_team: Dict[str, AgentCore]
    network_graph: nx.DiGraph
    queue: deque
    executed: list

    async def on_start(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        network = runner_input.network
        self._initialize_graph(network)

    def _initialize_graph(self, network):
        # Add nodes and edges based on the agents and their dependencies
        for agent, dependencies in network.items():
            self.network_graph.add_node(agent)
            for dependency in dependencies:
                self.network_graph.add_edge(dependency, agent)

        # Initialize the queue with nodes that have no dependencies (indegree 0)
        self.queue.extend([node for node in self.network_graph if self.network_graph.in_degree(node) == 0])

    def get_next_agent(self):
        if not self.queue:
            print("No more agents to execute.")
            return None
        return self.queue[0]

    def update_status(self, agent):
        if agent not in self.queue:
            print(f"Agent {agent} is not ready to execute or has already been executed.")
            return

        self.queue.remove(agent)
        self.executed.append(agent)
        print(f"Executing {agent}")

        # Remove the current agent and update the graph
        for successor in list(self.network_graph.successors(agent)):
            self.network_graph.remove_edge(agent, successor)
            if self.network_graph.in_degree(successor) == 0:
                self.queue.append(successor)
        self.network_graph.remove_node(agent)

        if not self.network_graph.nodes:
            print("Workflow executed successfully.")
        elif not self.queue:
            print("Cycle detected in the workflow!")

    def get_executed(self):
        return self.executed

    def __init__(self, name, position, llm, responsibilities=None, instructions=None, tools=None):
        if responsibilities is None:
            responsibilities = []
        if instructions is None:
            instructions = []
        if tools is None:
            tools = []
        self.tools = tools
        self.llm = llm
        super().__init__(definition=AgentDefinition(
            id=None,
            name=name,
            responsibilities=responsibilities,
            position=position,
            is_leader=False,
            instructions=instructions
        ),
            config=AgentConfig(memory_context_size=10),
            agent_handler=self,
            on_message=self, processor=self, meta=None, event_handlers={})

        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()

        # Initialize the queue and executed agents
        self.queue = deque()
        self.executed = []

    async def on_agent(self, agent: AgentDefinition):
        self.log(f"{self.definition().name} on_agent {agent.name}")

        # Manually check the next agent to execute
        next_agent = self.get_next_agent()
        if next_agent:
            print(f"Next agent to execute: {next_agent}")

            # Manually update the status of the next agent
        #     self.update_status(next_agent)
        #
        # print("Executed agents:", self.get_executed())

    async def on_message(self, agent_id, message):
        self.log(f"on_message {agent_id} {message}")

    async def run(self, inputs):
        pass
