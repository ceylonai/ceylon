import copy
import logging
import sys
from textwrap import dedent
from typing import Dict, List, Set

import networkx as nx
import pydantic.v1
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from loguru import logger

from ceylon.llm.llm_task_operator import LLMTaskOperator
from ceylon.static_val import DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_PORT
from ceylon.task import SubTaskResult, Task, SubTask
from ceylon.task.task_coordinator import TaskCoordinator
from ceylon.task.task_operation import TaskDeliverable

logger.remove()
logger.add(sys.stderr, level="INFO")


class TaskDeliverableModel(pydantic.v1.BaseModel):
    objective: str = pydantic.v1.Field(
        description="The main objective of the task",
        default=""
    )
    deliverable: str = pydantic.v1.Field(
        description="The single, primary deliverable for the task",
        default=""
    )
    key_features: List[str] = pydantic.v1.Field(
        description="Key features of the deliverable",
        default=[]
    )
    considerations: List[str] = pydantic.v1.Field(
        description="Important considerations or constraints for the deliverable",
        default=[]
    )

    def to_v2(self) -> TaskDeliverable:
        return TaskDeliverable(
            objective=self.objective,
            deliverable=self.deliverable,
            key_features=self.key_features,
            considerations=self.considerations
        )

    @staticmethod
    def create_default_task_deliverable(task):
        return TaskDeliverableModel(
            objective="Complete the assigned task",
            deliverable=task.description,
            key_features=["Basic functionality"],
            considerations=["Meet minimum requirements"]
        )


class SubTaskModel(pydantic.v1.BaseModel):
    name: str = pydantic.v1.Field(description="Subtask name (snake_case)")
    description: str = pydantic.v1.Field(description="Detailed subtask explanation", default="")
    required_specialty: str = pydantic.v1.Field(description="Required skill or expertise", default="")
    depends_on: Set[str] = pydantic.v1.Field(description="Names of prerequisite subtasks", default=[])

    def to_v2(self, parent_task_id) -> SubTask:
        return SubTask(
            parent_task_id=parent_task_id,
            name=self.name,
            description=self.description,
            required_specialty=self.required_specialty,
            depends_on=self.depends_on
        )


class SubTaskListSchema(pydantic.v1.BaseModel):
    sub_task_list: List[SubTaskModel] = pydantic.v1.Field(description="The subtasks of the task", default_factory=list)


class LLMTaskCoordinator(TaskCoordinator):
    tasks: List[Task] = []
    agents: List[LLMTaskOperator] = []
    results: Dict[str, List[SubTaskResult]] = {}
    team_network: nx.Graph = nx.Graph()

    def __init__(self, tasks: List[Task] = None, agents: List[LLMTaskOperator] = None,
                 context: str = "",
                 team_goal: str = "",

                 llm=None, tool_llm=None,
                 name=DEFAULT_WORKSPACE_ID,
                 port=DEFAULT_WORKSPACE_PORT):
        self.context = context
        self.team_goal = team_goal
        self.llm = copy.copy(llm)
        self.tool_llm = copy.copy(tool_llm) if tool_llm is not None else copy.copy(llm)
        self.tasks = tasks if tasks is not None else []
        self.agents = agents if agents is not None else []
        super().__init__(name=name, port=port, tasks=tasks, agents=agents)

    def on_init(self):
        if len(self.agents) > 0:
            logger.info(
                f"LLM Task Coordinator initialized with {len(self.tasks)} "
                f"tasks and {len(self.get_llm_operators)} agents {[agent.details().name for agent in self.get_llm_operators]}")

    #     self.initialize_team_network()
    #
    # def initialize_team_network(self):
    #     for agent in self.get_llm_operators:
    #         self.team_network.add_node(agent.details().name, role=agent.details().role)

    async def update_task(self, idx: int, task: Task):
        logger.info(f"Updating task {task.name} with {len(task.subtasks)} subtasks")
        if task.task_deliverable is None:
            task_deliverable = await self.build_task_deliverable(task)
            task.set_deliverable(task_deliverable)

        if len(task.subtasks) == 0:
            sub_tasks = await self.generate_tasks_from_description(task)
            for sub_task in sub_tasks:
                task.add_subtask(sub_task)

            final_sub_task = await self.generate_final_sub_task_from_description(task)
            task.add_subtask(final_sub_task)

        logger.info(f"Task {task.name} updated with {len(task.subtasks)} subtasks")
        for subtask in task.subtasks.values():
            logger.info(f"Subtask {subtask.name} updated with {len(subtask.depends_on)} dependencies")
        # await self.update_team_network(task)
        return task

    # async def update_team_network(self, task: Task):
    #     for subtask in task.subtasks.values():
    #         agent_name = await self.get_best_agent_for_subtask(subtask)
    #         for dependency in subtask.depends_on:
    #             dependency_agent = await self.get_best_agent_for_subtask(task.subtasks[dependency])
    #             self.team_network.add_edge(agent_name, dependency_agent, task=task.id, subtask=subtask.name)
    #
    # async def analyze_team_dynamics(self) -> str:
    #     prompt = PromptTemplate.from_template(
    #         dedent("""
    #         Analyze the following team network and provide insights on team dynamics:
    #
    #         Nodes (Agents): {nodes}
    #         Edges (Collaborations): {edges}
    #
    #         Please provide a brief analysis covering:
    #         1. Key collaborators
    #         2. Potential bottlenecks
    #         3. Suggestions for improving team efficiency
    #
    #         Respond in a concise paragraph.
    #         """
    #                ))
    #
    #     nodes = [f"{node}: {data}" for node, data in self.team_network.nodes(data=True)]
    #     edges = [f"{u} - {v}: {data}" for u, v, data in self.team_network.edges(data=True)]
    #
    #     chain = prompt | self.llm | StrOutputParser()
    #     analysis = chain.invoke({"nodes": nodes, "edges": edges})
    #     return analysis
    #
    # def visualize_team_network(self, output_file: str = None):
    #     import matplotlib.pyplot as plt
    #     plt.figure(figsize=(12, 8))
    #     pos = nx.spring_layout(self.team_network)
    #     nx.draw(self.team_network, pos, with_labels=True, node_color='lightblue', node_size=1000, font_size=8)
    #     edge_labels = nx.get_edge_attributes(self.team_network, 'task')
    #     nx.draw_networkx_edge_labels(self.team_network, pos, edge_labels=edge_labels)
    #     if output_file is not None:
    #         plt.title("Team Collaboration Network")
    #         plt.savefig(output_file)
    #         plt.close()
    #     else:
    #         plt.show()

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
        logger.debug(f"Getting best agent for subtask '{subtask.name}'")
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
                logger.info(f"Attempt {attempt + 1}: Invalid agent name received: {response} {subtask}. Retrying...")

            raise Exception(f"Failed to get a valid agent name after {max_attempts} attempts.")

        return get_valid_agent_name()

    async def generate_final_sub_task_from_description(self, task: Task) -> SubTask:
        logger.debug(
            f"Generating final subtask from task description '{task.description}' and subtasks '{len(task.subtasks)}'")
        pydantic_parser = PydanticOutputParser(pydantic_object=SubTaskModel)
        format_instructions = pydantic_parser.get_format_instructions()
        # Prompt template
        prompt = PromptTemplate(
            template=dedent(
                """
                Given the following job description and existing subtasks, add a final delivery step to complete the project.
                This final step should focus on delivering the completed work.

                Job Description: {description}
                Job Deliverable Data: {task_deliverable}

                Existing Subtasks:
                {existing_subtasks}

                Respond with the final delivery step in the following JSON format:

                {format_instructions}

                Additional Considerations:
                - Ensure the final step encompasses presenting or delivering the completed work
                - Use clear, action-oriented language for the description
                - Include dependencies on relevant existing subtasks
                - Focus on delivering the functionality and value of the completed project
                """
            ),
            input_variables=["description", "task_deliverable", "existing_subtasks"],
            partial_variables={"format_instructions": format_instructions},
        )
        prompt_str = prompt.format(**{
            "description": task.description,
            "task_deliverable": task.task_deliverable,
            "existing_subtasks": "\n".join([f"{t.name}- {t.description}" for t in task.subtasks.values()])
        })
        logger.opt(exception=True).debug(f"Prompt: {prompt_str}")

        chain = prompt | self.tool_llm | pydantic_parser
        final_subtask_model = chain.invoke(input={
            "description": task.description,
            "task_deliverable": task.task_deliverable,
            "existing_subtasks": "\n".join([f"{t.name}- {t.description}" for t in task.subtasks.values()])
        })
        print(f"Final subtask: {final_subtask_model}")
        return final_subtask_model.to_v2(task.id)

    async def generate_tasks_from_description(self, task: Task) -> List[SubTask]:
        logger.info(f"Generating sub tasks from description: {task.description}")

        pydantic_parser = PydanticOutputParser(pydantic_object=SubTaskListSchema)
        format_instructions = pydantic_parser.get_format_instructions()

        # Prompt template
        prompt = PromptTemplate(
            template=dedent(
                """
                Analyze the following job description and break it down into a main task and 3-5 key subtasks:

                Job Description: {description}
                Job Deliverable: {task_deliverable}

                {format_instructions}

                Guidelines:
                - Max {number_of_max_tasks} subtasks
                - Name must be in snake_case
                - Description must be in clear, action-oriented language
                - Prioritize subtasks by importance or sequence
                - Ensure each subtask is distinct and essential
                - Use clear, action-oriented language
                - Include subtask interdependencies where relevant
                - Strictly adhere to the JSON format provided above
                """
            ),
            input_variables=["description", "task_deliverable", "number_of_max_tasks"],
            partial_variables={"format_instructions": format_instructions},
        )

        prompt_str = prompt.format(**{
            "description": task.description,
            "metadata": task.metadata,
            "task_deliverable": task.task_deliverable,
            "number_of_max_tasks": task.max_subtasks - 1,
        })
        logger.opt(exception=True).debug(f"Prompt: {prompt_str}")

        chain = prompt | self.tool_llm | pydantic_parser
        sub_task_list = chain.invoke(input={
            "description": task.description,
            "metadata": task.metadata,
            "task_deliverable": task.task_deliverable,
            "number_of_max_tasks": task.max_subtasks - 1,
        })

        # logger.info(sub_task_list)
        # Make sure subtasks are valid
        sub_task_list = self.recheck_and_update_subtasks(subtasks=sub_task_list)
        if len(sub_task_list) == 0:
            return []
        return [t.to_v2(task.id) for t in sub_task_list]

    def recheck_and_update_subtasks(self, subtasks):

        pydantic_parser = PydanticOutputParser(pydantic_object=SubTaskListSchema)
        format_instructions = pydantic_parser.get_format_instructions()

        # Prompt template
        prompt = PromptTemplate(
            template=dedent(
                """
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
                Output in JSON format:

                {format_instructions}

                Guidelines:
                - Name must be in snake_case
                - Description must be in clear, action-oriented language
                - Prioritize subtasks by importance or sequence
                - Ensure each subtask is distinct and essential
                - Use clear, action-oriented language
                - Include subtask interdependencies where relevant
                - Strictly adhere to the JSON format provided above
                """
            ),
            input_variables=["subtasks"],
            partial_variables={"format_instructions": format_instructions},
        )

        # Chain
        prompt_str = prompt.format(**{
            "subtasks": subtasks
        })
        logger.opt(exception=True).debug(f"Prompt: {prompt_str}")

        chain = prompt | self.tool_llm | pydantic_parser
        result: SubTaskListSchema = chain.invoke(input={
            "subtasks": subtasks
        })
        if result is None:
            return []
        return result.sub_task_list

    async def build_task_deliverable(self, task: Task):
        logger.info(f"Building deliverable for task: {task.id}")

        pydantic_parser = PydanticOutputParser(pydantic_object=TaskDeliverableModel)
        format_instructions = pydantic_parser.get_format_instructions()

        prompt = PromptTemplate(
            template=dedent("""
            Given:
            Context: {context}
            Team Objectives: {objectives}
            Task Description: {task_description}
    
            Analyze the above information and provide:
            1. The main objective of the task
            2. A single, primary deliverable
            3. Key features of the deliverable
            4. Important considerations based on team objectives
    
            Respond in JSON format:
    
            {format_instructions}
        """),
            input_variables=["context", "objectives", "task_description"],
            partial_variables={"format_instructions": format_instructions},
        )

        # Chain
        prompt_str = prompt.format(**{
            "context": self.context,
            "objectives": self.team_goal,
            "task_description": task.description
        })
        logger.opt(exception=True).debug(f"Prompt: {prompt_str}")

        chain = prompt | self.tool_llm | pydantic_parser
        task_deliverable: TaskDeliverableModel = chain.invoke(input={
            "context": self.context,
            "objectives": self.team_goal,
            "task_description": task.description
        })
        if task_deliverable is None:
            return TaskDeliverableModel.create_default_task_deliverable(task).to_v2()
        return task_deliverable.to_v2()
