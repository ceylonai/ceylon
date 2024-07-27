from typing import Any, List

from langchain_core.tools import render_text_description

from ceylon import Agent, AgentJobStepRequest, AgentJobResponse
from ceylon.llm.llm.llm_executor import LLMExecutor
from ceylon.llm.prompt import PromptMessage
from ceylon.llm.types.agent import AgentDefinition


def render_history(history: List[AgentJobResponse]):
    text = ""
    for h in history:
        text = f"{text}\n{h.worker}-{h.job_data['response']}\n"
    return text


class LLMAgent(Agent):
    class Config:
        arbitrary_types_allowed = True

    def __init__(self,
                 name: str,
                 role: str,
                 objective: str,
                 context: str,
                 tools: list = [],
                 llm: Any = None
                 ):
        self.tools = tools
        tool_names = render_text_description(self.tools)
        self.definition = AgentDefinition(
            name=name,
            role=role,
            objective=objective,
            context=context,
            tools=tool_names
        )
        self.llm = llm
        super().__init__(name=name, role=role)

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        pm = PromptMessage(paths=[
            "prompts.job.step_history",
            "prompts.agent",
            "prompts.job.step_execution_with_tools" if self.tools else "prompts.job.step_execution"
        ])

        prompt_wrapper = pm.build(name=self.details().name,
                                  role=self.details().role,
                                  objective=self.definition.objective,
                                  context=self.definition.context,
                                  tools=self.definition.tools,
                                  history=render_history(self.history_responses),
                                  explanation=request.step.explanation + " " + request.job_data)
        executor = LLMExecutor(llm=self.llm, type="llm_executor")
        llm_response = executor.execute(prompt_wrapper, tools=self.tools)
        return AgentJobResponse(
            worker=self.details().name,
            job_data={"response": llm_response}
        )
