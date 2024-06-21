import pickle
from collections import deque
from typing import Dict
import networkx as nx
from langchain_core.tools import StructuredTool
from pydantic import dataclasses

from ceylon.ceylon import AgentCore, MessageHandler, AgentHandler, AgentDefinition, AgentConfig, Processor
from ceylon.llm.llm_caller import process_agent_request
from ceylon.runner import RunnerInput


@dataclasses.dataclass
class AgentMessage:
    agent: str
    response: str


class LLMAgent(AgentCore, MessageHandler, AgentHandler, Processor):
    tools: list[StructuredTool]
    neighbour_agents: Dict[str, AgentDefinition]
    joined_team: Dict[str, AgentDefinition]
    network_graph: nx.DiGraph
    queue: deque
    executed: list
    input: RunnerInput

    async def on_start(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        network = runner_input.network
        for agent in runner_input.agents:
            self.neighbour_agents[agent.name] = agent
        self._initialize_graph(network)
        self.joined_team[self.definition().name] = self.definition()

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

    def __init__(self, name, position, llm, responsibilities=None, instructions=None, tools=None, is_leader=False):
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
            is_leader=is_leader,
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
        self.joined_team = {}
        self.neighbour_agents = {}

    async def on_agent(self, agent: AgentDefinition):
        self.log(f"{self.definition().name} on_agent {agent.name}")
        self.joined_team[agent.name] = agent
        # If all agents have joined, execute the workflow
        if len(self.joined_team) == len(self.neighbour_agents):
            next_agent = self.get_next_agent()
            if next_agent == self.definition().name:
                self.log(
                    f"Next agent to execute: {next_agent} {self.definition().name} {next_agent == self.definition().name}")
                self.log(f"Running {self.definition().name} My self")
                response = process_agent_request(self.llm, self.input.request, self.definition(),
                                                 tools=self.tools)
                # response = "Test response"
                agent_task_response = AgentMessage(
                    agent=self.definition().name,
                    response=response
                )
                await self.broadcast(pickle.dumps(agent_task_response), None)

    async def on_message(self, agent_id, message):
        print(f"{self.definition().id} Received message from = '{agent_id}' message= {message}")
        # message: AgentMessage = pickle.loads(message)
        # print(f"{self.definition().name} Received message from = '{agent_id}' message= {message}")
        # self.log(f"{self.definition().name} Received message from = '{agent_id}' message= {message}")
        # # Manually check the next agent to execute
        # next_agent = self.get_next_agent()
        # if next_agent:
        #     print(f"Next agent to execute: {next_agent}")

    async def run(self, inputs):
        self.input: RunnerInput = pickle.loads(inputs)
