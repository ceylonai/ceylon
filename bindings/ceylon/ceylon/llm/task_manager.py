import enum
from typing import List, Tuple

from pydantic import dataclasses


class TaskStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclasses.dataclass
class Task:
    name: str
    dependencies: List[str]
    status: TaskStatus = TaskStatus.PENDING


class TaskManager:
    def __init__(self, tasks: List[Task] = None):
        self.tasks = tasks or []

    def add_tasks(self, tasks: List[Task]):
        self.tasks.extend(tasks)

    def add_dependencies(self, task_name: str, dependencies: List[str]):
        task = next((task for task in self.tasks if task.name == task_name), None)
        if task:
            task.dependencies.extend(dependencies)

    def update_status(self, task_name: str, status: TaskStatus) -> bool:
        task = next((task for task in self.tasks if task.name == task_name), None)
        if task:
            if status == TaskStatus.RUNNING or status == TaskStatus.COMPLETED:
                can_start, required_tasks = self.can_start_with_required_tasks(task_name)
                if not can_start:
                    print(
                        f"Cannot update task '{task_name}' to '{status.name}'"
                        f" because the following tasks need to be completed first: {required_tasks}")
                    return False
            task.status = status
            return True
        return False

    def find_next_task(self) -> List[Task]:
        tasks: List[Task] = self.tasks
        # Create a dictionary to quickly access task status by name
        task_status = {task.name: task.status for task in tasks}

        # List to hold the names of tasks that can be started next
        next_tasks = []

        # Iterate through each task to find eligible ones
        for task in tasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                if all(task_status[dep] == TaskStatus.COMPLETED for dep in task.dependencies):
                    next_tasks.append(task)

        return next_tasks

    def can_start_with_required_tasks(self, task_name: str) -> Tuple[bool, List[str]]:
        task = next((task for task in self.tasks if task.name == task_name), None)
        if not task:
            return False, []

        required_tasks = self._get_pending_dependencies(task)
        can_start = len(required_tasks) == 0

        return can_start, required_tasks

    def _get_pending_dependencies(self, task: Task) -> List[str]:
        pending_dependencies = []

        for dependency_name in task.dependencies:
            dependency = next((t for t in self.tasks if t.name == dependency_name), None)
            if dependency and dependency.status != TaskStatus.COMPLETED:
                pending_dependencies.append(dependency_name)
                pending_dependencies.extend(self._get_pending_dependencies(dependency))

        return list(set(pending_dependencies))


if __name__ == '__main__':
    tasks = [
        Task(name="task1", dependencies=["task2", "task3"]),
        Task(name="task2", dependencies=["task4"]),
        Task(name="task3", dependencies=["task4"]),
        Task(name="task4", dependencies=[]),
        Task(name="task9", dependencies=[]),
        Task(name="task5", dependencies=["task3"]),
        Task(name="task6", dependencies=["task3"])
    ]

    task_manager = TaskManager(tasks)
    print(task_manager.find_next_task())

    print(task_manager.can_start_with_required_tasks("task1"))

    task_manager.update_status("task4", TaskStatus.COMPLETED)
    print(task_manager.can_start_with_required_tasks("task1"))
    task_manager.update_status("task2", TaskStatus.COMPLETED)
    print(task_manager.can_start_with_required_tasks("task1"))
    task_manager.update_status("task3", TaskStatus.COMPLETED)
    print(task_manager.can_start_with_required_tasks("task1"))