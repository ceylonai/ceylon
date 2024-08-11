import pprint
from typing import Dict, List, Set

import pydantic.v1
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from loguru import logger

from ceylon import on_message, CoreAdmin
from ceylon.llm import TaskAssignment, TaskResult, Task, SubTask
from ceylon.llm.agent import SpecializedAgent


class SubTaskModel(pydantic.v1.BaseModel):
    name: str = pydantic.v1.Field(description="the name of the subtask write in snake_case")
    description: str = pydantic.v1.Field(
        description="the description of the subtask, Explains the task in detail")
    required_specialty: str = pydantic.v1.Field(description="the required specialty of the subtask")
    depends_on: Set[str] = pydantic.v1.Field(description="the subtasks that must be completed before this one",
                                             default=[])

    def to_v2(self, parent_task_id) -> SubTask:
        return SubTask(
            parent_task_id=parent_task_id,
            name=self.name,
            description=self.description,
            required_specialty=self.required_specialty,
            depends_on=self.depends_on
        )


class SubTaskList(pydantic.v1.BaseModel):
    sub_task_list: List[SubTaskModel] = pydantic.v1.Field(description="the subtasks of the task", default=[])


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: Dict[str, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent], llm=None, tool_llm=None):
        self.llm = llm
        self.tool_llm = tool_llm
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000)

    async def run(self, inputs: bytes):
        for idx, task in enumerate(self.tasks):
            if len(task.subtasks) == 0:
                sub_tasks = await self.generate_tasks_from_description(task)
                for sub_task in sub_tasks:
                    task.add_subtask(sub_task)
                pprint.pprint(sub_tasks)

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
        runnable = prompt_template | self.llm | StrOutputParser()

        response = runnable.invoke({
            "subtask_description": subtask.description,
            "required_specialty": subtask.required_specialty,
            "agent_specialties": agent_specialties
        })
        return response.strip()

    async def generate_tasks_from_description(self, task: Task) -> List[SubTask]:

        # Prompt template
        prompt = PromptTemplate.from_template(
            """
            Given the following job description, break it down into a main task and 3-5 key subtasks. Each subtask should have a specific description and required specialty.

            Job Description: {description}

            Respond with the tasks and their subtasks in the following format:

            Main Task: <Concise description of the overall task>

            Subtasks:
            1. <Specific subtask description> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            2. <Specific subtask description> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            3. <Specific subtask description> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            (Add up to 2 more subtasks if necessary)

            Additional Considerations:
            - Prioritize the subtasks in order of importance or chronological sequence
            - Ensure each subtask is distinct and contributes uniquely to the main task
            - Use clear, action-oriented language for each description
            - If applicable, include any interdependencies between subtasks
            """
        )

        # Chain
        structured_llm = self.tool_llm.with_structured_output(SubTaskList)
        chain = prompt | structured_llm
        sub_task_list = chain.invoke(input={
            "description": task.description
        })

        sub_task_list = self.recheck_and_update_subtasks(subtasks=sub_task_list)
        print(sub_task_list)

        return [t.to_v2(task.id) for t in sub_task_list.sub_task_list]

    def recheck_and_update_subtasks(self, subtasks):
        subtask_validation_template = PromptTemplate.from_template("""
                You are tasked with reviewing and modifying a list of SubTasks. Please process the following list of SubTasks according to these criteria:
                
                1. Name Format:
                   - Convert all SubTask names to snake_case format.
                   - Ensure each word is lowercase and separated by underscores.
                   - Example: "draftArticleOutline" should become "draft_article_outline"
                
                2. Dependency Validation:
                   - Check that all dependencies listed in the 'depends_on' field are valid SubTask names within the list.
                   - Ensure that the dependency names are also in snake_case format.
                   - Remove any dependencies that do not correspond to existing SubTask names.
                
                3. Circular Dependency Check:
                   - Verify that there are no circular dependencies among the SubTasks.
                   - A circular dependency occurs when Task A depends on Task B, and Task B directly or indirectly depends on Task A.
                
                4. Consistency:
                   - Ensure all other fields (id, parent_task_id, description, required_specialty, completed, completed_at, result) remain unchanged.
                
                5. Output Format:
                   - Return the modified list of SubTasks in the same structure as the input.
                
                Here is the list of SubTasks to process:
                
                {subtasks}
                
                Please provide the updated list of SubTasks with all the above modifications and validations applied.
        """)
        structured_llm = self.tool_llm.with_structured_output(SubTaskList)
        chain = subtask_validation_template | structured_llm
        sub_task_list = chain.invoke(input={
            "subtasks": subtasks
        })
        return sub_task_list

    def do(self, inputs: bytes) -> List[Task]:
        self.run_admin(inputs, self.agents)
        return self.tasks
