import asyncio

from ceylon.llm.agent import LLMConfig, LLMAgent
from ceylon.llm.models.ollama import OllamaModel
from ceylon.processor.agent import ProcessRequest, ProcessResponse
from ceylon.processor.playground import ProcessPlayGround
from ceylon.task.data import Task, TaskResult
from ceylon.task.playground import TaskProcessingPlayground


async def main():
    # Create playground and worker
    playground = TaskProcessingPlayground()
    llm_model = OllamaModel(
        model_name="deepseek-r1:8b",
        base_url="http://localhost:11434"
    )

    # Configure LLM agent
    llm_config = LLMConfig(
        system_prompt=(
            "You are an expert content writer specializing in technology topics. "
        ),
        temperature=0.7,
        max_tokens=1000,
        retry_attempts=1
    )

    # Create LLM agent
    llm_agent = LLMAgent(
        name="writer_1",
        llm_model=llm_model,
        config=llm_config,
        role="writer"
    )

    # Start the system
    async with playground.play(workers=[llm_agent]) as active_playground:
        active_playground: TaskProcessingPlayground = active_playground
        # Send some test requests
        response: TaskResult = await active_playground.add_and_execute_task(
            Task(
                name="Process Data 1",
                processor="writer",
                input_data={"request": "A Simple title for a blog post about AI"}
            )
        )
        print(f"Response received: {response.output}")


if __name__ == "__main__":
    asyncio.run(main())
