import asyncio
import os
from typing import List

from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from openai import OpenAI
from pydantic.dataclasses import dataclass

from ceylon import Agent, CoreAdmin, on_message

# Ensure you set your OpenAI API key as an environment variable
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


@dataclass
class Task:
    id: int
    description: str


@dataclass
class TaskAssignment:
    task: Task
    assigned_agent: str


@dataclass
class TaskResult:
    task_id: int
    agent: str
    result: str


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str):
        self.specialty = specialty
        super().__init__(name=name, workspace_id="openai_task_management", admin_peer="TaskManager", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received task: {data.task.description}")
            # Simulate task execution
            await asyncio.sleep(2)
            result = f"{self.details().name} completed the task: {data.task.description}"
            await self.broadcast_data(TaskResult(task_id=data.task.id, agent=self.details().name, result=result))


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: List[TaskResult] = []

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent]):
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000)

    async def run(self, inputs: bytes):
        await self.assign_tasks()

    async def assign_tasks(self):
        for task in self.tasks:
            assigned_agent = await self.get_best_agent_for_task(task)
            print(f"Assigned task {task.id} to agent {assigned_agent}")
            await self.broadcast_data(TaskAssignment(task=task, assigned_agent=assigned_agent))

    async def get_best_agent_for_task(self, task: Task) -> str:
        agent_specialties = "\n".join([f"{agent.details().name}: {agent.specialty}" for agent in self.agents])
        # Initialize the language model
        llm = ChatOllama(model="llama3.1:latest", temperature=0)

        # Create a prompt template
        prompt_template = ChatPromptTemplate.from_template(
            """Given the following task and list of agents with their specialties, determine which agent is 
            best suited for the task.        

            Task: {task_description}
            
            Agents and their specialties:
            {agent_specialties}
            
            Respond with only the name of the best-suited agent."""
        )

        # Create the chain
        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(task_description=task.description, agent_specialties=agent_specialties)
        return response.strip()

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        self.results.append(result)
        logger.info(f"Received result for task {result.task_id} from {result.agent}: {result.result}")
        if len(self.results) == len(self.tasks):
            await self.end_task_management()

    async def end_task_management(self):
        logger.info("All tasks completed. Results:")
        for result in self.results:
            logger.info(f"Task {result.task_id}: {result.result}")
        await self.stop()


if __name__ == "__main__":
    # Create tasks
    tasks = [
        Task(id=1, description="Analyze recent stock market trends"),
        Task(id=2, description="Debug a Python web application"),
        Task(id=3, description="Write a press release for a new product launch"),
    ]

    # Create specialized agents
    agents = [
        SpecializedAgent("FinanceExpert", "Financial analysis and stock market trends"),
        SpecializedAgent("SoftwareDeveloper", "Programming, debugging, and software development"),
        SpecializedAgent("ContentWriter", "Writing, editing, and content creation"),
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, agents)
    task_manager.run_admin(inputs=b"", workers=agents)
