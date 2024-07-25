from typing import Any

from pydantic import BaseModel, Field


class AgentJobStepRequest(BaseModel):
    worker: str = Field(description="the worker name")
    job_data: Any = Field(None, description="the job data")


class AgentJobResponse(BaseModel):
    worker: str = Field(description="the worker name")
    job_data: Any = Field(None, description="the job data")
