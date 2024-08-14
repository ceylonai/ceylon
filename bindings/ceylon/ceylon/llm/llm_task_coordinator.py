from typing import Dict, List, Set

import pydantic.v1
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from ceylon.llm.llm_task_operator import LLMTaskOperator
from ceylon.task import TaskResult, Task, SubTask
from ceylon.task.task_coordinator import TaskCoordinator


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


class LLMTaskCoordinator(TaskCoordinator):
    tasks: List[Task] = []
    agents: List[LLMTaskOperator] = []
    results: Dict[str, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[LLMTaskOperator], llm=None, tool_llm=None):
        self.llm = llm
        self.tool_llm = tool_llm
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000, tasks=tasks, agents=agents)

    async def get_task_executor(self, task: SubTask) -> str:
        return await self.get_best_agent_for_subtask(task)

    async def update_task(self, idx: int, task: Task):
        if len(task.subtasks) == 0:
            sub_tasks = await self.generate_tasks_from_description(task)
            for sub_task in sub_tasks:
                task.add_subtask(sub_task)

            depends_on = [sub_task.name for sub_task in sub_tasks]
            final_sub_task = SubTask(
                name="Generate Final Answer",
                description=f"Based on all previous sub-tasks, provide a comprehensive final answer to the main task: {task.description}",
                required_specialty="Synthesize information and generate conclusive answers",
                depends_on=depends_on,
            )
            task.add_subtask(final_sub_task)
        return task

    async def get_best_agent_for_subtask(self, subtask: SubTask) -> str:
        agent_specialties = "\n".join(
            [f"{agent.details().name}: {agent.details().role} {agent.context}" for agent in self.agents])

        prompt_template = ChatPromptTemplate.from_template(
            """
            Select the most suitable agent for this subtask:
        
            Subtask: {subtask_description}
            Required specialty: {required_specialty}
        
            Agent specialties:
            {agent_specialties}
        
            Available agents: {agent_names}
        
            Important: Respond ONLY with the exact name of the single most suitable agent from the available agents list.
            If no agent perfectly matches, choose the closest fit.
            """
        )

        runnable = prompt_template | self.llm | StrOutputParser()

        def get_valid_agent_name(max_attempts=3):
            agent_names = [agent.details().name for agent in self.agents]

            for attempt in range(max_attempts):
                response = runnable.invoke({
                    "subtask_description": subtask.description,
                    "required_specialty": subtask.required_specialty,
                    "agent_specialties": agent_specialties,
                    "agent_names": ", ".join(agent_names)
                }).strip()

                if response in agent_names:
                    return response
                print(response)
                print(f"Attempt {attempt + 1}: Invalid agent name received: {response} {subtask}. Retrying...")

            raise Exception(f"Failed to get a valid agent name after {max_attempts} attempts.")

        return get_valid_agent_name()

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
        # Make sure subtasks are valid
        sub_task_list = self.recheck_and_update_subtasks(subtasks=sub_task_list)
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
