import asyncio
import uuid
from typing import List
from ceylon.task import TaskPlayGround
from ceylon.task.data import TaskMessage, TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.task.manager import TaskManager
from ceylon.llm.models.ollama import OllamaModel
from ceylon.llm.agent import LLMAgent, LLMConfig
from datetime import datetime

def print_header(text: str):
    print(f"\n{'='*80}")
    print(f"{text.center(80)}")
    print(f"{'='*80}")

def create_writing_tasks(topics: List[str]) -> List[TaskMessage]:
    """Create content generation tasks for given topics"""
    tasks = []
    for topic in topics:
        task_id = str(uuid.uuid4())
        tasks.append(TaskMessage(
            task_id=task_id,
            name=f"Write Article: {topic}",
            description=(
                f"Write a comprehensive article about {topic}. "
                f"Include key concepts, recent developments, and future implications."
            ),
            duration=3,
            required_role="content_writer",
            metadata={
                "type": "article_writing",
                "topic": topic,
                "target_length": 500,
                "style": "informative"
            }
        ))
    return tasks

def create_analysis_tasks(texts: List[str]) -> List[TaskMessage]:
    """Create text analysis tasks"""
    tasks = []
    for i, text in enumerate(texts):
        task_id = str(uuid.uuid4())
        tasks.append(TaskMessage(
            task_id=task_id,
            name=f"Analyze Text {i + 1}",
            description=(
                "Perform a detailed analysis of the provided text. "
                "Include key themes, sentiment, and main points."
            ),
            duration=2,
            required_role="content_writer",
            metadata={
                "type": "text_analysis",
                "content": text,
                "analysis_aspects": ["themes", "sentiment", "key_points"]
            }
        ))
    return tasks

def create_success_rate_checker(required_rate: float):
    """Create a goal checker that verifies task success rate"""
    def check_completion(task_groups: dict, completed_tasks: dict) -> bool:
        if not completed_tasks:
            return False

        successful_tasks = sum(
            1 for task in completed_tasks.values()
            if task.completed and task.status != GoalStatus.FAILED
        )
        total_tasks = len(completed_tasks)
        success_rate = successful_tasks / total_tasks

        print(f"\nProgress Update:")
        print(f"Completed Tasks: {successful_tasks}/{total_tasks}")
        print(f"Success Rate: {success_rate:.1%} (Target: {required_rate:.1%})")
        return success_rate >= required_rate

    return check_completion

async def main():
    print_header("Ceylon LLM Agent Demo")
    print("\nInitializing system...")

    # Initialize Ollama model
    llm_model = OllamaModel(
        model_name="llama3.2",  # Or your preferred model
        base_url="http://localhost:11434"
    )

    # Configure LLM agent
    llm_config = LLMConfig(
        system_prompt=(
            "You are an expert content writer and analyst capable of producing "
            "well-researched articles and performing detailed content analysis. "
            "Always provide clear, accurate, and structured responses."
        ),
        temperature=0.7,
        max_tokens=2000,
        retry_attempts=2,
        retry_delay=1.0,
        timeout=30.0
    )

    # Create LLM agents
    llm_agents = [
        LLMAgent(
            name=f"writer_{i}",
            llm_model=llm_model,
            config=llm_config,
            worker_role="content_writer",
            max_concurrent_tasks=2
        )
        for i in range(2)
    ]

    # Initialize playground
    playground = TaskPlayGround(name="content_generation")

    # Define writing topics
    topics = [
        "Quantum Computing Applications",
        "Sustainable Energy Solutions",
        "Future of Remote Work",
        "Space Exploration Progress"
    ]

    print("\nTopics for Article Generation:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")

    # Create writing task group
    writing_group = TaskManager.create_task_group(
        name="Article Writing",
        description="Generate informative articles on various topics",
        subtasks=create_writing_tasks(topics),
        goal=TaskGroupGoal(
            name="Writing Quality Goal",
            description="Achieve 80% success rate in content generation",
            check_condition=create_success_rate_checker(0.8),
            success_message="Successfully completed article writing tasks!",
            failure_message="Failed to achieve target success rate in writing."
        ),
        priority=1
    )

    # Sample texts for analysis
    analysis_texts = [
        "Recent advancements in AI have transformed healthcare diagnosis through improved pattern recognition and early disease detection.",
        "Renewable energy adoption has increased significantly globally, with solar and wind power becoming increasingly cost-competitive with traditional energy sources.",
        "The shift to remote work has fundamentally changed workplace dynamics, leading to new challenges in team collaboration and work-life balance."
    ]

    print("\nTexts for Analysis:")
    for i, text in enumerate(analysis_texts, 1):
        print(f"\n{i}. {text[:100]}...")

    # Create analysis task group
    analysis_group = TaskManager.create_task_group(
        name="Content Analysis",
        description="Analyze various texts for insights",
        subtasks=create_analysis_tasks(analysis_texts),
        goal=TaskGroupGoal(
            name="Analysis Quality Goal",
            description="Achieve 90% success rate in text analysis",
            check_condition=create_success_rate_checker(0.9),
            success_message="Successfully completed text analysis tasks!",
            failure_message="Failed to achieve target success rate in analysis."
        ),
        priority=2
    )

    try:
        print_header("Starting Task Processing")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Run the playground
        async with playground.play(workers=llm_agents) as active_playground:
            # Assign task groups
            await active_playground.assign_task_groups([
                writing_group,
                analysis_group
            ])

            # Monitor progress
            while True:
                await asyncio.sleep(2)

                # Check completion status
                writing_done = (
                        writing_group.task_id in active_playground.task_manager.completed_groups
                        or (writing_group.goal and
                            writing_group.goal.status == GoalStatus.ACHIEVED)
                )

                analysis_done = (
                        analysis_group.task_id in active_playground.task_manager.completed_groups
                        or (analysis_group.goal and
                            analysis_group.goal.status == GoalStatus.ACHIEVED)
                )

                # Print status
                print(f"\nStatus Update ({datetime.now().strftime('%H:%M:%S')})")
                print(f"Article Writing: {writing_group.status.value}")
                print(f"Text Analysis: {analysis_group.status.value}")

                if writing_done and analysis_done:
                    print_header("All Tasks Completed!")
                    break

            print_header("Final Statistics")
            await active_playground.print_all_statistics()

    finally:
        # Cleanup
        await llm_model.close()
        print("\nSystem shutdown completed.")

if __name__ == "__main__":
    print("\nStarting Ceylon LLM Agent Demo...")
    print("Make sure Ollama is running at http://localhost:11434\n")
    asyncio.run(main())