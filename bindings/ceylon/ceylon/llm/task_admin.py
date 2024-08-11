from typing import Dict, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import on_message, CoreAdmin
from ceylon.llm import TaskAssignment, TaskResult, Task, SubTask
from ceylon.llm.agent import SpecializedAgent


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: Dict[str, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent], tool_llm=None):
        self.tool_llm = tool_llm
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000)

    async def run(self, inputs: bytes):
        for idx, task in enumerate(self.tasks):
            if task.validate_sub_tasks():
                logger.info(f"Task {task.name} is valid")
            else:
                logger.info(f"Task {task.name} is invalid")
                del self.tasks[idx]

        await self.run_tasks()

    async def run_tasks(self):
        if len(self.tasks) == 0:
            logger.info("No tasks found")
            return
        for task in self.tasks:
            self.results[task.id] = []
            sub_task = task.get_next_subtask()
            if sub_task is None:
                continue
            subtask_name, subtask_ = sub_task
            assigned_agent = await self.get_best_agent_for_subtask(subtask_)
            await self.broadcast_data(TaskAssignment(task=subtask_, assigned_agent=assigned_agent))

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        for idx, task in enumerate(self.tasks):
            sub_task = task.get_next_subtask()
            if sub_task is None or result.task_id != sub_task[1].id:
                continue
            if result.task_id == sub_task[1].id:
                task.update_subtask_status(sub_task[1].name, result.result)
                break

        if self.all_tasks_completed():
            await self.end_task_management()

        await self.run_tasks()

    def all_tasks_completed(self) -> bool:
        for task in self.tasks:
            subtask_completed_status = [st.completed for st in task.subtasks.values()]
            if not all(subtask_completed_status):
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

        prompt_template = ChatPromptTemplate.from_template(
            """Given the following subtask and list of agents with their specialties, determine which agent is 
            best suited for the subtask.        

            Subtask: {subtask_description}
            Required Specialty: {required_specialty}
            
            Agents and their specialties:
            {agent_specialties}
            
            Respond with only the name of the best-suited agent."""
        )
        runnable = prompt_template | self.tool_llm | StrOutputParser()

        response = runnable.invoke({
            "subtask_description": subtask.description,
            "required_specialty": subtask.required_specialty,
            "agent_specialties": agent_specialties
        })
        return response.strip()

    def do(self, inputs: bytes) -> List[Task]:
        self.run_admin(inputs, self.agents)
        return self.tasks
