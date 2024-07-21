import datetime
import pickle
from collections import deque
from typing import List

import networkx as nx
from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import Prompt
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import format_tool_to_openai_function
from langchain_experimental.llms.ollama_functions import convert_to_ollama_tool
from pydantic.v1 import BaseModel

from ceylon.ceylon import AgentDetail
from ceylon.llm.llm_task_executor import execute_llm_with_function_calling, execute_llm, execute_llm_with_json_out
from ceylon.llm.prompt_builder import get_agent_definition, get_prompt, job_planing_prompt
from ceylon.llm.types import LLMAgentRequest, Job, LLMAgentResponse, AgentDefinition, Step
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
                agent_definition_prompt = get_agent_definition(self.definition)
                prompt_value = get_prompt({
                    "user_inputs": request.user_inputs,
                    "agent_definition": agent_definition_prompt,
                    "history": request.history
                })
                prompt = Prompt(template=prompt_value)
                if self.tools and len(self.tools) > 0:
                    response_text = execute_llm_with_function_calling(self.llm, prompt, self.tools)
                else:
                    response_text = execute_llm(self.llm, prompt)

                response = LLMAgentResponse(
                    time=datetime.datetime.now().timestamp(),
                    agent_id=self.details().id,
                    agent_name=self.details().name,
                    response=response_text
                )
                await self.broadcast(pickle.dumps(response))


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
        for step in self.job.work_order:
            self.network_graph.add_node(step.owner)
            for dependency in step.dependencies:
                self.network_graph.add_edge(dependency, step.owner)

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
                                    user_inputs=self.job.input,
                                    history=only_dependencies),
                ))
        else:
            last_response = self.agent_responses[-1]
            self.return_response = last_response.response
            await self.stop()

    def execute(self, job: Job):
        if job.build_workflow:
            worker_summary = [worker.definition.intro for worker in self.workers]
            prompt_txt = job_planing_prompt({
                "job": job.input,
                "workers": worker_summary
            })

            class JobSteps(BaseModel):
                '''the steps of the job'''
                steps: List[Step]

            res = execute_llm_with_json_out(self.llm, prompt_txt, JobSteps)
            if res is not None:
                job.work_order = res.steps
            else:
                raise Exception("Failed to build workflow")
        return self.run_admin(pickle.dumps(job), self.workers)
