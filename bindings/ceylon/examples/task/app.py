import asyncio
from ceylon.processor.agent import ProcessWorker, ProcessRequest
from ceylon.task.manager import TaskResult, Task
from ceylon.task.playground import TaskProcessingPlayground


class TextProcessor(ProcessWorker):
    """Example worker that processes text-based tasks."""

    async def _processor(self, request: ProcessRequest, time: int):
        print(f"Processing text: {request}")
        data = request.data
        return data * 5


class AggregateProcessor(ProcessWorker):
    """Example worker that processes text-based tasks."""

    async def _processor(self, request: ProcessRequest, time: int):
        print(f"Aggregating text: {request}")
        data = request.data or 0
        for d in request.dependency_data.values():
            data += d.output
        return data


async def main():
    # Create playground and worker
    playground = TaskProcessingPlayground()
    worker = TextProcessor("text_worker", role="multiply")
    aggregate_worker = AggregateProcessor("aggregate_worker", role="aggregate")

    async with playground.play(workers=[worker, aggregate_worker]) as active_playground:
        task1 = Task(
            name="Process Data 1",
            processor="multiply",
            input_data={'data': 5}
        )

        task2 = Task(
            name="Process Data 2",
            processor="multiply",
            input_data={'data': 10}
        )

        task3 = Task(
            name="Process Data 3",
            processor="aggregate",
            dependencies={task1.id, task2.id},
        )

        for task in [task1, task2, task3]:
            print(f"\nExecuting Task: {task.name}")
            # Execute independent tasks
            task_result: TaskResult = await active_playground.add_and_execute_task(
                task=task,  # Pass task data
                wait_for_completion=True
            )

            print(f"\nTask Results:")
            print(f"Task: {task.name}")
            print(f"Result: {task_result.output}")

        # task2_id: TaskResult = await active_playground.add_and_execute_task(
        #     name="Reverse Text",
        #     process_type="reverse",
        #     input_data={'data': "hello world"},
        #     wait_for_completion=True
        # )
        #
        # # Execute dependent task
        # combine_task: TaskResult = await active_playground.add_and_execute_task(
        #     name="Combine Results",
        #     process_type="combine",
        #     input_data={
        #         'data': {
        #             'text1': task1_id.output,
        #             'text2': task2_id.output
        #         }
        #     },
        #     dependencies={task1_id, task2_id},
        #     wait_for_completion=True
        # )
        #
        # print(f"\nTask Results:")
        # print(f"Task 1 (Uppercase): {task1_id.output}")
        # print(f"Task 2 (Reverse): {task2_id.output}")
        # print(f"Combined Result: {combine_task.output}")


if __name__ == "__main__":
    asyncio.run(main())
