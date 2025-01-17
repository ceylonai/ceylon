import copy
from typing import Dict, List, Set, Any

from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from loguru import logger

from ceylon.task import SubTaskResult
from ceylon.task.task_operation import SubTask
from ceylon.task.task_operator import TaskOperator


class LLMTaskOperator(TaskOperator):
    """LLM-based task operator."""
    agent_type = "LLM_TASK_OPERATOR"

    def __init__(self, name: str, role: str, context: str, skills: List[str],
                 tools: List[Any] = None, llm=None, tool_llm=None, verbose=False,
                 config_file=None,
                 workspace_id="ceylon_agent_stack",
                 extra_instructions="",
                 admin_port=8888, ):
        self.context = context
        self.extra_instructions = extra_instructions
        self.verbose = verbose
        self.tools = tools if tools else []
        self.task_history = []
        self.skills = skills
        self.llm = copy.copy(llm)
        self.tool_llm = copy.copy(tool_llm)
        self.history: Dict[str, List[SubTaskResult]] = {}
        super().__init__(name=name, role=role, workspace_id=workspace_id, admin_port=admin_port, conf_file=config_file)

    async def get_result(self, task):
        return await self.get_llm_response(task)

    async def get_llm_response(self, subtask: SubTask) -> str:
        agent_profile = f"You are {self.details().name}, a {self.details().role} {self.context}. Your key skills include: {', '.join(self.skills)}"

        task_info = f"""
        Task: {subtask.name}
        Description: {subtask.description}
        Expected Output: {subtask.expected_output}

        Additional context:
        {self._format_task_history(subtask.parent_task_id, subtask.depends_on)}

        Objective: Provide the most successful response for completing {subtask.name}.
        """

        try:
            if self.tools:
                return await self._execute_react_agent(agent_profile, task_info)
            else:
                return await self._execute_simple_llm(agent_profile, task_info)
        except Exception as e:
            logger.error(f"Error in LLM request: {e}")
            return f"Error in processing the task: {str(e)}"

    async def _execute_react_agent(self, agent_profile: str, task_info: str) -> str:
        system_template = """
        {agent_profile}
            Use the following format:
    
            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of {tool_names}
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
    
            Final Answer: the final answer to the original input question
        """

        human_template = """
                Question: {input}
                Tools: {tools}
                Extra Instruction: {extra_instructions}
                {agent_scratchpad}
                Thought:
        """

        chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template(human_template)
        ])

        react_agent = create_react_agent(self.llm, self.tools, prompt=chat_prompt)
        agent_executor = AgentExecutor(agent=react_agent, tools=self.tools, verbose=self.verbose,
                                       handle_parsing_errors=True)

        response = await agent_executor.ainvoke({
            "agent_profile": agent_profile,
            "input": task_info,
            "extra_instructions": self.extra_instructions,
            "tools": "\n".join(f"{tool.name}: {tool.description}" for tool in self.tools),
            "agent_scratchpad": "",
            "tool_names": [tool.name for tool in self.tools],
        })

        return response["output"]

    async def _execute_simple_llm(self, agent_profile: str, task_info: str) -> str:
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=agent_profile),
            HumanMessage(content=task_info)
        ])

        runnable = prompt_template | self.llm | StrOutputParser()
        return await runnable.ainvoke({})

    def _format_task_history(self, task_id, depends_on: Set[str]) -> str:
        if task_id not in self.history:
            return ""

        results = []
        len_history = 0
        for rest_his in self.history[task_id]:
            if rest_his.name in depends_on:
                results.append(f"{rest_his.name}: {rest_his.result}\n")
                len_history += 1
        if len_history == 0:
            return ""
        logger.info(f"Task history length: {len_history}")
        return "\n".join(results)