from typing import List

from pydantic.v1 import BaseModel, Field


class Step(BaseModel):
    '''the step'''
    owner: str = Field(description="the owner name of the step")
    dependencies: List[str] = Field(description="the dependencies of the step, these steps must be another step owner")


class Job(BaseModel):
    title: str
    input: dict
    work_order: List[Step]
    visualize: bool = False
    build_workflow: bool = False


class LLMAgentResponse(BaseModel):
    time: float
    agent_id: str
    agent_name: str
    response: str


class LLMAgentRequest(BaseModel):
    name: str
    user_inputs: dict
    history: dict
