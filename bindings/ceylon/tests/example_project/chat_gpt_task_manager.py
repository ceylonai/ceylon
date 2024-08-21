import datetime


class Task:
    def __init__(self, name, priority, due_date=None):
        self.name = name
        self.priority = priority
        self.due_date = due_date
        self.completed = False

    def __str__(self):
        status = "✓" if self.completed else "✗"
        due_date_str = self.due_date.strftime("%Y-%m-%d") if self.due_date else "No due date"
        return f"{status} | {self.name} | Priority: {self.priority} | Due: {due_date_str}"


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, name, priority, due_date=None):
        task = Task(name, priority, due_date)
        self.tasks.append(task)
        print(f"Task '{name}' added.")

    def list_tasks(self, show_completed=False):
        print("\n--- Task List ---")
        for i, task in enumerate(self.tasks):
            if show_completed or not task.completed:
                print(f"{i + 1}. {task}")
        print("-----------------\n")

    def complete_task(self, task_index):
        try:
            task = self.tasks[task_index - 1]
            task.completed = True
            print(f"Task '{task.name}' marked as completed.")
        except IndexError:
            print("Invalid task number.")

    def list_tasks_by_date(self, date):
        print(f"\n--- Tasks Due on {date.strftime('%Y-%m-%d')} ---")
        for i, task in enumerate(self.tasks):
            if task.due_date == date and not task.completed:
                print(f"{i + 1}. {task}")
        print("-----------------\n")

    def download_task_list(self, filename="tasks.txt"):
        with open(filename, "w") as f:
            for task in self.tasks:
                f.write(str(task) + "\n")
        print(f"Task list saved to {filename}.")

    def check_finished_tasks(self):
        print("\n--- Completed Tasks ---")
        for i, task in enumerate(self.tasks):
            if task.completed:
                print(f"{i + 1}. {task}")
        print("----------------------\n")


def main():
    manager = TaskManager()

    while True:
        print("\nTask Manager Options:")
        print("1. Add a Task")
        print("2. List Tasks")
        print("3. Mark Task as Completed")
        print("4. List Tasks by Due Date")
        print("5. Download Task List")
        print("6. Check Finished Tasks")
        print("7. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            name = input("Enter task name: ")
            priority = input("Enter task priority (1-5): ")
            due_date_input = input("Enter due date (YYYY-MM-DD) or leave empty: ")
            due_date = datetime.datetime.strptime(due_date_input, "%Y-%m-%d").date() if due_date_input else None
            manager.add_task(name, priority, due_date)

        elif choice == "2":
            show_completed = input("Show completed tasks? (yes/no): ").strip().lower() == 'yes'
            manager.list_tasks(show_completed)

        elif choice == "3":
            task_index = int(input("Enter task number to mark as completed: "))
            manager.complete_task(task_index)

        elif choice == "4":
            date_input = input("Enter date (YYYY-MM-DD): ")
            date = datetime.datetime.strptime(date_input, "%Y-%m-%d").date()
            manager.list_tasks_by_date(date)

        elif choice == "5":
            filename = input("Enter filename to save task list (default: tasks.txt): ") or "tasks.txt"
            manager.download_task_list(filename)

        elif choice == "6":
            manager.check_finished_tasks()

        elif choice == "7":
            print("Exiting Task Manager. Goodbye!")
            break

        else:
            print("Invalid option. Please choose again.")


if __name__ == "__main__":
    main()
