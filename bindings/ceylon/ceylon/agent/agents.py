import datetime
import pickle
from collections import deque
from typing import List

import networkx as nx
from langchain_core.tools import BaseTool

from ceylon.agent.types.agent_request import AgentJobStepRequest, AgentJobResponse
from ceylon.agent.types.job import JobRequest
from ceylon.ceylon import AgentDetail
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker

workspace_id = "llm_unit"
admin_port = 8888
admin_peer = "admin"


class Agent(Worker):

    def __init__(self, name: str, role: str):
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_port=admin_port,
            admin_peer=admin_peer,
            role=role
        )

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == AgentJobStepRequest:
            request: AgentJobStepRequest = data
            if request.worker == self.details().name:
                response = await self.execute_request(request)
                await self.broadcast(pickle.dumps(response))

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        raise NotImplemented


class RunnerAgent(Admin):
    job: JobRequest
    network_graph: nx.DiGraph
    network_graph_original: nx.DiGraph
    queue: deque

    agent_responses: List[AgentJobResponse] = []

    def __init__(self, name=workspace_id, port=admin_port, workers=[], tool_llm=None):
        self.queue = deque()
        self.llm = tool_llm
        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()
        self.agent_responses = []
        self.workers = workers
        super().__init__(name, port)

    async def run(self, inputs: "bytes"):
        self.job: JobRequest = pickle.loads(inputs)
        # Create a directed graph
        self._initialize_graph()

    def _initialize_graph(self):
        print("Initializing graph", self.job.steps.steps)
        for step in self.job.steps.steps:
            self.network_graph.add_node(step.worker)
            for dependency in step.dependencies:
                self.network_graph.add_edge(dependency, step.worker)

        self.network_graph_original = self.network_graph.copy()
        topological_order = list(nx.topological_sort(self.network_graph))

        # Convert the sorted list into a queue
        self.queue = deque(topological_order)

        # Print the queue
        print("Order of tasks considering dependencies:")
        print(self.queue)

    def get_next_agent(self):
        if not self.queue:
            return None
        next_agent = self.queue[0]
        print("Next agent is", next_agent)
        return next_agent

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        next_agent = self.get_next_agent()
        if next_agent == agent.name:
            await self._execute_request()

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == AgentJobResponse:
            data: AgentJobResponse = data
            self.agent_responses.append(data)
            next_agent = self.get_next_agent()
            if next_agent == data.worker:
                self.queue.popleft()

            await self._execute_request()

    async def _execute_request(self):
        next_agent = self.get_next_agent()
        if next_agent:
            next_step = self.job.steps.step(next_agent)
            dependencies = list(self.network_graph_original.predecessors(next_agent))
            only_dependencies = {dt.worker: dt.job_data for dt in self.agent_responses if
                                 dt.worker in dependencies}
            if len(only_dependencies) == len(dependencies):
                await self.broadcast(pickle.dumps(
                    AgentJobStepRequest(worker=next_agent, job_data={})
                ))
        else:
            last_response = self.agent_responses[-1]
            self.return_response = last_response.job_data
            await self.stop()

    def execute(self, job: JobRequest):
        return self.run_admin(pickle.dumps(job), self.workers)
