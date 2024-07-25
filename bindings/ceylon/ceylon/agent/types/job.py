from typing import List

from pydantic import BaseModel, Field


class Step(BaseModel):
    '''the step'''
    worker: str = Field(description="the worker name of the step")
    dependencies: List[str] = Field(description="the dependencies of the step, these steps must be another step worker",
                                    default=[])
    explanation: str = Field(description="the explanation of the step", default="")

    class Config:
        arbitrary_types_allowed = True


class JobSteps(BaseModel):
    '''the steps of the job'''
    steps: List[Step] = Field(description="the steps of the job", default=[])

    def step(self, worker: str):
        '''get the next step of the job'''
        for step in self.steps:
            if step.worker == worker:
                return step
        return None


class JobRequest(BaseModel):
    steps: JobSteps

    class Config:
        arbitrary_types_allowed = True
