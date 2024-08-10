from typing import List

from pydantic.v1 import BaseModel, Field


class SubTask(BaseModel):
    id: int = Field(description="the id of the subtask")
    description: str = Field(description="the description of the subtask, Explains the task in detail")
    required_specialty: str = Field(description="the required specialty of the subtask")
    dependencies: List[int] = Field(description="the dependencies of the subtask", default=[])


class SubTaskList(BaseModel):
    subtasks: List[SubTask]


class Task(BaseModel):
    """
    id: int
    description: str
    subtasks: List[SubTask]
    """
    id: int = Field(description="the id of the task")
    description: str = Field(description="the description of the task")
    subtasks: List[SubTask] = Field(description="the subtasks of the task", default=[])


class TaskAssignment(BaseModel):
    task: Task = Field(description="the task assigned to the agent")
    subtask: SubTask = Field(description="the subtask assigned to the agent")
    assigned_agent: str = Field(description="the agent assigned to the subtask")


class TaskResult(BaseModel):
    task_id: int = Field(description="the id of the task")
    subtask_id: int = Field(description="the id of the subtask")
    agent: str = Field(description="the agent who completed the subtask")
    result: str = Field(description="the result of the subtask")
