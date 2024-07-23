import datetime
import pickle
from collections import deque
from typing import List

import networkx as nx
from langchain.prompts import Prompt
from langchain_core.tools import BaseTool

from ceylon.ceylon import AgentDetail
from ceylon.llm.llm.llm_executor import LLMExecutor
from ceylon.llm.llm_task_executor import execute_llm_with_function_calling, execute_llm
from ceylon.llm.prompt_builder import get_prompt
from ceylon.llm.types import LLMAgentRequest, LLMAgentResponse
from ceylon.llm.types.agent import AgentDefinition
from ceylon.llm.types.job import Job, JobWorker, JobSteps, JobStepsV1, Step
from ceylon.llm.types.step import StepExecution
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker

workspace_id = "llm_unit"
admin_port = 8888
admin_peer = "admin"


class LLMAgent(Worker):

    def __init__(self, definition: AgentDefinition, tools: [BaseTool] = [], tool_llm=None):
        self.definition = definition
        self.tools = tools
        self.llm = tool_llm
        super().__init__(
            name=definition.name,
            workspace_id=workspace_id,
            admin_port=admin_port,
            admin_peer=admin_peer,
            role=definition.role
        )

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == LLMAgentRequest:
            request: LLMAgentRequest = data
            if request.name == self.definition.name:
                definition = self.definition
                definition.tools = [tool.name for tool in self.tools if isinstance(tool, BaseTool)]

                print(" Executing", request.job_explanation)

                agent_intro = definition.prompt

                step_exc = StepExecution(
                    worker=self.definition,
                    explanation=request.job_explanation,
                    dependencies=[]
                )
                executor = LLMExecutor(llm=self.llm, type="llm_executor")
                res = executor.execute(step_exc.prompt)
                print(res)

                print(agent_intro)

                # agent_definition_prompt = self.definition.prompt
                # prompt_value = get_prompt({
                #     "user_inputs": request.user_inputs,
                #     "agent_definition": agent_definition_prompt,
                #     "history": request.history
                # })
                # prompt = Prompt(template=prompt_value)
                # if self.tools and len(self.tools) > 0:
                #     response_text = execute_llm_with_function_calling(self.llm, prompt, self.tools)
                # else:
                #     response_text = execute_llm(self.llm, prompt)
                #
                # response = LLMAgentResponse(
                #     time=datetime.datetime.now().timestamp(),
                #     agent_id=self.details().id,
                #     agent_name=self.details().name,
                #     response=response_text
                # )
                # await self.broadcast(pickle.dumps(response))


class ChiefAgent(Admin):
    job: Job
    network_graph: nx.DiGraph
    network_graph_original: nx.DiGraph
    queue: deque

    agent_responses: List[LLMAgentResponse] = []

    def __init__(self, name=workspace_id, port=admin_port, workers=[], tool_llm=None):
        self.queue = deque()
        self.llm = tool_llm
        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()
        self.agent_responses = []
        self.workers = workers
        super().__init__(name, port)

    async def run(self, inputs: "bytes"):
        self.job: Job = pickle.loads(inputs)
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

        # # Example usage of the queue
        # while self.queue:
        #     task = dependency_queue.popleft()
        #     print(f"Processing task {task}")

    def get_next_agent(self):
        if not self.queue:
            return None
        next_agent = self.queue[0]
        print("Next agent is", next_agent)
        return next_agent

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        next_agent = self.get_next_agent()
        if next_agent == agent.name:
            await self.execute_request()

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == LLMAgentResponse:
            self.agent_responses.append(data)
            next_agent = self.get_next_agent()
            if next_agent == data.agent_name:
                self.queue.popleft()

            await self.execute_request()

    async def execute_request(self):
        next_agent = self.get_next_agent()
        print("Executing", next_agent)
        if next_agent:
            dependencies = list(self.network_graph_original.predecessors(next_agent))
            only_dependencies = {dt.agent_name: dt.response for dt in self.agent_responses if
                                 dt.agent_name in dependencies}

            if len(only_dependencies) == len(dependencies):
                await self.broadcast(pickle.dumps(
                    LLMAgentRequest(name=next_agent,
                                    job_explanation=self.job.explanation,
                                    history=only_dependencies),
                ))
        else:
            last_response = self.agent_responses[-1]
            self.return_response = last_response.response
            await self.stop()

    def execute(self, job: Job):
        self.job = job
        self.job.workers = [JobWorker.from_agent_definition(worker.definition) for worker in self.workers]
        if job.steps is None or job.steps.steps is None or len(job.steps.steps) == 0:
            executor = LLMExecutor(llm=self.llm, type="llm_executor")
            self.job.steps = executor.execute(job.prompt_planning)
            if self.job.steps is None or len(self.job.steps.steps) == 0:
                self.job.steps = JobSteps(steps=[
                    Step(
                        worker=worker.definition.name,
                        dependencies=[],
                        explanation=f"Follow the role description and expectation {job.explanation}",
                    )
                    for worker in self.workers
                ])
        return self.run_admin(pickle.dumps(job), self.workers)
