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

    async def on_agent(self, agent: AgentDefinition):
        self.log(f"{self.definition().name} on_agent {agent.name}")

    async def on_message(self, agent_id, message):
        self.log(f"on_message {agent_id} {message}")

    async def run(self, inputs):
        pass

    async def on_start(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
        # print(runner_input)

        network = runner_input.network

        # Create a directed graph to represent the workflow
        G = nx.DiGraph()

        # Add nodes and edges based on the agents and their dependencies
        for agent, dependencies in network.items():
            G.add_node(agent)
        for dependency in dependencies:
            G.add_edge(dependency, agent)

            # Function to execute the workflow in the correct order

        def execute_workflow(graph):
            # Find all nodes with no dependencies (indegree 0)
            queue = deque([node for node in graph if graph.in_degree(node) == 0])
            executed = []

            while queue:
                current_agent = queue.popleft()
                executed.append(current_agent)
                print(f"Executing {current_agent}")

                # Remove the current agent and update the graph
                for successor in list(graph.successors(current_agent)):
                    graph.remove_edge(current_agent, successor)
                    if graph.in_degree(successor) == 0:
                        queue.append(successor)
                graph.remove_node(current_agent)

            if graph.nodes:
                print("Cycle detected in the workflow!")
            else:
                print("Workflow executed successfully.")

        # Execute the workflow
        execute_workflow(G)
