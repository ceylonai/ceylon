import enum
import pickle
import uuid
from collections import deque
from typing import List, Any, Optional, Callable, Awaitable

import networkx as nx
from pydantic import BaseModel, Field, PrivateAttr

from ceylon.agent.types.agent_request import AgentJobResponse, AgentJobStepRequest
from ceylon.ceylon import AgentDetail
from .job_step import Step




class JobSteps(BaseModel):
    '''the steps of the job'''
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id')
    steps: List[Step] = Field(description="the steps of the job", default=[])

    def step(self, worker: str):
        '''get the next step of the job'''
        for step in self.steps:
            if step.worker == worker:
                return step
        return None


class JobStatus(enum.Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobRequestResponse(BaseModel):
    job_id: str = Field(None, description="the job id")
    status: JobStatus = Field(JobStatus.RUNNING, description="the status of the job")
    data: Any = Field(None, description="the data of the job")


class JobRequest(BaseModel):
    title: str = Field(description="the name of the job")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id')
    steps: JobSteps = Field(description="the steps of the job", default=JobSteps(steps=[]))

    on_success_callback: Optional[Callable[[JobRequestResponse, 'JobRequest'], Awaitable[None]]] = Field(default=None)
    on_failure_callback: Optional[Callable[[JobRequestResponse, 'JobRequest'], Awaitable[None]]] = Field(default=None)

    current_status: JobStatus = Field(JobStatus.IDLE, description="the current status of the job")

    _network_graph: nx.DiGraph = PrivateAttr(default=nx.DiGraph())
    _network_graph_original: nx.DiGraph = PrivateAttr(default=nx.DiGraph())
    _queue: deque = PrivateAttr(default=deque([]))

    _agent_responses: List[AgentJobResponse] = PrivateAttr(default=[])

    result: Any = Field(None, description="the result of the job")
    job_data: Any = Field(None, description="the job data")

    class Config:
        arbitrary_types_allowed = True

    def initialize_graph(self):
        for step in self.steps.steps:
            self._network_graph.add_node(step.worker)
            for dep in step.dependencies:
                self._network_graph.add_edge(dep, step.worker)
        self._network_graph_original = self._network_graph.copy()
        if not nx.is_directed_acyclic_graph(self._network_graph):
            raise ValueError("Job steps contain cycles")

        for layer in nx.topological_generations(self._network_graph):
            self._queue.append(layer)

    def get_next_agents(self):
        if not self._queue:
            return None
        next_agents = self._queue[0]
        # print(self.id, self.title
        #       , "Next agent is", next_agents)
        return next_agents

    async def execute_request(self, data: AgentJobResponse = None, broadcaster=None):
        if data:
            self._agent_responses.append(data)
            next_agents = self.get_next_agents()
            for next_agent in next_agents:
                if next_agent == data.worker:
                    next_agents.remove(next_agent)
            if len(next_agents) == 0:
                self._queue.popleft()

        next_agents = self.get_next_agents()
        if next_agents:
            for next_agent in next_agents:
                # print(self.id, self.title, "Next agent", next_agent)
                dependencies = list(self._network_graph_original.predecessors(next_agent))
                only_dependencies = {dt.worker: dt.job_data for dt in self._agent_responses if
                                     dt.worker in dependencies}
                if len(only_dependencies) == len(dependencies):
                    await broadcaster(pickle.dumps(
                        AgentJobStepRequest(worker=next_agent, job_data=self.job_data, job_id=self.id,
                                            step=self.steps.step(next_agent)),
                    ))
        else:
            last_response = self._agent_responses[-1]
            if self.on_success_callback:
                await self.on_success_callback(
                    JobRequestResponse(job_id=self.id, status=JobStatus.COMPLETED, data=last_response.job_data), self)
            self.result = last_response
            return JobRequestResponse(job_id=self.id, status=JobStatus.COMPLETED, data=last_response.job_data)

    async def on_agent_connected(self, topic: "str", agent: AgentDetail, broadcaster=None):
        next_agents = self.get_next_agents()
        for next_agent in next_agents:
            if next_agent == agent.name and self.current_status == JobStatus.IDLE:
                self.current_status = JobStatus.RUNNING
            await self.execute_request(None, broadcaster)

    def show_graph(self):
        import matplotlib.pyplot as plt
        nx.draw(self._network_graph, with_labels=True)
        plt.show()

    def __str__(self):
        return f"Job {self.id}: {self.title} with {len(self.steps.steps)} steps"
