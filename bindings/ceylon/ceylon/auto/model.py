from dataclasses import field, dataclass
from typing import Any, Dict, List
from uuid import uuid4

from pydantic import BaseModel
from transitions import Machine, State


@dataclass
class SubTask:
    name: str
    executor: str
    needs_approval: bool
    dependencies: List['SubTask'] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2
    state: str = 'pending'
    inputs_needed: List[str] = field(default_factory=list)
    inputs_provided: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))

    states = [
        State(name='pending'),
        State(name='approved'),
        State(name='in_progress'),
        State(name='completed'),
        State(name='failed')
    ]

    transitions = [
        {'trigger': 'approve', 'source': 'pending', 'dest': 'approved', 'conditions': 'needs_approval'},
        {'trigger': 'start', 'source': ['approved', 'pending'], 'dest': 'in_progress', 'conditions': 'can_start'},
        {'trigger': 'complete', 'source': 'in_progress', 'dest': 'completed'},
        {'trigger': 'fail', 'source': 'in_progress', 'dest': 'failed', 'after': 'handle_failure'},
        {'trigger': 'retry', 'source': 'failed', 'dest': 'in_progress', 'conditions': 'can_retry'},
    ]

    def __post_init__(self):
        self.machine = Machine(
            model=self,
            states=SubTask.states,
            transitions=SubTask.transitions,
            initial=self.state
        )

    def can_start(self):
        dependencies_completed = all(dep.state == 'completed' for dep in self.dependencies)
        return dependencies_completed and self.has_all_inputs()

    def has_all_inputs(self):
        return all(input_name in self.inputs_provided for input_name in self.inputs_needed)

    def can_retry(self):
        return self.retry_count < self.max_retries

    def handle_failure(self):
        self.retry_count += 1
        print(f"SubTask '{self.name}' failed. Retry count: {self.retry_count}")


@dataclass
class Task:
    name: str
    subtasks: List[SubTask] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))

    def all_subtasks_completed(self):
        return all(subtask.state == 'completed' for subtask in self.subtasks)


class SubTaskRequest(BaseModel):
    task_id: str  # id of the parent task
    subtask_name: str  # name of the sub task
    inputs: Dict[str, Any]  # inputs provided by the user
    dependencies: List[str]  # list of sub task names
