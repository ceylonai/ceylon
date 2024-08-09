import uuid
from typing import Any

from pydantic import BaseModel, Field

from .job_step import Step


class AgentJobStepRequest(BaseModel):
    """ the agent job step request"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id', description="the id of the request")
    job_id: str = Field(None, description="the job id")
    worker: str = Field(description="the worker name")
    job_data: Any = Field(None, description="the job data")
    step: Step = Field(None, description="the step")


class AgentJobResponse(BaseModel):
    """
    the agent job response
    this is the response that is sent back to the agent
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id', description="the id of the response")
    job_id: str = Field(None, description="the job id of the response")
    worker: str = Field(description="the worker name")
    job_data: Any = Field(None, description="the job data")
