import copy
from typing import Dict, List, Set

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import Agent, on_message
from ceylon.llm import TaskAssignment, TaskResult


class SpecializedAgent(Agent):
    def __init__(self, name: str, role: str, context: str, skills: List[str],
                 tools: List[str] = None, llm=None):
        self.context = context
        self.skills = skills
        self.tools = tools if tools else []
        self.task_history = []
        self.llm = copy.copy(llm)
        self.history: Dict[str, List[TaskResult]] = {}
        super().__init__(name=name, workspace_id="openai_task_management", admin_port=8000)

    async def get_llm_response(self, task_description: str, parent_task_id: str, depends_on: Set[str]) -> str:
        # Construct the agent profile context
        agent_profile = f"""
        Agent Profile:
        - Name: {self.details().name}
        - Role: {self.details().role}
        - Context: {self.context}
        - Skills: {', '.join(self.skills)}
        - Available Tools: {', '.join(self.tools)}
        """

        # Construct the task information context
        task_info = f"""
        Task Information:
        - Description: {task_description}
        
        Recent Task History:
        {self._format_task_history(parent_task_id, depends_on)}
        """

        # Combine all context information
        context = f"{agent_profile}\n\n{task_info}"

        # Create the prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are an AI assistant helping a specialized agent. "
                        "Use the following context to provide the best approach for the task."),
            HumanMessage(
                content=f"{context}\n\nGiven this information, what's the best"
                        f"approach to complete this task efficiently and effectively?")
        ])

        try:
            runnable = prompt_template | self.llm | StrOutputParser()
            response = runnable.invoke({
                context: context
            })
            return response
        except Exception as e:
            logger.error(f"Error in LLM request: {e}")
            return "Error in processing the task with LLM."

    def _format_task_history(self, task_id, depends_on: Set[str]) -> str:
        if task_id not in self.history:
            return ""

        results = []
        for rest_his in self.history[task_id]:
            if rest_his.name in depends_on:
                results.append(f"{rest_his.agent} - \n- {rest_his.result}")
        return "\n".join(results)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.task.description}")
            result = await self.get_llm_response(
                data.task.description,
                data.task.parent_task_id,
                data.task.depends_on
            )
            result_task = TaskResult(task_id=data.task.id,
                                     name=data.task.name,
                                     agent=self.details().name,
                                     parent_task_id=data.task.parent_task_id,
                                     result=result)
            # Update task history
            await self.add_result_to_history(result_task)
            await self.broadcast_data(result_task)

    @on_message(type=TaskResult)
    async def on_task_result(self, data: TaskResult):
        await self.add_result_to_history(data)

    async def add_result_to_history(self, data: TaskResult):
        if data.parent_task_id in self.history:
            self.history[data.parent_task_id].append(data)
        else:
            self.history[data.parent_task_id] = [data]
