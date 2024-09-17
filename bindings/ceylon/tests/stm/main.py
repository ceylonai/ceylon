# Assuming the previous code has been imported and the SubTask and Task classes are available
from ceylon.auto.manager.cli_manager import CLI_TaskManager
from ceylon.auto.model import Task, SubTask

# Create subtasks for a second task
# SubTask 1: Gather Data
gather_data = SubTask(
    name="Gather Data",
    executor="Grace",
    needs_approval=False
)

# SubTask 2: Analyze Data
analyze_data = SubTask(
    name="Analyze Data",
    executor="Heidi",
    needs_approval=True,
    dependencies=[gather_data]
)

# SubTask 3: Write Report
write_report = SubTask(
    name="Write Report",
    executor="Ivan",
    needs_approval=False,
    dependencies=[analyze_data]
)

# SubTask 4: Review Report
review_report = SubTask(
    name="Review Report",
    executor="Judy",
    needs_approval=True,
    dependencies=[write_report]
)

# SubTask 5: Finalize Report
finalize_report = SubTask(
    name="Finalize Report",
    executor="Kevin",
    needs_approval=False,
    dependencies=[review_report]
)

# SubTask 6: Distribute Report
distribute_report = SubTask(
    name="Distribute Report",
    executor="Laura",
    needs_approval=False,
    dependencies=[finalize_report]
)

# Create the second main task
monthly_report_task = Task(
    name="Prepare Monthly Report",
    subtasks=[gather_data, analyze_data, write_report, review_report, finalize_report, distribute_report]
)

# Create TaskManager instance
task_manager = CLI_TaskManager()

# Add tasks to the manager
task_manager.add_task(monthly_report_task)
# task_manager.add_task(monthly_report_task)

# Simulate the task progression
while not task_manager.all_tasks_completed():
    task_manager.progress_tasks()
