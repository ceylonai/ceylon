# Task Management System Tutorial

A distributed system for automatically assigning tasks to workers based on skill requirements.

## Use Case

This system simulates a skill-based task assignment scenario where:
- Tasks have different difficulty levels
- Workers have varying skill levels
- Tasks are automatically assigned to available workers
- Task completion success depends on worker skill vs task difficulty

## Quick Start

```python
import asyncio
from task_manager import TaskManager, WorkerAgent, Task

async def main():
    # Create tasks with varying difficulty
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="ML model training", difficulty=8),
    ]

    # Initialize task manager
    task_manager = TaskManager(tasks, expected_workers=3)
    admin_details = task_manager.details()

    # Create workers with different skill levels
    workers = [
        WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id),
        WorkerAgent("Intermediate", skill_level=6, admin_peer=admin_details.id),
        WorkerAgent("Senior", skill_level=9, admin_peer=admin_details.id),
    ]

    # Start the system
    await task_manager.start_agent(b"", workers)

asyncio.run(main())
```

## System Flow

1. **Task Manager Initialization**
   ```python
   task_manager = TaskManager(tasks, expected_workers=3)
   ```

2. **Worker Registration**
   ```python
   WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id)
   ```

3. **Task Assignment**
   ```python
   @on_connect("*")
   async def handle_connection(self, topic: str, agent: AgentDetail):
       if connected_count == self.expected_workers:
           await self.assign_tasks()
   ```

4. **Task Execution**
   ```python
   @on(TaskAssignment)
   async def handle_task(self, data: TaskAssignment, time: int, agent: AgentDetail):
       success = self.skill_level >= data.task.difficulty
   ```

## Customization

Add task priorities:
```python
@dataclass
class Task:
    id: int
    description: str
    difficulty: int
    priority: int = 1
```

Implement worker specialization:
```python
class WorkerAgent(BaseAgent):
    def __init__(self, name: str, skill_level: int, specialties: List[str]):
        self.specialties = specialties
```

## License
Apache License, Version 2.0