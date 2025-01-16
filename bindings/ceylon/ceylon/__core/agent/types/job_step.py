import uuid
from typing import List

from pydantic import BaseModel, Field


class Step(BaseModel):
    '''the step'''
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias='_id')
    worker: str = Field(description="the worker name of the step")
    dependencies: List[str] = Field(description="the dependencies of the step, these steps must be another step worker",
                                    default=[])
    explanation: str = Field(description="the explanation of the step", default="")

    class Config:
        arbitrary_types_allowed = True
