import asyncio
import datetime
import pickle
from collections import deque
from typing import List

import networkx as nx
from langchain.agents import AgentExecutor
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import Prompt
from langchain_community.chat_models import ChatOllama
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import format_tool_to_openai_function

from ceylon.ceylon import AgentDetail
from ceylon.llm.prompt_builder import get_agent_definition, get_prompt
from ceylon.llm.types import LLMAgentRequest, Job, LLMAgentResponse, AgentDefinition, Step
from ceylon.tools.search_tool import SearchTool
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
            print(request.name, self.definition.name)
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
                    llm = self.llm.bind(functions=[format_tool_to_openai_function(t) for t in self.tools])
                    agent = prompt | llm | OpenAIFunctionsAgentOutputParser()
                    executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
                    llm_response = executor.invoke({})
                    response = LLMAgentResponse(
                        time=datetime.datetime.now().timestamp(),
                        agent_id=self.details().id,
                        agent_name=self.details().name,
                        response=llm_response["output"]
                    )
                    await self.broadcast(pickle.dumps(response))
                else:
                    agent = prompt | self.llm
                    response = agent.invoke({})
                    print(response)


class ChiefAgent(Admin):
    job: Job
    network_graph: nx.DiGraph
    network_graph_original: nx.DiGraph
    queue: deque

    agent_responses: List[LLMAgentResponse] = []

    def __init__(self, name="admin", port=8888):
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
        # Initialize the queue with nodes that have no dependencies (indegree 0)
        self.queue.extend([node for node in self.network_graph if self.network_graph.in_degree(node) == 0])

    def get_next_agent(self):
        if not self.queue:
            print("No more agents to execute.")
            return None
        return self.queue[0]

    async def on_agent_connected(self, topic: "str", agent: AgentDetail):
        next_agent = self.get_next_agent()
        print(f"Agent {agent} connected to {topic} and is executing {next_agent}")
        if next_agent == agent.name:
            await self.broadcast(pickle.dumps(
                LLMAgentRequest(name=agent.name,
                                user_inputs=self.job.input, history=self.agent_responses),
            ))
            # self.queue.popleft()

    async def on_message(self, agent_id: "str", data: "bytes", time: "int"):
        print("Admin on_message", agent_id)
        data = pickle.loads(data)
        if type(data) == LLMAgentResponse:
            self.agent_responses.append(data)
            next_agent = self.get_next_agent()
            if next_agent == data.agent_name:
                self.queue.popleft()

            next_agent = self.get_next_agent()
            if next_agent:
                await self.broadcast(pickle.dumps(
                    LLMAgentRequest(name=next_agent,
                                    user_inputs=self.job.input,
                                    history=self.agent_responses),
                ))
            else:
                print("No more agents to execute.")
                last_response = self.agent_responses[-1]
                print(last_response.response)
                await self.stop()


async def main():
    llm_lib = ChatOllama(model="llama3:instruct")

    chief = ChiefAgent(
        name=workspace_id,
        port=admin_port,
    )

    writer = LLMAgent(
        AgentDefinition(
            name="writer",
            role="Creative AI Content Writer",
            role_description="""
                As AIStoryWeaver, your primary function is to transform complex AI and machine learning research 
                into captivating, accessible content. You excel at crafting engaging narratives that bridge the gap 
                between technical expertise and public understanding. Your writing should spark curiosity, 
                foster comprehension, and ignite imagination about the potential of AI technologies.
            """,
            responsibilities=[
                "Synthesize technical AI research into engaging, narrative-driven articles",
                "Translate complex concepts into relatable metaphors and real-world examples",
                "Craft compelling storylines that capture the essence of AI advancements",
                "Tailor content to appeal to readers with diverse levels of AI knowledge",
                "Infuse creativity and humor to make technical subjects more approachable",
                "Maintain scientific accuracy while prioritizing readability and engagement",
            ],
            skills=[
                "Creative writing and storytelling",
                "Simplification of technical concepts",
                "Audience-focused content creation",
                "Metaphor and analogy generation",
                "Narrative structure and pacing",
                "Balancing entertainment with educational value",
            ],
            tools=[
                "Metaphor generator",
                "Readability analysis tools",
                "Interactive storytelling frameworks",
                "Visual concept mapping software",
            ],
            knowledge_domains=[
                "Artificial Intelligence",
                "Machine Learning",
                "Natural Language Processing",
                "Data Science",
                "Technology Trends",
                "Science Communication",
            ],
            interaction_style="Friendly, engaging, and slightly whimsical. Use a conversational tone that invites curiosity and makes complex ideas feel accessible and exciting.",
            operational_parameters="""
                While creativity is encouraged, always prioritize accuracy in representing AI concepts. 
                Avoid oversimplification that could lead to misconceptions. When using analogies or 
                metaphors, clearly link them back to the original AI concepts. Encourage critical 
                thinking about the implications of AI technologies.
            """,
            performance_objectives=[
                "Increase reader engagement with AI topics",
                "Improve public understanding of complex AI concepts",
                "Generate shareable content that sparks discussions about AI",
                "Bridge the communication gap between AI researchers and the general public",
            ],
            version="2.0.0"
        ),
        llm=llm_lib
    )
    researcher = LLMAgent(
        AgentDefinition(
            name="researcher",
            role="AI and Machine Learning Research Specialist",
            role_description="Your role is to gather detailed and accurate information on how AI can be utilized in machine learning...",
            responsibilities=[
                "Conduct thorough research on AI applications in machine learning",
                "Gather detailed information from reputable academic and industry sources",
            ],
            skills=[
                "Advanced information retrieval and data mining",
                "Critical analysis of technical papers and reports",
            ],
            tools=[
                "Academic database access (e.g., arXiv, IEEE Xplore)",
                "Industry report aggregators",
            ],
            knowledge_domains=[
                "Artificial Intelligence",
                "Machine Learning Algorithms",
            ],
            interaction_style="Professional and analytical. Communicate findings clearly and objectively, with a focus on accuracy and relevance.",
            operational_parameters="Prioritize peer-reviewed sources and reputable industry reports...",
            performance_objectives=[
                "Provide comprehensive coverage of AI applications in machine learning",
                "Ensure all gathered information is current and accurately represented",
            ],
            version="2.0.0"
        ),
        tools=[SearchTool()],
        llm=llm_lib
    )

    job = Job(
        title="write_article",
        work_order=[
            Step(owner="researcher", dependencies=[]),
            Step(owner="writer", dependencies=["researcher"]),
        ],
        input={
            "title": "How to use AI for Machine Learning",
            "tone": "informal",
            "length": "large",
            "style": "creative"
        }
    )

    res = await chief.run_admin(pickle.dumps(job), [
        writer,
        researcher
    ])
    print(res)


if __name__ == '__main__':
    # enable_log("INFO")
    asyncio.run(main())
