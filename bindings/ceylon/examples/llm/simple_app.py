#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
import uuid
from ceylon.task import TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal
from ceylon.task.manager import TaskManager
from ceylon.llm.models.ollama import OllamaModel
from ceylon.llm.agent import LLMAgent, LLMConfig

async def main():
    # Initialize Ollama model
    llm_model = OllamaModel(
        model_name="llama3.2",
        base_url="http://localhost:11434"
    )

    # Configure LLM agent
    llm_config = LLMConfig(
        system_prompt=(
            "You are an expert content writer specializing in technology topics. "
            "Provide clear, informative, and engaging responses."
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
        worker_role="content_writer"
    )

    # Initialize playground
    playground = TaskPlayGround(name="simple_llm_demo")

    # Create a single task
    task = TaskMessage(
        task_id=str(uuid.uuid4()),
        name="Write about AI",
        description=(
            "Write a short, engaging paragraph about artificial intelligence "
            "and its impact on society."
        ),
        duration=2,
        required_role="content_writer",
        metadata={
            "type": "content_generation",
            "topic": "Artificial Intelligence",
            "target_length": 100
        }
    )

    # Create task group
    task_group = TaskManager.create_task_group(
        name="Content Writing",
        description="Generate AI content",
        subtasks=[task],
        priority=1
    )

    try:
        print("\nStarting LLM Task Processing...")

        # Run the playground
        async with playground.play(workers=[llm_agent]) as active_playground:
            # Assign task group
            await active_playground.assign_task_groups([task_group])

            # Wait for completion
            while True:
                await asyncio.sleep(1)
                if task.task_id in active_playground.get_completed_tasks():
                    break

            # Get and display results
            completed_task = active_playground.get_completed_tasks()[task.task_id]
            if completed_task.completed:
                print("\nTask Completed Successfully!")
                print(f"Duration: {completed_task.end_time - completed_task.start_time:.2f}s")
                print("\nGenerated Content:")
                print("=" * 80)
                task_result = active_playground.get_task_results().get(task.task_id)
                if task_result:
                    print(task_result)
                print("=" * 80)
            else:
                print(f"\nTask Failed: {completed_task.error}")

            await active_playground.finish()

    finally:
        await llm_model.close()

if __name__ == "__main__":
    print("Starting Ceylon LLM Agent Demo...")
    print("Ensure Ollama is running at http://localhost:11434")
    asyncio.run(main())