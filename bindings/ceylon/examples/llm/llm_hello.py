import asyncio

from ceylon.processor.agent import ProcessWorker, ProcessRequest, ProcessResponse
from ceylon.processor.playground import ProcessPlayGround


class MessageProcessor(ProcessWorker):
    async def _processor(self, request: ProcessRequest, time: int):
        if request.task_type == "uppercase":
            if isinstance(request.data, str):
                result = request.data.upper()
                return result
            else:
                raise Exception("Input must be a string")
        else:
            raise Exception(f"Unknown task type: {request.task_type}")

    def __init__(self, name: str):
        super().__init__(name=name, role="processor")


async def main():
    # Create playground and worker
    playground = ProcessPlayGround()
    worker = MessageProcessor("worker1")

    # Start the system
    async with playground.play(workers=[worker]) as active_playground:
        active_playground: ProcessPlayGround = active_playground
        # Send some test requests
        test_cases = [
            ("uppercase", "hello world"),
            ("uppercase", 123),  # Should cause an error
            ("unknown", "test")  # Should cause an error
        ]

        for task_type, data in test_cases:
            print(f"\nSending request - Type: {task_type}, Data: {data}")
            response: ProcessResponse = await active_playground.process_request(ProcessRequest(
                task_type=task_type,
                data=data
            ))
            print(f"Response received: {response.result}")
            await asyncio.sleep(1)  # Small delay between requests
        await active_playground.finish()


if __name__ == "__main__":
    asyncio.run(main())
