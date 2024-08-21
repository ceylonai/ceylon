import copy
from textwrap import dedent
from typing import Dict, List, Set

import networkx as nx
import pydantic.v1
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from loguru import logger

from ceylon.llm.llm_task_operator import LLMTaskOperator
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_ADMIN_PORT
from ceylon.task import SubTaskResult, Task, SubTask
from ceylon.task.task_coordinator import TaskCoordinator
from ceylon.task.task_operation import TaskDeliverable


class TaskDeliverableModel(pydantic.v1.BaseModel):
    objectives: List[str] = pydantic.v1.Field(
        description="the objectives of the task, Explains the task in detail",
        default=[]
    )
    final_output: str = pydantic.v1.Field(
        description="the final output of the task",
        default="")
    final_output_type: str = pydantic.v1.Field(
        description="the type of the final output of the task",
        default="")

    def to_v2(self) -> TaskDeliverable:
        return TaskDeliverable(
            objectives=self.objectives,
            final_output=self.final_output,
            final_output_type=self.final_output_type
        )


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
    results: Dict[str, List[SubTaskResult]] = {}
    team_network: nx.Graph = nx.Graph()

    def __init__(self, tasks: List[Task], agents: List[LLMTaskOperator],
                 context: str,
                 team_goal: str,

                 llm=None, tool_llm=None,
                 name=DEFAULT_WORKSPACE_ID,
                 port=DEFAULT_ADMIN_PORT):
        self.context = context
        self.team_goal = team_goal
        self.llm = copy.copy(llm)
        self.tool_llm = copy.copy(tool_llm) if tool_llm is not None else copy.copy(llm)
        self.tasks = tasks
        self.agents = agents
        self.initialize_team_network()
        logger.info(
            f"LLM Task Coordinator initialized with {len(tasks)} tasks and {len(self.get_llm_operators)} agents {[agent.details().name for agent in self.get_llm_operators]}")
        super().__init__(name=name, port=port, tasks=tasks, agents=agents)

    def initialize_team_network(self):
        for agent in self.get_llm_operators:
            self.team_network.add_node(agent.details().name, role=agent.details().role)

    async def update_task(self, idx: int, task: Task):
        if task.task_deliverable is None:
            task_deliverable = await self.build_task_deliverable(task)
            task.set_deliverable(task_deliverable)

        if len(task.subtasks) == 0:
            sub_tasks = await self.generate_tasks_from_description(task)
            for sub_task in sub_tasks:
                task.add_subtask(sub_task)

            final_sub_task = await self.generate_final_sub_task_from_description(task)
            task.add_subtask(final_sub_task)

        await self.update_team_network(task)
        return task

    async def update_team_network(self, task: Task):
        for subtask in task.subtasks.values():
            agent_name = await self.get_best_agent_for_subtask(subtask)
            for dependency in subtask.depends_on:
                dependency_agent = await self.get_best_agent_for_subtask(task.subtasks[dependency])
                self.team_network.add_edge(agent_name, dependency_agent, task=task.id, subtask=subtask.name)

    async def analyze_team_dynamics(self) -> str:
        prompt = PromptTemplate.from_template(
            dedent("""
            Analyze the following team network and provide insights on team dynamics:

            Nodes (Agents): {nodes}
            Edges (Collaborations): {edges}

            Please provide a brief analysis covering:
            1. Key collaborators
            2. Potential bottlenecks
            3. Suggestions for improving team efficiency

            Respond in a concise paragraph.
            """
                   ))

        nodes = [f"{node}: {data}" for node, data in self.team_network.nodes(data=True)]
        edges = [f"{u} - {v}: {data}" for u, v, data in self.team_network.edges(data=True)]

        chain = prompt | self.llm | StrOutputParser()
        analysis = chain.invoke({"nodes": nodes, "edges": edges})
        return analysis

    def visualize_team_network(self, output_file: str = None):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.team_network)
        nx.draw(self.team_network, pos, with_labels=True, node_color='lightblue', node_size=1000, font_size=8)
        edge_labels = nx.get_edge_attributes(self.team_network, 'task')
        nx.draw_networkx_edge_labels(self.team_network, pos, edge_labels=edge_labels)
        if output_file is not None:
            plt.title("Team Collaboration Network")
            plt.savefig(output_file)
            plt.close()
        else:
            plt.show()

    async def get_task_executor(self, task: SubTask) -> str:
        return await self.get_best_agent_for_subtask(task)

    @property
    def get_llm_operators(self) -> List[LLMTaskOperator]:
        operators = []
        for agent in self.agents:
            if isinstance(agent, LLMTaskOperator) and hasattr(agent,
                                                              "agent_type") and agent.agent_type == LLMTaskOperator.agent_type:
                operators.append(agent)

        return operators

    async def get_best_agent_for_subtask(self, subtask: SubTask) -> str:
        agent_specialties = "\n".join(
            [f"{agent.details().name}: {agent.details().role} {agent.context}" for agent in self.get_llm_operators])

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
            agent_names = [agent.details().name for agent in self.get_llm_operators]

            for attempt in range(max_attempts):
                response = runnable.invoke({
                    "subtask_description": subtask.description,
                    "required_specialty": subtask.required_specialty,
                    "agent_specialties": agent_specialties,
                    "agent_names": ", ".join(agent_names)
                }).strip()

                if response in agent_names:
                    return response
                # print(response)
                logger.info(f"Attempt {attempt + 1}: Invalid agent name received: {response} {subtask}. Retrying...")

            raise Exception(f"Failed to get a valid agent name after {max_attempts} attempts.")

        return get_valid_agent_name()

    async def generate_final_sub_task_from_description(self, task: Task) -> SubTask:
        prompt = PromptTemplate.from_template(
            dedent("""
                Given the following job description and existing subtasks, add a final delivery step to complete the project.
                 This final step should focus on  delivering the completed work.

                Job Description: {description}
                Job Deliverable Data : {task_deliverable}

                Existing Subtasks:
                {existing_subtasks}

                Respond with only the final delivery step in the following format:

                Final Step:
                <Specific description of the final delivery step> - Specialty: <Required specialty or skill> - Depends on: <Names of subtasks that must be completed before this one>

                Additional Considerations:
                - Ensure the final step encompasses presenting or delivering the completed work
                - Use clear, action-oriented language for the description
                - Include dependencies on relevant existing subtasks
                - Focus on delivering the functionality and value of the completed project
                """)
        )

        # Chain
        structured_llm = self.tool_llm.with_structured_output(SubTaskModel)
        chain = prompt | structured_llm
        sub_task: SubTaskModel = chain.invoke(input={
            "description": task.description,
            "task_deliverable": task.task_deliverable,
            "existing_subtasks": "\n".join([f"{t.name}- {t.description}" for t in task.subtasks.values()])
        })
        # print(sub_task)
        return sub_task.to_v2(task.id)

    async def generate_tasks_from_description(self, task: Task) -> List[SubTask]:

        # Prompt template
        prompt = PromptTemplate.from_template(
            dedent(
                """
            Given the following job description, break it down into a main task and 3-5 key subtasks. Each subtask should have a specific description and required specialty.

            Job Description: {description}
            Job Deliverable Data : {task_deliverable}

            Respond with the tasks and their subtasks in the following format:

            Main Task: <Concise description of the overall task>

            Subtasks:
            1. <Describe the first action item needed to progress towards the objective.> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            2. <Describe the second action item needed to progress towards the objective.> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            3. <Describe the third action item needed to progress towards the objective.> - Specialty: <Required specialty or skill> - Depends on: <Subtasks name that must be completed before this one>
            (Add up to 2 more subtasks if necessary)

            Additional Considerations:
            - Prioritize the subtasks in order of importance or chronological sequence
            - Ensure each subtask is distinct and contributes uniquely to the main task
            - Use clear, action-oriented language for each description
            - If applicable, include any interdependencies between subtasks
            """)
        )

        # Chain
        structured_llm = self.tool_llm.with_structured_output(SubTaskList)
        chain = prompt | structured_llm
        sub_task_list = chain.invoke(input={
            "description": task.description,
            "metadata": task.metadata,
            "task_deliverable": task.task_deliverable,
        })
        # Make sure subtasks are valid
        sub_task_list = self.recheck_and_update_subtasks(subtasks=sub_task_list)
        return [t.to_v2(task.id) for t in sub_task_list.sub_task_list]

    def recheck_and_update_subtasks(self, subtasks):
        subtask_validation_template = PromptTemplate.from_template(
            dedent("""
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
        """))
        structured_llm = self.tool_llm.with_structured_output(SubTaskList)
        chain = subtask_validation_template | structured_llm
        sub_task_list = chain.invoke(input={
            "subtasks": subtasks
        })
        return sub_task_list

    async def build_task_deliverable(self, task: Task):
        build_task_deliverable_template = PromptTemplate.from_template(dedent("""
        Context: {context}

        Team Objectives: {objectives}

        Task Description: {task_description}

        Based on the given context, team objectives, and task description, please provide:

        1. Clear goals for the task management application project
        2. A list of specific deliverables
        3. Key features to be implemented
        4. Any considerations or constraints based on the team's objectives
        
        Please format your response as a JSON object with the following structure:
            {{
              "objectives": ["objective1", "objective2", ...],
              "final_output": "Description of the final output",
              "final_output_type": "Type of the final output"
            }}
        
        
        """))

        structured_llm = self.tool_llm.with_structured_output(TaskDeliverableModel)
        chain = build_task_deliverable_template | structured_llm
        task_deliverable: TaskDeliverableModel = chain.invoke(input={
            "context": self.context,
            "objectives": self.team_goal,
            "task_description": task.description
        })
        if task_deliverable is None:
            return TaskDeliverable(
                objectives=[
                    "Finish the required deliverable",
                ],
                final_output=f"{task.description}",
                final_output_type="text"
            )
        return task_deliverable.to_v2()
