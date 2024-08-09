import asyncio
from typing import List, Dict

from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from loguru import logger
from pydantic.v1 import BaseModel, Field

from ceylon import Agent, CoreAdmin, on_message


class SubTask(BaseModel):
    id: int = Field(description="the id of the subtask")
    description: str = Field(description="the description of the subtask")
    required_specialty: str = Field(description="the required specialty of the subtask")


class SubTaskList(BaseModel):
    subtasks: List[SubTask]


class Task(BaseModel):
    """
    id: int
    description: str
    subtasks: List[SubTask]
    """
    id: int = Field(description="the id of the task")
    description: str = Field(description="the description of the task")
    subtasks: List[SubTask] = Field(description="the subtasks of the task", default=[])


class TaskAssignment(BaseModel):
    task: Task = Field(description="the task assigned to the agent")
    subtask: SubTask = Field(description="the subtask assigned to the agent")
    assigned_agent: str = Field(description="the agent assigned to the subtask")


class TaskResult(BaseModel):
    task_id: int = Field(description="the id of the task")
    subtask_id: int = Field(description="the id of the subtask")
    agent: str = Field(description="the agent who completed the subtask")
    result: str = Field(description="the result of the subtask")


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

    async def generate_tasks_from_description(self, description: str) -> List[SubTask]:

        # Prompt template
        prompt = PromptTemplate.from_template(
            """
            Given the following job description, break it down into a main task and 3-5 key subtasks. Each subtask should have a specific description and required specialty.

            Job Description: {description}

            Respond with the tasks and their subtasks in the following format:

            Main Task: <Concise description of the overall task>

            Subtasks:
            1. <Specific subtask description> - Specialty: <Required specialty or skill>
            2. <Specific subtask description> - Specialty: <Required specialty or skill>
            3. <Specific subtask description> - Specialty: <Required specialty or skill>
            (Add up to 2 more subtasks if necessary)

            Additional Considerations:
            - Prioritize the subtasks in order of importance or chronological sequence
            - Ensure each subtask is distinct and contributes uniquely to the main task
            - Use clear, action-oriented language for each description
            - If applicable, include any interdependencies between subtasks
            """
        )

        # Chain
        llm = OllamaFunctions(model="llama3.1:latest", format="json", temperature=0.7)
        structured_llm = llm.with_structured_output(SubTaskList)
        chain = prompt | structured_llm
        sub_task_list = chain.invoke(input={
            "description": description
        })
        return sub_task_list.subtasks

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
        Task(id=1, description="Create an article about AI advancements"),
    ]

    # Create specialized agents
    agents = [
        SpecializedAgent("ContentWriter", "Content writing and research"),
        SpecializedAgent("ImageGenerator", "AI image generation and editing"),
        SpecializedAgent("Editor", "Proofreading, editing, and formatting"),
        SpecializedAgent("SEOMaster", "Search engine optimization and content optimization"),
        SpecializedAgent("ContentResearcher", "Content research and analysis"),
        SpecializedAgent("UIDesigner", "UI/UX design and frontend development"),
        SpecializedAgent("BackendDev", "Backend development and database management"),
        SpecializedAgent("QATester", "Software testing and quality assurance")
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, agents)
    task_manager.run_admin(inputs=b"", workers=agents)
