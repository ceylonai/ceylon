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

from ceylon.ceylon import AgentDetail
from ceylon.llm.prompt_builder import get_agent_definition, get_prompt
from ceylon.llm.types import LLMAgentRequest, Job, LLMAgentResponse, AgentDefinition
from ceylon.workspace.admin import Admin
from ceylon.workspace.worker import Worker

workspace_id = "llm_unit"
admin_port = 8888
admin_peer = "admin"


class LLMAgent(Worker):

    def __init__(self, definition: AgentDefinition, tools: [BaseTool] = [], llm=None):
        self.definition = definition
        self.tools = tools
        self.llm = llm
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
                response_text = ""
                if self.tools and len(self.tools) > 0:
                    llm = self.llm.bind(functions=[format_tool_to_openai_function(t) for t in self.tools])
                    agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
                    executor = AgentExecutor(agent=agent, tools=self.tools, verbose=False)
                    llm_response = executor.invoke({})
                    response_text = llm_response["output"]
                else:
                    agent = prompt | self.llm
                    response = agent.invoke({})
                    response_text = response.content

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

    def __init__(self, name=workspace_id, port=admin_port):
        self.queue = deque()
        # Create a directed graph to represent the workflow
        self.network_graph = nx.DiGraph()
        self.agent_responses = []
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
            await self.execute()

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        data = pickle.loads(data)
        if type(data) == LLMAgentResponse:
            self.agent_responses.append(data)
            next_agent = self.get_next_agent()
            if next_agent == data.agent_name:
                self.queue.popleft()

            await self.execute()

    async def execute(self):
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
