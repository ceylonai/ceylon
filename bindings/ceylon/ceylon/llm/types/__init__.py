from typing import List

from pydantic.v1 import BaseModel, Field





class LLMAgentResponse(BaseModel):
    time: float
    agent_id: str
    agent_name: str
    response: str


class LLMAgentRequest(BaseModel):
    name: str
    user_inputs: str
    history: dict
