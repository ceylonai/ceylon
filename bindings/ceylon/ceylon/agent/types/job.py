import enum
import pickle
import uuid
from collections import deque
from typing import List, Any, Optional, Callable, Awaitable

import networkx as nx
from pydantic import BaseModel, Field, PrivateAttr

from ceylon.agent.types.agent_request import AgentJobResponse, AgentJobStepRequest
from ceylon.ceylon import AgentDetail


class Step(BaseModel):
    '''the step'''
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id')
    worker: str = Field(description="the worker name of the step")
    dependencies: List[str] = Field(description="the dependencies of the step, these steps must be another step worker",
                                    default=[])
    explanation: str = Field(description="the explanation of the step", default="")

    class Config:
        arbitrary_types_allowed = True


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

    on_success_callback: Optional[Callable[[JobRequestResponse], Awaitable[None]]] = Field(default=None)
    on_failure_callback: Optional[Callable[[JobRequestResponse], Awaitable[None]]] = Field(default=None)

    current_status: JobStatus = Field(JobStatus.IDLE, description="the current status of the job")

    _network_graph: nx.DiGraph = PrivateAttr(default=nx.DiGraph())
    _network_graph_original: nx.DiGraph = PrivateAttr(default=nx.DiGraph())
    _queue: deque = PrivateAttr(default=deque([]))

    _agent_responses: List[AgentJobResponse] = PrivateAttr(default=[])

    class Config:
        arbitrary_types_allowed = True

    def initialize_graph(self):
        print(self.id, self.title, "Initializing graph", self.steps.steps)
        for step in self.steps.steps:
            self._network_graph.add_node(step.worker)
            for dependency in step.dependencies:
                self._network_graph.add_edge(dependency, step.worker)

        self._network_graph_original = self._network_graph.copy()
        topological_order = list(nx.topological_sort(self._network_graph))

        # Convert the sorted list into a queue
        self._queue = deque(topological_order)

        # Print the queue
        print(self.id, self.title
              , f"Order of tasks considering dependencies: {self.id}")
        print(self._queue)

    def get_next_agent(self):
        if not self._queue:
            return None
        next_agent = self._queue[0]
        print(self.id, self.title
              , "Next agent is", next_agent)
        return next_agent

    async def execute_request(self, data: AgentJobResponse = None, broadcaster=None):
        if data:
            self._agent_responses.append(data)
            next_agent = self.get_next_agent()
            if next_agent == data.worker:
                self._queue.popleft()

        next_agent = self.get_next_agent()
        if next_agent:
            dependencies = list(self._network_graph_original.predecessors(next_agent))
            only_dependencies = {dt.worker: dt.job_data for dt in self._agent_responses if
                                 dt.worker in dependencies}
            if len(only_dependencies) == len(dependencies):
                await broadcaster(pickle.dumps(
                    AgentJobStepRequest(worker=next_agent, job_data={}, job_id=self.id)
                ))
        else:
            last_response = self._agent_responses[-1]
            print(self.id, self.title, "Last response", last_response)
            await self.on_success_callback(
                JobRequestResponse(job_id=self.id, status=JobStatus.COMPLETED, data=last_response.job_data))
            return JobRequestResponse(job_id=self.id, status=JobStatus.COMPLETED, data=last_response.job_data)

    async def on_agent_connected(self, topic: "str", agent: AgentDetail, broadcaster=None):
        next_agent = self.get_next_agent()
        if next_agent == agent.name and self.current_status == JobStatus.IDLE:
            self.current_status = JobStatus.RUNNING
            await self.execute_request(None, broadcaster)
