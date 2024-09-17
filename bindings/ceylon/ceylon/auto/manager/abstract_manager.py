from abc import ABC, abstractmethod


# Abstract TaskManager class
class TaskManager(ABC):
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        """Add a Task to the manager."""
        self.tasks.append(task)

    def remove_task(self, task):
        """Remove a Task from the manager."""
        self.tasks.remove(task)

    def all_tasks_completed(self):
        """Check if all tasks are completed."""
        return all(task.all_subtasks_completed() for task in self.tasks)

    def progress_tasks(self):
        """Progress through the tasks by simulating subtask progression."""
        for task in self.tasks:
            print(f"Progressing Task: '{task.name}'")
            subtasks_sequence = task.subtasks  # Assuming tasks have subtasks in desired order
            for subtask in subtasks_sequence:
                if subtask.state in ['pending', 'approved', 'failed']:
                    self.progress_subtask(subtask)
            print("\n")
        if self.all_tasks_completed():
            print("All tasks are completed.")

    @abstractmethod
    def progress_subtask(self, subtask):
        """Simulate the progression of a subtask."""
        pass
