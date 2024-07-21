from typing import List, Optional

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


class AgentDefinition(BaseModel):
    name: str
    role: str
    role_description: str
    responsibilities: List[str]
    skills: List[str]
    tools: List[str] = []
    knowledge_domains: Optional[List[str]] = []
    interaction_style: Optional[str] = None
    operational_parameters: Optional[str] = None
    performance_objectives: Optional[List[str]] = []
    version: Optional[str] = None

    @property
    def intro(self):
        return {
            "name": self.name,
            "role": self.role,
            "role_description": self.role_description,
        }


class LLMAgentResponse(BaseModel):
    time: float
    agent_id: str
    agent_name: str
    response: str


class LLMAgentRequest(BaseModel):
    name: str
    user_inputs: dict
    history: dict
