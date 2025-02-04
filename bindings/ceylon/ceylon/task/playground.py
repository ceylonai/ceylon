#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from typing import Dict, List, Any

from loguru import logger

from ceylon import on
from ceylon.processor.agent import ProcessRequest, ProcessResponse, ProcessState
from ceylon.processor.playground import ProcessPlayGround
from ceylon.task.manager import TaskManager, TaskResult, TaskStatus, Task


class TaskProcessingPlayground(ProcessPlayGround):
    """
    Extended playground that combines ProcessPlayGround capabilities with TaskManager
    for structured task processing and dependency management.
    """

    def __init__(self, name="task_processor", port=8888):
        super().__init__(name=name, port=port)
        self.task_manager = TaskManager()
        self.task_process_map: Dict[str, str] = {}  # Maps task IDs to process request IDs
        self.pending_tasks: Dict[str, asyncio.Event] = {}
        self.task_responses: Dict[str, TaskResult] = {}

    async def add_and_execute_task(self,
                                   task: Task,
                                   wait_for_completion: bool = True) -> TaskResult:
        """
        Add a task and execute it through the processor system.

        Args:
            task (Task): The task to be added and executed.
            wait_for_completion (bool): Whether to wait for the task to complete.

        Returns:
            TaskResult: Result of the task execution
            :param wait_for_completion:
            :param task:
        """
        if type(task.processor) == str:
            required_role = task.processor
        else:
            raise ValueError("Processor must be a string (role)")

        async def process_executor(input_data: Dict) -> Any:

            if task.dependencies:
                dependency_data = {}
                for dependency_id in task.dependencies:
                    dependency_data[dependency_id] = self.task_responses[dependency_id]

            else:
                dependency_data = None

            # Create and send process request
            process_request = ProcessRequest(
                task_type=required_role,
                data=input_data.get('data'),
                dependency_data=dependency_data
            )

            # Store mapping
            self.task_process_map[task.id] = process_request.id

            # Send request and wait for response
            response = await self.process_request(process_request)

            if response.status == ProcessState.SUCCESS:
                return response.result
            else:
                raise Exception(response.error_message or "Task processing failed")

        task.processor = process_executor

        if wait_for_completion:
            # Create completion event
            self.pending_tasks[task.id] = asyncio.Event()

            # Execute task
            result = await self._execute_task(task)
            self.task_responses[task.id] = result
            self.task_manager.add_task(task)

            # Clean up
            self.pending_tasks.pop(task.id, None)
            return result
        else:
            # Start execution without waiting
            asyncio.create_task(self._execute_task(task))
            return None

    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute a single task and handle its result."""
        try:
            # Execute the task
            result = await asyncio.create_task(
                self.task_manager.execute_task(task)
            )

            # Set completion event if it exists
            if task.id in self.pending_tasks:
                self.pending_tasks[task.id].set()

            return result

        except Exception as e:
            logger.error(f"Error executing task {task.name}: {e}")
            return TaskResult(success=False, error=str(e))

    async def execute_task_group(self, tasks: List[Task]) -> Dict[str, TaskResult]:
        """Execute a group of tasks respecting dependencies."""
        results = {}
        pending_tasks = set()

        for task in tasks:
            event = asyncio.Event()
            self.pending_tasks[task.id] = event
            pending_tasks.add(task.id)

            # Start task execution
            asyncio.create_task(self._execute_task(task))

        # Wait for all tasks to complete
        while pending_tasks:
            completed = []
            for task_id in pending_tasks:
                if self.pending_tasks[task_id].is_set():
                    completed.append(task_id)
                    task = self.task_manager.get_task(task_id)
                    results[task_id] = task.result
                    self.pending_tasks.pop(task_id)

            for task_id in completed:
                pending_tasks.remove(task_id)

            await asyncio.sleep(0.1)

        return results

    @on(ProcessResponse)
    async def handle_process_response(self, response: ProcessResponse, time: int):
        """Handle process responses and update task status."""
        await super().handle_process_response(response, time)

        # Find corresponding task
        task_id = next(
            (tid for tid, pid in self.task_process_map.items()
             if pid == response.request_id),
            None
        )

        if task_id:
            task = self.task_manager.get_task(task_id)
            if task:
                if response.status == ProcessState.SUCCESS:
                    task.status = TaskStatus.COMPLETED
                elif response.status == ProcessState.ERROR:
                    task.status = TaskStatus.FAILED

                # Clean up mapping
                self.task_process_map.pop(task_id, None)
