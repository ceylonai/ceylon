from typing import List

from pydantic import BaseModel, Field, PrivateAttr

from ceylon.llm.prompt import PromptMessage
from ceylon.llm.types.agent import AgentDefinition


class StepHistory(BaseModel):
    '''the step history'''
    worker: str = Field(description="the worker name of the step")
    result: str = Field(description="the result of the step")

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.step_history"),
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def prompt(self):
        return self._prompt.build(worker=self.worker, result=self.result)


class StepExecution(BaseModel):
    '''the step execution'''
    explanation: str = Field(description="the explanation of the step")
    worker: AgentDefinition = Field(description="the worker name of the step")
    dependencies: List[StepHistory] = Field(
        description="the dependencies of the step, these steps must be another step worker",
        default=[]
    )

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.step_execution"),
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def prompt(self):
        worker_prompt = self.worker.prompt
        return self._prompt.build(
            worker=worker_prompt.invoke(),
            dependencies=[d.prompt for d in self.dependencies],
            explanation=self.explanation
        )
