# Distributed Task Management System

This project implements a distributed task management system using the Ceylon framework. It simulates a workforce of
agents with different skill levels performing tasks of varying difficulty.

## Overview

The system consists of two main types of agents:

1. **Workers**: Agents with different skill levels who can perform tasks
2. **Task Manager**: Central coordinator that distributes tasks and monitors completion

The system demonstrates skill-based task execution where success depends on the worker's skill level matching or
exceeding the task's difficulty.

## Components

### Data Classes

- `Task`: Represents a task to be performed
    - id: Unique identifier
    - description: Task description
    - difficulty: Integer value from 1-10 indicating task complexity

- `TaskAssignment`: Message containing a task to be assigned
    - task: The Task to be performed

- `TaskResult`: Message containing the outcome of a task
    - task_id: ID of the completed task
    - worker: Name of the worker who performed the task
    - success: Boolean indicating task completion success

### Agents

1. **WorkerAgent (Worker)**
    - Represents an individual worker with specific skills
    - Properties:
        - name: Worker's identifier
        - skill_level: Integer (1-10) representing worker's capabilities
        - has_task: Boolean tracking if worker is currently assigned a task
    - Methods:
        - `on_message`: Handles task assignments and simulates task execution
        - `run`: Maintains the worker's event loop

2. **TaskManager (Admin)**
    - Coordinates task distribution and monitors completion
    - Properties:
        - tasks: List of tasks to be assigned
        - expected_workers: Number of workers expected to connect
        - task_results: Collection of completed task results
        - tasks_assigned: Boolean tracking if tasks have been distributed
    - Methods:
        - `on_agent_connected`: Triggers task distribution when all workers connect
        - `assign_tasks`: Distributes tasks to connected workers
        - `on_message`: Processes task completion results
        - `end_task_management`: Summarizes task completion statistics

## How It Works

1. The TaskManager initializes with a list of tasks and expected number of workers
2. Workers connect to the system, each with their own skill level
3. Once all workers are connected, the TaskManager distributes tasks
4. Workers receive tasks and attempt to complete them based on their skill level
    - Success occurs if worker's skill_level >= task difficulty
    - Task execution time is simulated based on task difficulty
5. Workers report task completion results back to the TaskManager
6. The TaskManager collects all results and generates a completion report

## Running the Code

1. Install required dependencies:
   ```
   pip install asyncio loguru ceylon
   ```

2. Run the script:
   ```
   python task_manager.py
   ```

## Default Configuration

The example includes:

- Three tasks of increasing difficulty:
    1. Simple calculation (difficulty: 2)
    2. Data analysis (difficulty: 5)
    3. Machine learning model training (difficulty: 8)
- Three workers with different skill levels:
    1. Junior (skill level: 3)
    2. Intermediate (skill level: 6)
    3. Senior (skill level: 9)

## Output

The system provides detailed logging of:

- Worker initialization and connections
- Task assignments
- Task completions with success/failure status
- Final success rate and detailed results using checkmarks (✓) and crosses (✗)

## Customization

You can customize the simulation by modifying the `main` function:

- Add or remove tasks with different difficulties
- Change the number of workers and their skill levels
- Modify task descriptions and complexities
- Adjust the task execution simulation time

## Note

This implementation uses:

- Ceylon framework for agent communication
- Loguru for enhanced logging
- Pickle for message serialization
- Asyncio for asynchronous execution

## Limitations and Potential Improvements

- Fixed one-to-one task assignment (each worker gets exactly one task)
- No task prioritization or queuing system
- No support for task dependencies or workflows
- Limited to synchronous task completion (no parallel task execution)
- No task reassignment on failure
- No worker load balancing
- No persistent storage of task results
- No error recovery mechanism for failed tasks
- No consideration of worker specializations beyond skill level

These limitations provide opportunities for extending the system for more complex task management scenarios.