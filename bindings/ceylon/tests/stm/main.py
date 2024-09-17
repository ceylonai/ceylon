# Create subtasks
from ceylon.auto.model import SubTask, Task

# SubTask 1: Research Trending Topics
research_trends = SubTask(
    name="Research Trending Topics",
    executor="Alice",
    needs_approval=False
)

# SubTask 2: Write Draft Blog Post
write_draft = SubTask(
    name="Write Draft Blog Post",
    executor="Bob",
    needs_approval=True,
    dependencies=[research_trends]
)

# SubTask 3: Edit and Proofread
edit_proofread = SubTask(
    name="Edit and Proofread",
    executor="Charlie",
    needs_approval=True,
    dependencies=[write_draft]
)

# SubTask 4: Optimize for SEO
optimize_seo = SubTask(
    name="Optimize for SEO",
    executor="Dave",
    needs_approval=False,
    dependencies=[edit_proofread]
)

# SubTask 5: Publish Post
publish_post = SubTask(
    name="Publish Post",
    executor="Eve",
    needs_approval=True,
    dependencies=[optimize_seo]
)

# SubTask 6: Promote Post on Social Media
promote_post = SubTask(
    name="Promote Post on Social Media",
    executor="Frank",
    needs_approval=False,
    dependencies=[publish_post]
)

# Create main task
blog_post_task = Task(
    name="Publish Blog Post with Research Trend and Optimize SEO",
    subtasks=[research_trends, write_draft, edit_proofread, optimize_seo, publish_post, promote_post]
)


# Function to simulate subtask progression
def progress_subtask(subtask):
    # Approve if needed
    if subtask.needs_approval and subtask.state == 'pending':
        subtask.approve()
        print(f"SubTask '{subtask.name}' approved.")

    # Handle failed state and retries
    if subtask.state == 'failed' and subtask.can_retry():
        subtask.retry()
        print(f"Retrying SubTask '{subtask.name}'.")
        # After retrying, simulate completion or another failure
        if subtask.retry_count < subtask.max_retries:
            # For the sake of simulation, let's assume it succeeds after retry
            subtask.complete()
            print(f"SubTask '{subtask.name}' completed after retry.")
        else:
            print(f"SubTask '{subtask.name}' failed after maximum retries.")
        return  # Exit the function after handling retry

    # Start subtask if possible
    if subtask.can_start() and subtask.state in ['approved', 'pending']:
        subtask.start()
        print(f"SubTask '{subtask.name}' started by {subtask.executor}.")
        # Simulate completion or failure
        if subtask.name == "Optimize for SEO" and subtask.retry_count == 0:
            subtask.fail()
        else:
            subtask.complete()
            print(f"SubTask '{subtask.name}' completed.")
    else:
        if subtask.state not in ['completed', 'in_progress', 'failed']:
            print(f"SubTask '{subtask.name}' cannot start yet. Waiting for dependencies.")


# Simulate the task progression

# List of subtasks in the order they should be attempted
# Simulate the task progression

# List of subtasks in the order they should be attempted
subtasks_sequence = [research_trends, write_draft, edit_proofread, optimize_seo, publish_post, promote_post]

# Keep progressing through subtasks until all are completed
while not blog_post_task.all_subtasks_completed():
    for subtask in subtasks_sequence:
        if subtask.state in ['pending', 'approved', 'failed']:
            progress_subtask(subtask)
    print("\n")

print(f"Task '{blog_post_task.name}' is completed.")
