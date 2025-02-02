import asyncio
import uuid
from typing import List
from ceylon.task import TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.task.manager import TaskManager

# Import our LLM Agent and related classes
from ceylon.llm.agent import LLMAgent, LLMConfig, LLMResponse


def create_text_generation_tasks(count: int) -> List[TaskMessage]:
    """Create a batch of content generation tasks"""
    topics = [
        "Artificial Intelligence in Healthcare",
        "Sustainable Energy Solutions",
        "Future of Remote Work",
        "Space Exploration Updates",
        "Quantum Computing Advances"
    ]

    tasks = []
    for i in range(count):
        task_id = str(uuid.uuid4())
        topic = topics[i % len(topics)]

        # Include additional parameters in metadata
        metadata = {
            "type": "content_generation",
            "topic": topic,
            "style": "informative",
            "target_length": 500
        }

        tasks.append(TaskMessage(
            task_id=task_id,
            name=f"Generate Content: {topic}",
            description=(
                f"Create an informative article about {topic}. "
                f"Target length: 500 words. Style: informative"
            ),
            duration=2,
            required_role="llm_processor",
            metadata=metadata
        ))

    return tasks


def create_analysis_tasks(texts: List[str]) -> List[TaskMessage]:
    """Create text analysis tasks"""
    tasks = []
    for i, text in enumerate(texts):
        task_id = str(uuid.uuid4())

        # Include analysis parameters in metadata
        metadata = {
            "type": "text_analysis",
            "analysis_type": "comprehensive",
            "source_text": text
        }

        tasks.append(TaskMessage(
            task_id=task_id,
            name=f"Analyze Text {i + 1}",
            description=(
                f"Perform comprehensive analysis of the following text:\n\n"
                f"{text}\n\nInclude: sentiment, key points, and main themes"
            ),
            duration=1,
            required_role="llm_processor",
            metadata=metadata
        ))

    return tasks


def create_goal_checker(required_success_rate: float):
    """Create a goal checker for LLM task success rate"""

    def check_completion(task_groups: dict, completed_tasks: dict) -> bool:
        if not completed_tasks:
            return False

        successful_tasks = sum(
            1 for task in completed_tasks.values()
            if task.completed and not hasattr(task, 'error')
        )
        total_tasks = len(completed_tasks)
        success_rate = successful_tasks / total_tasks

        print(f"Current success rate: {success_rate:.2%}")
        return success_rate >= required_success_rate

    return check_completion


async def main():
    # Create LLM configuration
    llm_config = LLMConfig(
        system_prompt=(
            "You are a versatile AI assistant capable of both generating "
            "content and analyzing text. Provide clear, accurate, and "
            "well-structured responses."
        ),
        temperature=0.7,
        max_tokens=1000,
        retry_attempts=2,
        retry_delay=1.0,
        timeout=20.0
    )

    # Create LLM agents
    llm_agents = [
        LLMAgent(
            name=f"llm_worker_{i}",
            config=llm_config,
            worker_role="llm_processor",
            max_concurrent_tasks=2
        )
        for i in range(2)  # Create 2 LLM agents
    ]

    # Initialize playground
    playground = TaskPlayGround(name="llm_playground")

    # Create task groups
    generation_group = TaskManager.create_task_group(
        name="Content Generation",
        description="Generate various content pieces using LLM",
        subtasks=create_text_generation_tasks(count=5),
        goal=TaskGroupGoal(
            name="Content Generation Success",
            description="Achieve 80% success rate in content generation",
            check_condition=create_goal_checker(required_success_rate=0.8),
            success_message="Successfully completed content generation tasks!",
            failure_message="Failed to achieve target success rate in content generation."
        ),
        priority=1
    )

    # Sample texts for analysis
    sample_texts = [
        "The new AI breakthrough has revolutionized medical diagnosis.",
        "Renewable energy adoption has increased by 50% globally.",
        "Remote work has become the new normal for many companies."
    ]

    analysis_group = TaskManager.create_task_group(
        name="Text Analysis",
        description="Analyze various texts using LLM",
        subtasks=create_analysis_tasks(sample_texts),
        goal=TaskGroupGoal(
            name="Analysis Success",
            description="Achieve 90% success rate in text analysis",
            check_condition=create_goal_checker(required_success_rate=0.9),
            success_message="Successfully completed text analysis tasks!",
            failure_message="Failed to achieve target success rate in text analysis."
        ),
        priority=2
    )

    # Run the playground
    async with playground.play(workers=llm_agents) as active_playground:
        active_playground: TaskPlayGround = active_playground

        # Assign both task groups
        await active_playground.assign_task_groups([
            generation_group,
            analysis_group
        ])

        # Monitor progress
        while True:
            await asyncio.sleep(1)

            # Check completion status of both groups
            generation_complete = (
                    generation_group.task_id in active_playground.task_manager.completed_groups
                    or (generation_group.goal and
                        generation_group.goal.status == GoalStatus.ACHIEVED)
            )

            analysis_complete = (
                    analysis_group.task_id in active_playground.task_manager.completed_groups
                    or (analysis_group.goal and
                        analysis_group.goal.status == GoalStatus.ACHIEVED)
            )

            # Print status
            print("\nTask Groups Status:")
            print(f"Content Generation: {generation_group.status.value}")
            print(f"Text Analysis: {analysis_group.status.value}")

            if generation_complete and analysis_complete:
                print("\nAll task groups completed!")
                break

        # Print final statistics
        await active_playground.print_all_statistics()


if __name__ == "__main__":
    asyncio.run(main())
