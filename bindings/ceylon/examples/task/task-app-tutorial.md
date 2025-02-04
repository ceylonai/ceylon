# Ceylon Tutorial: Building a Distributed Task Processing System

This tutorial demonstrates how to build a scalable distributed task processing system using Ceylon. The system includes
task groups, goal-based completion tracking, and multiple worker agents processing tasks concurrently.

## System Overview

The system implements:

- Multiple worker agents processing tasks in parallel
- Task grouping with dependencies and goals
- Progress tracking and completion monitoring
- Configurable concurrency limits per worker
- Goal-based completion criteria

## Prerequisites

- Python 3.8+
- Ceylon framework
- Basic understanding of async Python

## Core Components

````mermaid
flowchart TB
    subgraph Playground[Task Playground]
        TM[Task Manager]
        WR[Worker Registry]
        PM[Progress Monitor]
    end

    subgraph TaskGroup[Task Group]
        Tasks[Tasks]
        Goal[Goal Checker]
        Status[Status Tracker]
    end

    subgraph Workers[Worker Agents]
        W1[Worker 1]
        W2[Worker 2]
        subgraph Queue1[Worker 1 Queue]
            TQ1[Task Queue]
            AT1[Active Tasks]
        end
        subgraph Queue2[Worker 2 Queue]
            TQ2[Task Queue]
            AT2[Active Tasks]
        end
    end

    %% Task Creation and Assignment Flow
    TM --> |Creates| TaskGroup
    Tasks --> |Assigned to| WR
    WR --> |Distributes| TQ1
    WR --> |Distributes| TQ2

    %% Worker Processing Flow
    TQ1 --> |Processes| AT1
    TQ2 --> |Processes| AT2
    AT1 --> |Reports| Status
    AT2 --> |Reports| Status

    %% Progress Monitoring Flow
    Status --> |Updates| PM
    PM --> |Checks| Goal
    Goal --> |Triggers| Complete[Goal Achievement]

    %% Status Updates
    W1 --> |Status Updates| PM
    W2 --> |Status Updates| PM

    %% System Control Flow
    Complete --> |Notifies| TM
    TM --> |Controls| Workers

    %% Styling
    classDef primary fill:#2196f3,stroke:#1976d2,stroke-width:2px,color:white
    classDef secondary fill:#4caf50,stroke:#388e3c,stroke-width:2px,color:white
    classDef accent fill:#ff9800,stroke:#f57c00,stroke-width:2px,color:white
    
    class TM,WR,PM primary
    class Tasks,Goal,Status secondary
    class W1,W2,TQ1,TQ2,AT1,AT2 accent
    class Complete primary
````

### 1. Task Data Models

```python
@dataclass
class TaskMessage:
    task_id: str
    name: str
    description: str
    duration: float
    required_role: str
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskGroup:
    task_id: str
    name: str
    description: str
    subtasks: List[TaskMessage]
    goal: Optional[TaskGroupGoal] = None
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING


@dataclass
class TaskGroupGoal:
    name: str
    description: str
    check_condition: Callable
    success_message: str
    failure_message: str
    status: GoalStatus = GoalStatus.NOT_STARTED
```

### 2. Worker Agent Implementation

The worker agent processes tasks assigned to it:

```python
class TaskExecutionAgent(Worker):
    def __init__(self, name: str, worker_role: str, max_concurrent_tasks: int = 3):
        super().__init__(
            name=name,
            role=worker_role,
        )
        self.worker_role = worker_role
        self.active_tasks = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_queue = asyncio.Queue()
```

### 3. Goal Checker Function

Create a function to check goal completion:

```python
def create_goal_checker(required_tasks: int) -> Callable:
    def check_completion(task_groups: Dict[str, TaskGroup],
                         completed_tasks: Dict[str, TaskMessage]) -> bool:
        completed_group_tasks = sum(
            1 for task in completed_tasks.values()
            if hasattr(task, 'group_id') and
            task.group_id in task_groups
        )
        print(f"Progress: {completed_group_tasks}/{required_tasks} tasks completed")
        return completed_group_tasks >= required_tasks

    return check_completion
```

## Building the System

### 1. Initialize the Playground and Workers

```python
playground = TaskPlayGround()
workers = [
    TaskExecutionAgent("worker1", "processor", max_concurrent_tasks=2),
    TaskExecutionAgent("worker2", "processor", max_concurrent_tasks=2),
]
```

### 2. Create Task Group

```python
processing_group = TaskManager.create_task_group(
    name="Data Processing",
    description="Process 10 data items, goal achieves at 5",
    subtasks=[
        TaskMessage(
            task_id=str(uuid.uuid4()),
            name=f"Process Data Item {i}",
            description=f"Processing task {i}",
            duration=1,
            required_role="processor"
        )
        for i in range(10)
    ],
    goal=TaskGroupGoal(
        name="Partial Processing Complete",
        description="Complete at least 5 processing tasks",
        check_condition=create_goal_checker(required_tasks=5),
        success_message="Successfully completed minimum required tasks!",
        failure_message="Failed to complete minimum required tasks."
    ),
    priority=1
)
```

### 3. Run the System

```python
async with playground.play(workers=workers) as active_playground:
    await active_playground.assign_task_groups([processing_group])

    # Monitor progress
    while True:
        await asyncio.sleep(1)
        current_group = active_playground.task_manager.task_groups[processing_group.id]

        print(f"\nGroup Status: {current_group.status}")
        if current_group.goal:
            print(f"Goal Status: {current_group.goal.status}")

        if (current_group.goal and
                current_group.goal.status == GoalStatus.ACHIEVED):
            print("\nGoal achieved! System can stop while tasks continue.")
            break
```

## System Flow

````mermaid
sequenceDiagram
    participant P as Playground
    participant TM as TaskManager
    participant W1 as Worker1
    participant W2 as Worker2
    participant G as GoalChecker

    Note over P,G: System Initialization
    P->>TM: Create Task Groups
    P->>W1: Initialize Worker
    P->>W2: Initialize Worker
    
    Note over P,G: Task Assignment Phase
    TM->>W1: Assign Tasks
    TM->>W2: Assign Tasks
    
    par Task Processing
        W1->>TM: Process Tasks
        W2->>TM: Process Tasks
    end

    loop Progress Monitoring
        TM->>G: Check Goal Progress
        G-->>TM: Progress Status
        alt Goal Not Met
            TM->>W1: Continue Processing
            TM->>W2: Continue Processing
        else Goal Achieved
            TM->>P: Signal Goal Achievement
            Note over P,G: System can stop while remaining tasks complete
        end
    end

    Note over P,G: System Completion
    P->>W1: Cleanup
    P->>W2: Cleanup
    P->>TM: Final Statistics
````

1. **Initialization**
    - Create playground instance
    - Initialize worker agents
    - Define task groups and goals

2. **Task Assignment**
    - Tasks are assigned to available workers
    - Workers process tasks concurrently
    - System respects max_concurrent_tasks limit

3. **Progress Monitoring**
    - System tracks task completion
    - Goal conditions are checked
    - Status updates are printed

4. **Goal Achievement**
    - System detects when goals are met
    - Success messages are displayed
    - Processing can continue after goal achievement

## Key Features

1. **Concurrent Processing**
    - Multiple workers process tasks simultaneously
    - Each worker manages its own task queue
    - Configurable concurrent task limits

2. **Goal-Based Completion**
    - Define custom goal conditions
    - Track partial completion
    - Flexible goal checking logic

3. **Progress Monitoring**
    - Real-time status updates
    - Clear progress tracking
    - Goal status visibility

## Best Practices

1. **Task Design**
    - Keep tasks atomic and independent
    - Include clear descriptions
    - Set appropriate durations

2. **Worker Configuration**
    - Set reasonable concurrency limits
    - Match worker roles to task requirements
    - Consider resource constraints

3. **Goal Definition**
    - Define clear completion criteria
    - Include meaningful success/failure messages
    - Consider partial completion scenarios

## Error Handling

The system includes built-in error handling:

- Task failure recovery
- Worker disconnection handling
- Goal status monitoring

## Extending the System

You can extend the system by:

1. Adding new worker types
2. Implementing custom goal checkers
3. Adding task dependencies
4. Implementing priority queuing
5. Adding monitoring and metrics

## Running the Example

1. Save the code in `app.py`
2. Install required dependencies:
   ```bash
   pip install ceylon
   ```

3. Run the application:
   ```bash
   python app.py
   ```

## Future Enhancements

Consider these potential enhancements:

1. Persistent task storage
2. Web-based monitoring interface
3. Advanced scheduling algorithms
4. Task result aggregation
5. Dynamic worker scaling

## Troubleshooting

Common issues and solutions:

1. **Tasks not starting**: Check worker roles match task requirements
2. **Slow processing**: Adjust concurrent task limits
3. **Goals not achieving**: Verify goal checker logic
4. **Worker overload**: Monitor task queue lengths

## Conclusion

This tutorial demonstrated building a distributed task processing system with Ceylon. The system provides a flexible
foundation for handling concurrent task processing with goal-based completion tracking. The modular design allows for
easy extension and customization based on specific requirements.

For more information, visit:

- Ceylon Documentation: [https://docs.ceylon.ai](https://docs.ceylon.ai)
- API Reference: [https://docs.ceylon.ai/api](https://docs.ceylon.ai/api)
- GitHub Repository: [https://github.com/ceylon-ai/ceylon](https://github.com/ceylon-ai/ceylon)