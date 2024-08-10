import copy
from typing import List

from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import Agent, on_message
from ceylon.llm.data_types import TaskAssignment, TaskResult


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str, skills: List[str], experience_level: str,
                 tools: List[str], llm=None):
        self.specialty = specialty
        self.skills = skills
        self.experience_level = experience_level
        self.tools = tools
        self.task_history = []
        self.llm = copy.copy(llm)
        super().__init__(name=name, workspace_id="langchain_task_management", admin_port=8000)

    async def get_llm_response(self, task_description: str) -> str:
        # Construct the agent profile context
        agent_profile = f"""
        Agent Profile:
        - Name: {self.details().name}
        - Specialty: {self.specialty}
        - Skills: {', '.join(self.skills)}
        - Experience Level: {self.experience_level}
        - Available Tools: {', '.join(self.tools)}
        """

        # Construct the task information context
        task_info = f"""
        Task Information:
        - Description: {task_description}
        
        Recent Task History:
        {self._format_task_history()}
        """

        # Combine all context information
        context = f"{agent_profile}\n\n{task_info}"

        # Create the prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are an AI assistant helping a specialized agent. Use the following context to provide the best approach for the task."),
            HumanMessage(
                content=f"{context}\n\nGiven this information, what's the best approach to complete this task efficiently and effectively?")
        ])

        try:
            chain = LLMChain(llm=self.llm, prompt=prompt_template)
            response = chain.run(context=context)
            logger.info(f"LLM response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error in LLM request: {e}")
            return "Error in processing the task with LLM."

    def _format_task_history(self) -> str:
        history = "\n".join([f"- {task}" for task in self.task_history[-5:]])  # Last 5 tasks
        return history if history else "No recent tasks."

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.subtask.description}")

            # Get LLM suggestion
            llm_suggestion = await self.get_llm_response(
                data.subtask.description
            )

            # Simulate task execution using LLM suggestion
            # await asyncio.sleep(2)
            result = f"{self.details().name} completed the subtask: {data.subtask.description}\nLLM suggestion: {llm_suggestion}"

            # # Update task history
            # self.task_history.append(data.subtask.description)
            # if len(self.task_history) > 10:
            #     self.task_history.pop(0)

            await self.broadcast_data(
                TaskResult(task_id=data.task.id, subtask_id=data.subtask.id, agent=self.details().name, result=result)
            )

    @on_message(type=TaskResult)
    async def other_agents_results(self, result: TaskResult):
        logger.info(
            f"Received result for subtask {result.subtask_id} of task {result.task_id} from {result.agent}: {result.result}")
