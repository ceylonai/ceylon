from typing import List, Dict

from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from loguru import logger

from ceylon import CoreAdmin, on_message
from ceylon.llm.agent import SpecializedAgent
from ceylon.llm.data_types import Task, TaskResult, TaskAssignment, SubTask, SubTaskList


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: Dict[int, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent]):
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="langchain_task_management", port=8000)

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
