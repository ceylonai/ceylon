# Building a Simple Task Management System with Ceylon

## What We're Going to Build

We're going to create a basic system that assigns tasks to workers and keeps track of whether they complete these tasks successfully. Think of it like a simple version of how a manager might assign work to employees.

## What You Need to Know

- Basic Python knowledge
- Understanding of functions and classes

## Step 1: Create Our Building Blocks

First, we'll create simple structures to represent our tasks and workers:

```python
class Task:
    def __init__(self, name, difficulty):
        self.name = name
        self.difficulty = difficulty

class Worker:
    def __init__(self, name, skill):
        self.name = name
        self.skill = skill
```

## Step 2: Create a Task Manager

Now, let's create a manager that will assign tasks and track results:

```python
import random

class TaskManager:
    def __init__(self):
        self.tasks = []
        self.workers = []
        self.results = []

    def add_task(self, task):
        self.tasks.append(task)

    def add_worker(self, worker):
        self.workers.append(worker)

    def assign_tasks(self):
        for task in self.tasks:
            worker = random.choice(self.workers)
            success = worker.skill >= task.difficulty
            result = f"{worker.name} {'completed' if success else 'failed'} task: {task.name}"
            self.results.append(result)

    def print_results(self):
        for result in self.results:
            print(result)
```

## Step 3: Use Our Task Management System

Now let's put it all together and use our system:

```python
# Create a task manager
manager = TaskManager()

# Add some tasks
manager.add_task(Task("Easy Task", 1))
manager.add_task(Task("Medium Task", 5))
manager.add_task(Task("Hard Task", 10))

# Add some workers
manager.add_worker(Worker("Beginner Bob", 3))
manager.add_worker(Worker("Intermediate Ivy", 6))
manager.add_worker(Worker("Expert Eve", 9))

# Assign tasks and print results
manager.assign_tasks()
manager.print_results()
```

## How It Works

1. We create `Task` and `Worker` classes to represent our tasks and workers.
2. The `TaskManager` class handles adding tasks and workers, assigning tasks, and tracking results.
3. When we assign tasks, we randomly pick a worker for each task.
4. A task is completed successfully if the worker's skill is equal to or higher than the task's difficulty.
5. Finally, we print out the results to see which workers completed which tasks.

This simple system demonstrates basic concepts of task management. In a real-world scenario, this could be much more complex, but this gives you a starting point to understand the basics!