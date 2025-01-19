## Building a Distributed Task Management System with Ceylon

### Overview

In this tutorial, you'll learn how to create a distributed task management system using Python. This system will distribute tasks to worker agents based on their skill levels, execute the tasks asynchronously, and collect the results. We will use several Python libraries including `asyncio`, `ceylon`, and `loguru` for logging.

### Prerequisites

Before starting, ensure you have the following Python packages installed:

```bash
pip install loguru ceylon
```

### Step 1: Define Data Structures

We'll start by defining the data structures that will represent tasks, task assignments, and task results using Python's dataclasses.

```python
from dataclasses import dataclass

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

The `WorkerAgent` class represents a worker that performs tasks. Each worker has a name and a skill level that determines its ability to complete tasks of varying difficulties. We inherit from Ceylon's `Worker` class.

```python
import asyncio
import pickle
from ceylon.base.agents import Worker
from loguru import logger

class WorkerAgent(Worker):
    def __init__(self, name: str, skill_level: int, 
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer="",
                 admin_port=8000):
        self.name = name
        self.skill_level = skill_level
        self.has_task = False
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            admin_port=admin_port
        )
        logger.info(f"Worker {name} initialized with skill level {skill_level}")

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)
            
            if isinstance(message, TaskAssignment) and not self.has_task:
                logger.info(f"{self.name} received task: {message.task.description}")
                self.has_task = True
                
                # Simulate task execution
                await asyncio.sleep(message.task.difficulty)
                success = self.skill_level >= message.task.difficulty
                
                result = TaskResult(task_id=message.task.id, worker=self.name, success=success)
                await self.broadcast(pickle.dumps(result))
                logger.info(f"{self.name} completed task {message.task.id} with success={success}")
                
        except Exception as e:
            logger.error(f"Error processing message in worker: {e}")
```

### Step 3: Create the Task Manager

The `TaskManager` class is responsible for assigning tasks to workers and collecting the results. We inherit from Ceylon's `Admin` class.

```python
from ceylon.base.agents import Admin

class TaskManager(Admin):
    def __init__(self, tasks: List[Task], expected_workers: int, 
                 name="task_manager", port=8000):
        super().__init__(name=name, port=port)
        self.tasks = tasks
        self.expected_workers = expected_workers
        self.task_results = []
        self.tasks_assigned = False
        logger.info(f"Task Manager initialized with {len(tasks)} tasks")

    async def on_agent_connected(self, topic: str, agent_id: str):
        await super().on_agent_connected(topic, agent_id)
        connected_count = len(self.get_connected_agents())
        logger.info(f"Worker connected. {connected_count}/{self.expected_workers} workers connected.")

        if connected_count == self.expected_workers and not self.tasks_assigned:
            logger.info("All workers connected. Starting task distribution.")
            await self.assign_tasks()

    async def assign_tasks(self):
        if self.tasks_assigned:
            return
            
        self.tasks_assigned = True
        connected_workers = self.get_connected_agents()
        
        for task, worker in zip(self.tasks, connected_workers):
            assignment = TaskAssignment(task=task)
            await self.broadcast(pickle.dumps(assignment))
            logger.info(f"Assigned task {task.id} to worker {worker.name}")

    async def on_message(self, agent_id: str, data: bytes, time: int):
        try:
            message = pickle.loads(data)
            if isinstance(message, TaskResult):
                self.task_results.append(message)
                logger.info(
                    f"Received result for task {message.task_id} from {message.worker}: "
                    f"{'Success' if message.success else 'Failure'}"
                )
                
                if len(self.task_results) == len(self.tasks):
                    await self.end_task_management()
                    
        except Exception as e:
            logger.error(f"Error processing message in manager: {e}")
```

### Step 4: Main Execution Script

Finally, we need a script to create tasks, instantiate workers, and run the task manager.

```python
async def main():
    # Create tasks
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="Machine learning model training", difficulty=8),
    ]

    # Create task manager
    task_manager = TaskManager(tasks, expected_workers=3)
    admin_details = task_manager.details()

    # Create workers with proper admin_peer
    workers = [
        WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id),
        WorkerAgent("Intermediate", skill_level=6, admin_peer=admin_details.id),
        WorkerAgent("Senior", skill_level=9, admin_peer=admin_details.id),
    ]

    try:
        logger.info("Starting task management system...")
        await task_manager.arun_admin(b"", workers)
    except KeyboardInterrupt:
        logger.info("Shutting down task management system...")

if __name__ == "__main__":
    logger.info("Initializing task management system...")
    asyncio.run(main())
```

### Running the System

To run the distributed task management system:

1. Save the code as `task_management.py`
2. Ensure you have the required dependencies installed
3. Run the script:
```bash
python task_management.py
```

The system will:
- Create three workers with different skill levels
- Assign tasks of varying difficulty
- Execute tasks asynchronously
- Show detailed results including success/failure status for each task
- Calculate and display the overall success rate

### Key Features

- Asynchronous task execution
- Skill-based task assignment
- Proper message serialization using pickle
- Robust error handling
- Detailed logging of system events
- Connection state tracking
- Task completion monitoring
- Success rate calculation

### Implementation Notes

- Workers use broadcast messaging for task results
- Task Manager tracks worker connections
- Task assignments are only made once all workers are connected
- Each worker tracks its task state to prevent duplicate processing
- System uses proper serialization for message passing

---

Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
Licensed under the Apache License, Version 2.0 (See LICENSE or http://www.apache.org/licenses/LICENSE-2.0).