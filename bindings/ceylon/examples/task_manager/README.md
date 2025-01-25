# Task Management System Tutorial

## Introduction
This tutorial walks through building a distributed task management system using Ceylon. The system assigns tasks to workers based on skill levels and monitors completion success.

## Prerequisites
- Python 3.7+
- Ceylon framework
- Basic understanding of async programming

## Part 1: Data Models

### Task Definition
```python
@dataclass
class Task:
    id: int
    description: str
    difficulty: int
```

Tasks have three key attributes:
- `id`: Unique identifier
- `description`: Task details
- `difficulty`: Required skill level (1-10)

### Message Types
```python
@dataclass
class TaskAssignment:
    task: Task

@dataclass
class TaskResult:
    task_id: int
    worker: str
    success: bool
```

These classes handle:
- Task assignments to workers
- Results reporting back to manager

## Part 2: Worker Implementation

```python
class WorkerAgent(BaseAgent):
    def __init__(self, name: str, skill_level: int,
                 workspace_id=DEFAULT_WORKSPACE_ID,
                 admin_peer=""):
        self.name = name
        self.skill_level = skill_level
        self.has_task = False
        super().__init__(
            name=name,
            workspace_id=workspace_id,
            admin_peer=admin_peer,
            mode=PeerMode.CLIENT
        )
```

Key worker features:
1. Skill level determines task success probability
2. Track task assignment status
3. Connect to task manager via admin_peer

### Task Handling
```python
@on(TaskAssignment)
async def handle_task(self, data: TaskAssignment, time: int, agent: AgentDetail):
    if self.has_task:
        return

    self.has_task = True
    await asyncio.sleep(data.task.difficulty)  # Simulate work
    success = self.skill_level >= data.task.difficulty

    result = TaskResult(
        task_id=data.task.id,
        worker=self.name,
        success=success
    )
    await self.broadcast(pickle.dumps(result))
```

This method:
1. Checks if worker is available
2. Simulates work duration based on difficulty
3. Determines success based on skill level
4. Reports result back to manager

## Part 3: Task Manager Implementation

```python
class TaskManager(BaseAgent):
    def __init__(self, tasks: List[Task], expected_workers: int,
                 name="task_manager", port=8000):
        super().__init__(
            name=name,
            port=port,
            mode=PeerMode.ADMIN,
            role="task_manager"
        )
        self.tasks = tasks
        self.expected_workers = expected_workers
        self.task_results = []
        self.tasks_assigned = False
```

Manager responsibilities:
1. Track available tasks
2. Monitor connected workers
3. Collect and process results

### Connection Handling
```python
@on_connect("*")
async def handle_connection(self, topic: str, agent: AgentDetail):
    connected_count = len(await self.get_connected_agents())
    if connected_count == self.expected_workers and not self.tasks_assigned:
        await self.assign_tasks()
```

Starts task assignment when all workers connect.

### Task Assignment
```python
async def assign_tasks(self):
    if self.tasks_assigned:
        return

    self.tasks_assigned = True
    connected_workers = await self.get_connected_agents()
    for task, worker in zip(self.tasks, connected_workers):
        await self.broadcast(pickle.dumps(TaskAssignment(task=task)))
```

Distribution logic:
1. Checks if tasks already assigned
2. Gets connected worker list
3. Pairs tasks with workers
4. Broadcasts assignments

### Result Processing
```python
@on(TaskResult)
async def handle_result(self, data: TaskResult, time: int, agent: AgentDetail):
    self.task_results.append(data)
    if len(self.task_results) == len(self.tasks):
        print("All tasks completed")
        for result in self.task_results:
            print(f"Task {result.task_id} assigned to {result.worker} - "
                  f"{'Success' if result.success else 'Failure'}")
        await self.end_task_management()
```

Tracks completion and calculates success rate.

## Part 4: System Setup

```python
async def main():
    # Define tasks
    tasks = [
        Task(id=1, description="Simple calculation", difficulty=2),
        Task(id=2, description="Data analysis", difficulty=5),
        Task(id=3, description="ML model training", difficulty=8),
    ]

    # Create manager
    task_manager = TaskManager(tasks, expected_workers=3)
    admin_details = task_manager.details()

    # Create workers with varying skills
    workers = [
        WorkerAgent("Junior", skill_level=3, admin_peer=admin_details.id),
        WorkerAgent("Intermediate", skill_level=6, admin_peer=admin_details.id),
        WorkerAgent("Senior", skill_level=9, admin_peer=admin_details.id),
    ]

    # Start system
    await task_manager.start_agent(b"", workers)
```

## Running the System

1. Create task list with varying difficulties
2. Initialize task manager
3. Create workers with appropriate skill levels
4. Launch system with manager and workers

## Example Output
```
All tasks completed
Task 1 assigned to Junior - Success
Task 2 assigned to Intermediate - Success
Task 3 assigned to Senior - Success
Success rate: 100.00%
```

## Customization Options

### Priority-based Tasks
```python
@dataclass
class PriorityTask(Task):
    priority: int

    def get_processing_time(self):
        return self.difficulty * (1/self.priority)
```

### Specialized Workers
```python
class SpecializedWorker(WorkerAgent):
    def __init__(self, name, skill_level, specialties):
        super().__init__(name, skill_level)
        self.specialties = specialties

    async def handle_task(self, data: TaskAssignment):
        specialty_bonus = 2 if data.task.type in self.specialties else 0
        success = (self.skill_level + specialty_bonus) >= data.task.difficulty
        # Rest of implementation...
```

## Best Practices

1. Task Design
   - Set appropriate difficulty levels
   - Balance task distribution
   - Consider task dependencies

2. Worker Configuration
   - Match skill levels to task range
   - Provide adequate worker count
   - Consider specializations

3. Error Handling
   - Handle worker disconnections
   - Implement task timeouts
   - Plan for task failures

## Troubleshooting

Common issues and solutions:
1. Workers not connecting
   - Check admin_peer ID
   - Verify network configuration
   - Ensure port availability

2. Task assignment failures
   - Verify task format
   - Check worker availability
   - Monitor connection status

3. Performance issues
   - Adjust task difficulty
   - Balance worker load
   - Monitor system resources