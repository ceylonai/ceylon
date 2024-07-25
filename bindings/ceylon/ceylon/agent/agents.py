import pickle
from collections import deque
from typing import List

import networkx as nx

from ceylon.agent.types.agent_request import AgentJobStepRequest, AgentJobResponse
from ceylon.agent.types.job import JobRequest, JobStatus
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
                response.job_id = request.job_id
                await self.broadcast(pickle.dumps(response))

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        raise NotImplemented


class RunnerAgent(Admin):
    jobs: List[JobRequest] = []

    def __init__(self, name=workspace_id, port=admin_port, workers=[], tool_llm=None):
        self.queue = deque()
        self.llm = tool_llm
        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()
        self.agent_responses = []
        self.workers = workers
        super().__init__(name, port)

    async def run(self, inputs: "bytes"):
        job: JobRequest = pickle.loads(inputs)
        job.initialize_graph()
        self.jobs.append(job)

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        for job in self.jobs:
            await job.on_agent_connected(topic, agent, self.broadcast)

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == AgentJobResponse:
            data: AgentJobResponse = data
            job = self.get_job_by_id(data.job_id)
            if job:
                res = await job.execute_request(data, self.broadcast)
                if res is not None and res.status == JobStatus.COMPLETED:
                    self.jobs.remove(job)
        if len(self.jobs) == 0:
            await self.stop()

    def get_job_by_id(self, job_id: str):
        for job in self.jobs:
            if job.id == job_id:
                return job

    def execute(self, job: JobRequest):
        return self.run_admin(pickle.dumps(job), self.workers)
