from typing import List

import pydantic
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, PrivateAttr

from ceylon.llm.prompt import PromptMessage
from ceylon.llm.types.agent import AgentDefinition


class InputData(BaseModel):
    '''the input data'''
    data: dict = Field(description="the data of the input")

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.input"),
    )

    class Config:
        arbitrary_types_allowed = True


class OutputData(BaseModel):
    '''the output data'''
    data: dict = Field(description="the data of the output")
    format: str = Field(description="the format of the output", default="json")

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.output"),
    )

    class Config:
        arbitrary_types_allowed = True


class JobWorker(BaseModel):
    '''the job worker'''
    name: str = Field(description="the name of the job worker")
    role: str = Field(description="the role of the job worker")

    @staticmethod
    def from_agent_definition(agent_definition: AgentDefinition):
        '''create a job worker from an agent definition'''
        return JobWorker(
            name=agent_definition.name,
            role=agent_definition.role
        )

    def __str__(self):
        return self.model_dump_json()


class Step(BaseModel):
    '''the step'''
    worker: str = Field(description="the worker name of the step")
    dependencies: List[str] = Field(description="the dependencies of the step, these steps must be another step worker",
                                    default=[])
    explanation: str = Field(description="the explanation of the step", default="")

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.step"),
    )

    class Config:
        arbitrary_types_allowed = True


class JobSteps(BaseModel):
    '''the steps of the job'''
    steps: List[Step] = Field(description="the steps of the job", default=[])

    def step(self, worker: str) -> Step:
        '''get the next step of the job'''
        for step in self.steps:
            if step.worker == worker:
                return step

        return None


class Stepv1(pydantic.v1.BaseModel):
    '''the step'''
    worker: str = pydantic.v1.Field(description="the worker name of the step")
    dependencies: List[str] = pydantic.v1.Field(
        description="the dependencies of the step, these steps must be another step worker",
        default=[])

    def to_latest(self):
        return Step(worker=self.worker, dependencies=self.dependencies, explanation=self.explanation)


class JobStepsV1(pydantic.v1.BaseModel):
    '''the steps of the job'''
    steps: List[Stepv1] = pydantic.v1.Field(description="the steps of the job")

    def to_latest(self):
        return JobSteps(steps=[self.step.to_latest() for self.step in self.steps])

    class Config:
        arbitrary_types_allowed = True


class Job(BaseModel):
    title: str = Field(description="the title of the job. This should be a string containing the title of the job.")
    explanation: str = Field(
        description="the explanation of the job. This should be a string containing the explanation of the job.")
    result: str = Field(description="the result of the job.", default="")
    workers: List[JobWorker] = Field(
        description="the workers of the job. This should be a list of dictionaries, where each dictionary contains the following keys: name (str), role (str).",
        default=[])

    steps: JobSteps = Field(description="the steps of the job", default=JobSteps(steps=[]))

    _prompt: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.job"),
    )

    _prompt_planning: PromptMessage = PrivateAttr(
        default=PromptMessage(path="prompts.job.job_planning"),
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def prompt_planning(self):
        return self._prompt_planning.build(title=self.title, explanation=self.explanation,
                                           workers=[str(worker) for worker in self.workers],
                                           pydantic_object=JobSteps)
