import asyncio
from dataclasses import dataclass
from typing import Optional, Any

from ceylon import Worker, on
from ceylon.base.playground import BasePlayGround


@dataclass
class TaskRequest:
    task_id: str
    task_type: str
    data: Any


@dataclass
class TaskResponse:
    task_id: str
    result: Any
    status: str  # 'success' or 'error'
    error_message: Optional[str] = None


class MessagePlayground(BasePlayGround):
    def __init__(self, name="message_playground", port=8888):
        super().__init__(name=name, port=port)
        self.responses = {}
        self.response_events = {}

    @on(TaskResponse)
    async def handle_response(self, response: TaskResponse, time: int):
        # Store the response and trigger the event
        self.responses[response.task_id] = response
        if response.task_id in self.response_events:
            self.response_events[response.task_id].set()

        # Forward response externally (you can modify this part)
        print(f"Received response: {response}")

    async def send_task_request(self, task_type: str, data: Any) -> TaskResponse or None:
        # Create a unique task ID
        task_id = f"task_{len(self.responses)}"

        # Create an event for this task
        self.response_events[task_id] = asyncio.Event()

        # Create and send the request
        request = TaskRequest(task_id=task_id, task_type=task_type, data=data)
        await self.broadcast_message(request)

        # Wait for response
        try:
            await asyncio.wait_for(self.response_events[task_id].wait(), timeout=30.0)
            return self.responses[task_id]
        except asyncio.TimeoutError:
            return TaskResponse(
                task_id=task_id,
                result=None,
                status='error',
                error_message='Request timed out'
            )
        finally:
            # Cleanup
            self.response_events.pop(task_id, None)


class MessageWorker(Worker):
    def __init__(self, name: str):
        super().__init__(name=name, role="processor")

    @on(TaskRequest)
    async def handle_request(self, request: TaskRequest, time: int):
        try:
            # Process the request (example implementation)
            if request.task_type == "uppercase":
                if isinstance(request.data, str):
                    result = request.data.upper()
                    status = "success"
                    error_message = None
                else:
                    result = None
                    status = "error"
                    error_message = "Input must be a string"
            else:
                result = None
                status = "error"
                error_message = f"Unknown task type: {request.task_type}"

            # Send response
            response = TaskResponse(
                task_id=request.task_id,
                result=result,
                status=status,
                error_message=error_message
            )
            await self.broadcast_message(response)

        except Exception as e:
            # Handle errors
            error_response = TaskResponse(
                task_id=request.task_id,
                result=None,
                status="error",
                error_message=str(e)
            )
            await self.broadcast_message(error_response)


async def main():
    # Create playground and worker
    playground = MessagePlayground()
    worker = MessageWorker("worker1")

    # Start the system
    async with playground.play(workers=[worker]) as active_playground:
        # Send some test requests
        test_cases = [
            ("uppercase", "hello world"),
            ("uppercase", 123),  # Should cause an error
            ("unknown", "test")  # Should cause an error
        ]

        for task_type, data in test_cases:
            print(f"\nSending request - Type: {task_type}, Data: {data}")
            response = await active_playground.send_task_request(task_type, data)
            print(f"Response received: {response}")
            await asyncio.sleep(1)  # Small delay between requests
        await active_playground.finish()

if __name__ == "__main__":
    asyncio.run(main())