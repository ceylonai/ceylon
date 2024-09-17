# CLI_TaskManager class that extends TaskManager
from ceylon.auto.manager.abstract_manager import TaskManager


class CLI_TaskManager(TaskManager):
    def progress_subtask(self, subtask):
        """Simulate the progression of a subtask via CLI interaction."""
        # Approve if needed
        if subtask.needs_approval and subtask.state == 'pending':
            user_input = input(f"SubTask '{subtask.name}' needs approval. Approve? (y/n): ")
            if user_input.lower() == 'y':
                subtask.approve()
                print(f"SubTask '{subtask.name}' approved.")
            else:
                print(f"SubTask '{subtask.name}' not approved.")
                return

        # Handle failed state and retries
        if subtask.state == 'failed' and subtask.can_retry():
            user_input = input(f"SubTask '{subtask.name}' failed. Retry? (y/n): ")
            if user_input.lower() == 'y':
                subtask.retry()
                print(f"Retrying SubTask '{subtask.name}'.")
            else:
                print(f"SubTask '{subtask.name}' will not be retried.")
                return

        # Start subtask if possible
        if subtask.can_start() and subtask.state in ['approved', 'pending']:
            subtask.start()
            print(f"SubTask '{subtask.name}' started by {subtask.executor}.")
            # Simulate completion or failure
            user_input = input(f"Did SubTask '{subtask.name}' complete successfully? (y/n): ")
            if user_input.lower() == 'y':
                subtask.complete()
                print(f"SubTask '{subtask.name}' completed.")
            else:
                subtask.fail()
                print(f"SubTask '{subtask.name}' failed.")
        else:
            if subtask.state not in ['completed', 'in_progress', 'failed']:
                print(f"SubTask '{subtask.name}' cannot start yet. Waiting for dependencies.")
