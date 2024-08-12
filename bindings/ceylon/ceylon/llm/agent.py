import copy
from typing import Dict, List, Set, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import Agent, on_message
from ceylon.llm import TaskAssignment, TaskResult
from tasks.task_agent import SubTask


class SpecializedAgent(Agent):
    def __init__(self, name: str, role: str, context: str, skills: List[str],
                 tools: List[Any] = None, llm=None, tool_llm=None):
        self.context = context
        self.skills = skills
        self.tools = tools if tools else []
        self.task_history = []
        self.llm = copy.copy(llm)
        self.tool_llm = copy.copy(tool_llm)
        self.history: Dict[str, List[TaskResult]] = {}
        super().__init__(name=name, role=role, workspace_id="openai_task_management", admin_port=8000)

    async def get_llm_response(self, subtask: SubTask) -> str:

        # Construct the agent profile context
        agent_profile = f"""
        Hello, {self.details().name}.
        You are a {self.details().role} {self.context}.
        
        Your key skills include:
            {', '.join(self.skills)}
        
        """

        # Construct the task information context
        task_info = f"""
          I need you to finish the following task,
            {subtask.name},{subtask.description}
             
             Here are some additional information to help you:
               {self._format_task_history(subtask.id, subtask.depends_on)}
               Ensure these results are sufficient for executing the subtask.
               
            
            Give most successful response for {subtask.name}
            
            """

        if len(self.tools) > 0 and self.tool_llm:
            tool_llm = self.tool_llm
            tool_llm = tool_llm.bind_tools(self.tools)
        else:
            tool_llm = self.llm

        # Create the prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content=f"{agent_profile}"),
            HumanMessage(
                content=f"{task_info}")
        ])

        try:
            runnable = prompt_template | tool_llm | StrOutputParser()
            response = runnable.invoke({
                agent_profile: agent_profile,
                task_info: task_info
            })
            return response
        except Exception as e:
            raise e
            logger.error(f"Error in LLM request: {e}")
            return "Error in processing the task with LLM."

    def _format_task_history(self, task_id, depends_on: Set[str]) -> str:
        if task_id not in self.history:
            return ""

        results = []
        for rest_his in self.history[task_id]:
            if rest_his.name in depends_on:
                results.append(f"{rest_his.name}: {rest_his.result}\n")
        return "\n".join(results)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.task.description}")
            result = await self.get_llm_response(data.task)
            result_task = TaskResult(task_id=data.task.id,
                                     name=data.task.name,
                                     description=data.task.description,
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
