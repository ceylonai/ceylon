import asyncio
import uuid
from typing import Dict

from ceylon.task import TaskPlayGround
from ceylon.task.data import TaskGroup, TaskGroupGoal, GoalStatus
from ceylon.llm.agent import LLMTask, LLMTaskType, LLMAgent

def create_completion_checker(required_completions: int) -> callable:
    """Creates a checker that completes when X tasks are done"""
    def check(task_groups: Dict[str, TaskGroup],
              completed_tasks: Dict[str, LLMTask]) -> bool:
        completed_count = sum(
            1 for task in completed_tasks.values()
            if task.group_id in task_groups and task.completed
        )
        print(f"Completed tasks: {completed_count}/{required_completions}")
        return completed_count >= required_completions
    return check

async def main():
    # Create playground
    playground = TaskPlayGround()

    # Create agent
    completion_agent = LLMAgent(
        name="story writer",
        role="story_writer",
        agent_instructions="You are a creative story writer."
    )

    # Create story writing tasks
    story_tasks = [
        LLMTask(
            task_id=str(uuid.uuid4()),
            name=f"Story {i+1}",
            description="Write a short story",
            duration=0.1,
            system_prompt="Write an engaging short story",
            input_data=f"Topic: {topic}",
            task_type=LLMTaskType.COMPLETION
        )
        for i, topic in enumerate([
            "Space Adventure",
            "Mystery in the Woods",
            "Time Travel"
        ])
    ]

    # Create task group
    story_group = TaskPlayGround.create_task_group(
        name="Story Writing",
        description="Generate creative short stories",
        subtasks=story_tasks,
        goal=TaskGroupGoal(
            name="Complete Stories",
            description="Complete at least 2 stories",
            check_condition=create_completion_checker(2),
            success_message="Successfully wrote required stories!",
            failure_message="Failed to complete stories."
        )
    )

    # Run the playground
    async with playground.play(workers=[completion_agent]) as active_playground:
        # Assign the task group
        await active_playground.assign_task_groups([story_group])

        # Wait for completion
        while True:
            await asyncio.sleep(1)
            if story_group.task_id in active_playground.task_groups:
                current_group = active_playground.task_groups[story_group.task_id]
                # Check if goal is achieved
                if (current_group.goal and
                        current_group.goal.status == GoalStatus.ACHIEVED):
                    print("\nStory writing complete!")
                    break

        # Print final results
        print("\nFinal Results:")
        for task in story_tasks:
            if task.completed:
                print(f"\nStory: {task.name}")
                print(f"Output: {task.output}")
                print(f"Duration: {task.end_time - task.start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())