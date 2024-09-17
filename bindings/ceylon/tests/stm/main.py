# Create a new subtask that requires inputs
from ceylon.auto.manager.cli_manager import CLI_TaskManager
from ceylon.auto.model import SubTask, Task

# SubTask 1: Market Research
market_research = SubTask(
    name="Market Research",
    executor="Alice",
    needs_approval=False,
    inputs_needed=["Target Demographics", "Market Trends"]
)

# SubTask 2: Design Prototype
design_prototype = SubTask(
    name="Design Prototype",
    executor="Bob",
    needs_approval=False,  # Auto-approves since needs_approval is False
    dependencies=[market_research]
)

# SubTask 3: User Testing
user_testing = SubTask(
    name="User Testing",
    executor="Charlie",
    needs_approval=True,
    dependencies=[design_prototype]
)

# SubTask 4: Finalize Product
finalize_product = SubTask(
    name="Finalize Product",
    executor="Diana",
    needs_approval=False,
    dependencies=[user_testing],
    inputs_needed=["Final Specifications"]
)

# SubTask 5: Marketing Campaign
marketing_campaign = SubTask(
    name="Marketing Campaign",
    executor="Ethan",
    needs_approval=True,
    dependencies=[finalize_product]
)

# SubTask 6: Launch Event
launch_event = SubTask(
    name="Launch Event",
    executor="Fiona",
    needs_approval=False,
    dependencies=[marketing_campaign]
)

# Create the main task
launch_product_task = Task(
    name="Launch New Product",
    subtasks=[
        market_research,
        design_prototype,
        user_testing,
        finalize_product,
        marketing_campaign,
        launch_event
    ]
)

# Add the task to the manager and run
task_manager = CLI_TaskManager()
task_manager.add_task(launch_product_task)

while not task_manager.all_tasks_completed():
    task_manager.progress_tasks()
