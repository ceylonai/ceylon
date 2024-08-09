import asyncio
import pickle
from dataclasses import dataclass
from typing import List, Dict

from langchain.chains import LLMChain
from langchain.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import Agent, CoreAdmin, on_message


@dataclass
class SubTask:
    id: int
    description: str
    required_specialty: str


@dataclass
class Task:
    id: int
    description: str
    subtasks: List[SubTask]


@dataclass
class TaskAssignment:
    task: Task
    subtask: SubTask
    assigned_agent: str


@dataclass
class TaskResult:
    task_id: int
    subtask_id: int
    agent: str
    result: str


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str):
        self.specialty = specialty
        super().__init__(name=name, workspace_id="openai_task_management", admin_peer="TaskManager", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.subtask.description}")
            # Simulate task execution
            await asyncio.sleep(2)
            result = f"{self.details().name} completed the subtask: {data.subtask.description}"
            await self.broadcast_data(
                TaskResult(task_id=data.task.id, subtask_id=data.subtask.id, agent=self.details().name, result=result))


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: Dict[int, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent]):
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000)

    async def run(self, inputs: bytes):

        for idx, task in enumerate(self.tasks):
            if len(task.subtasks) == 0:
                generated_tasks = await self.generate_tasks_from_description(task.description)
                self.tasks[idx].subtasks = generated_tasks
        await self.assign_tasks()

    async def assign_tasks(self):
        for task in self.tasks:
            self.results[task.id] = []
            for subtask in task.subtasks:
                assigned_agent = await self.get_best_agent_for_subtask(subtask)
                print(f"Assigned subtask {subtask.id} of task {task.id} to agent {assigned_agent}")
                await self.broadcast_data(TaskAssignment(task=task, subtask=subtask, assigned_agent=assigned_agent))

    async def get_best_agent_for_subtask(self, subtask: SubTask) -> str:
        agent_specialties = "\n".join([f"{agent.details().name}: {agent.specialty}" for agent in self.agents])
        llm = ChatOllama(model="llama3.1:latest", temperature=0)

        prompt_template = ChatPromptTemplate.from_template(
            """Given the following subtask and list of agents with their specialties, determine which agent is 
            best suited for the subtask.        

            Subtask: {subtask_description}
            Required Specialty: {required_specialty}
            
            Agents and their specialties:
            {agent_specialties}
            
            Respond with only the name of the best-suited agent."""
        )

        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(subtask_description=subtask.description, required_specialty=subtask.required_specialty,
                             agent_specialties=agent_specialties)
        return response.strip()

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        self.results[result.task_id].append(result)
        logger.info(
            f"Received result for subtask {result.subtask_id} of task {result.task_id} from {result.agent}: {result.result}")
        if self.all_tasks_completed():
            await self.end_task_management()

    def all_tasks_completed(self) -> bool:
        for task in self.tasks:
            if len(self.results[task.id]) != len(task.subtasks):
                return False
        return True

    async def end_task_management(self):
        logger.info("All tasks completed. Results:")
        for task in self.tasks:
            logger.info(f"Task {task.id} results:")
            for result in self.results[task.id]:
                logger.info(f"  Subtask {result.subtask_id}: {result.result}")
        await self.stop()

    async def generate_tasks_from_description(self, description: str) -> List[Task]:
        llm = ChatOllama(model="llama3.1:latest", temperature=0.7)

        prompt_template = ChatPromptTemplate.from_template(
            """Given the following description, break it down into a main task and several subtasks. Each subtask 
            should have a specific description and required specialty. 

            Description: {description}
            
            Respond with the tasks and their subtasks in the following format:
            Task Description: <Main task description>
            Subtasks:
            1. <Subtask description> - Specialty: <Specialty>
            2. <Subtask description> - Specialty: <Specialty>
            ...
            """
        )

        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(description=description, verbose=True)

        print(f"LLM response: {description}")

        # Parsing the LLM response to extract tasks and subtasks
        tasks = self.parse_llm_response(response)
        return tasks

    @staticmethod
    def parse_llm_response(response: str) -> List[Task]:
        lines = response.splitlines()
        tasks = []
        current_task = None
        subtasks = []
        for line in lines:
            if line.startswith("Task Description:"):
                if current_task:
                    tasks.append(Task(id=len(tasks) + 1, description=current_task, subtasks=subtasks))
                    subtasks = []
                current_task = line.replace("Task Description:", "").strip()
            elif line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
                parts = line.split(" - Specialty: ")
                subtask_description = parts[0].split(". ", 1)[1].strip()
                required_specialty = parts[1].strip() if len(parts) > 1 else "General"
                subtasks.append(SubTask(id=len(subtasks) + 1, description=subtask_description,
                                        required_specialty=required_specialty))

        if current_task:
            tasks.append(Task(id=len(tasks) + 1, description=current_task, subtasks=subtasks))

        return tasks


if __name__ == "__main__":
    # Create tasks with subtasks
    tasks = [
        Task(id=1, description="Create an article about AI advancements", subtasks=[
            # SubTask(id=1, description="Write the main content of the article", required_specialty="Content writing"),
            # SubTask(id=2, description="Generate an AI-related image for the article",
            #         required_specialty="Image generation"),
            # SubTask(id=3, description="Proofread and format the article", required_specialty="Editing and formatting")
        ]),
        # Task(id=2, description="Develop a simple web application", subtasks=[
        #     # SubTask(id=1, description="Design the user interface", required_specialty="UI/UX design"),
        #     # SubTask(id=2, description="Implement the backend logic", required_specialty="Backend development"),
        #     # SubTask(id=3, description="Test the application", required_specialty="Software testing")
        # ])
    ]

    # Create specialized agents
    agents = [
        SpecializedAgent("ContentWriter", "Content writing and research"),
        SpecializedAgent("ImageGenerator", "AI image generation and editing"),
        SpecializedAgent("Editor", "Proofreading, editing, and formatting"),
        SpecializedAgent("UIDesigner", "UI/UX design and frontend development"),
        SpecializedAgent("BackendDev", "Backend development and database management"),
        SpecializedAgent("QATester", "Software testing and quality assurance")
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, agents)
    task_manager.run_admin(inputs=b"", workers=agents)
