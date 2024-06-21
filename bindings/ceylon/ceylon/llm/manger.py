import pickle
from collections import deque

import networkx as nx
from pydantic import BaseModel

from ceylon.ceylon import AgentCore, MessageHandler, Processor, AgentDefinition, AgentConfig, \
    AgentHandler, EventHandler
from ceylon.runner import RunnerInput


class OtherAgent(BaseModel):
    definition: AgentDefinition
    is_connected: bool

    class Config:
        arbitrary_types_allowed = True


class LLMManager(AgentCore, MessageHandler, Processor, AgentHandler):
    connected_agents = []

    class OnAnyEvent(EventHandler):
        async def on_event(self, message):
            print(f"on_any_event {message}")

    def __init__(self, llm, name="leader"):
        self.llm = llm
        super().__init__(
            definition=AgentDefinition(id=None, name=name,
                                       is_leader=True,
                                       position="LEADER",
                                       responsibilities=[
                                           "With inputs you need to select next agent or agents to send the message",
                                       ],
                                       instructions=[
                                           "Select next agent or agents to send the message"
                                       ]),
            config=AgentConfig(memory_context_size=10),
            on_message=self,
            processor=self, meta={},
            agent_handler=self,
            event_handlers={
                # EventType.ON_ANY: [self.OnAnyEvent()]
            })
        self.connected_agents = []

    async def on_agent(self, agent: "AgentDefinition"):
        print(f"{self.definition().name} on_agent {agent.name}")

    async def on_message(self, agent_id, message):
        pass

    async def run(self, inputs):
        runner_input: RunnerInput = pickle.loads(inputs)
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
