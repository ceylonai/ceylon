from typing import List, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class Step(BaseModel):
    owner: str
    dependencies: List[str]


class Job(BaseModel):
    title: str
    input: dict
    work_order: List[Step]
    visualize: bool = False


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


class LLMAgentResponse(BaseModel):
    time: float
    agent_id: str
    agent_name: str
    response: str


class LLMAgentRequest(BaseModel):
    name: str
    user_inputs: dict
    history: List[LLMAgentResponse]
