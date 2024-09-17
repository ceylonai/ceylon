from dataclasses import field, dataclass
from typing import List
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

    # Define possible states
    states = [
        State(name='pending'),
        State(name='approved'),
        State(name='in_progress'),
        State(name='completed'),
        State(name='failed')
    ]

    # Define transitions
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

    # Condition methods
    def can_start(self):
        return all(dep.state == 'completed' for dep in self.dependencies)

    def can_retry(self):
        return self.retry_count < self.max_retries

    # Callback methods
    def handle_failure(self):
        self.retry_count += 1
        print(f"SubTask '{self.name}' failed. Retry count: {self.retry_count}")


@dataclass
class Task:
    name: str
    subtasks: List[SubTask] = field(default_factory=list)

    def all_subtasks_completed(self):
        return all(subtask.state == 'completed' for subtask in self.subtasks)
