## Building a Distributed Task Management System with Ceylon

### Overview

In this tutorial, you'll learn how to create a distributed task management system using Python. This system will distribute tasks to worker agents based on their skill levels, execute the tasks asynchronously, and collect the results. We will use several Python libraries including `asyncio`, `pydantic`, and a custom distributed agent system called `ceylon`.

### Prerequisites

Before starting, ensure you have the following Python packages installed:

- `asyncio`: For asynchronous task handling.
- `pydantic`: For data validation and management.
- `loguru`: For logging.
- `ceylon`: For creating distributed agents.

You can install the necessary packages using pip:

```bash
pip install pydantic loguru ceylon
```

### Step 1: Define Data Structures

We'll start by defining the data structures that will represent tasks, task assignments, and task results.

```python
from pydantic.dataclasses import dataclass

@dataclass
class Task:
    id: int
    description: str
    difficulty: int  # 1-10 scale


@dataclass
class TaskAssignment:
    task: Task


@dataclass
class TaskResult:
    task_id: int
    worker: str
    success: bool
```

### Step 2: Create the Worker Agent

The `WorkerAgent` class represents a worker that performs tasks. Each worker has a name and a skill level that determines its ability to complete tasks of varying difficulties.

```python
import asyncio
from ceylon import Agent, on_message
from loguru import logger

class WorkerAgent(Agent):
    def __init__(self, name: str, skill_level: int):
        self.name = name
        self.skill_level = skill_level
        super().__init__(name=name, workspace_id="task_management", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        logger.info(f"{self.name} received task: {data.task.description}")
        # Simulate task execution
        await asyncio.sleep(data.task.difficulty)
        success = self.skill_level >= data.task.difficulty
        await self.broadcast_data(TaskResult(task_id=data.task.id, worker=self.name, success=success))
```

### Step 3: Create the Task Manager

The `TaskManager` class is responsible for assigning tasks to workers and collecting the results.

```python
from ceylon import CoreAdmin

class TaskManager(CoreAdmin):
    tasks = []
    workers = []
    task_results = []

    def __init__(self, tasks, workers):
        self.workers = workers
        self.tasks = tasks
        super().__init__(name="task_management", port=8000)

    async def on_agent_connected(self, topic: str, agent_id: AgentDetail):
        logger.info(f"Worker {agent_id} connected")
        if len(self.workers) == len(self.tasks):
            await self.assign_tasks()

    async def assign_tasks(self):
        for task, worker in zip(self.tasks, self.workers):
            await self.broadcast_data(TaskAssignment(task=task))

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        self.task_results.append(result)
        logger.info(
            f"Received result for task {result.task_id} from {result.worker}: {'Success' if result.success else 'Failure'}")
        if len(self.task_results) == len(self.tasks):
            await self.end_task_management()

    async def end_task_management(self):
        success_rate = sum(1 for result in self.task_results if result.success) / len(self.task_results)
        logger.info(f"All tasks completed. Success rate: {success_rate:.2%}")
        await self.stop()
```

### Step 4: Main Execution Script

Finally, we need a script to create tasks, instantiate workers, and run the task manager.

```python
if __name__ == '__main__':
    # Create tasks
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="Machine learning model training", difficulty=8),
    ]

    # Create workers
    workers = [
        WorkerAgent("Junior", skill_level=3),
        WorkerAgent("Intermediate", skill_level=6),
        WorkerAgent("Senior", skill_level=9),
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, workers)
    task_manager.run_admin(inputs=b"", workers=workers)
```

### Running the System

To run the distributed task management system, simply execute the main script. The `TaskManager` will distribute tasks to workers based on their skill levels, and each worker will either succeed or fail in completing the task. The results will be collected and logged.