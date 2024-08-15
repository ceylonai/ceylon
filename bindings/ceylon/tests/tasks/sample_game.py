from datetime import datetime


class Task:
    def __init__(self, title, due_date, description, priority='Medium'):
        self.title = title
        self.due_date = due_date
        self.description = description
        self.priority = priority
        self.completed = False

    def __repr__(self):
        status = "Completed" if self.completed else "Pending"
        return f"Task(title={self.title}, due_date={self.due_date}, description={self.description}, priority={self.priority}, status={status})"


import csv


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, title, due_date, description, priority='Medium'):
        new_task = Task(title, due_date, description, priority)
        self.tasks.append(new_task)
        print(f"Task '{title}' added successfully.")

    def list_tasks(self, completed=None):
        if completed is None:
            return self.tasks
        elif completed:
            return [task for task in self.tasks if task.completed]
        else:
            return [task for task in self.tasks if not task.completed]

    def complete_task(self, title):
        for task in self.tasks:
            if task.title == title and not task.completed:
                task.completed = True
                print(f"Task '{title}' marked as completed.")
                return
        print(f"Task '{title}' not found or already completed.")

    def delete_task(self, title):
        for task in self.tasks:
            if task.title == title:
                self.tasks.remove(task)
                print(f"Task '{title}' deleted successfully.")
                return
        print(f"Task '{title}' not found.")

    def set_task_priority(self, title, new_priority):
        for task in self.tasks:
            if task.title == title:
                task.priority = new_priority
                print(f"Priority for task '{title}' set to '{new_priority}'.")
                return
        print(f"Task '{title}' not found.")

    def filter_tasks_by_date(self, date):
        return [task for task in self.tasks if task.due_date.date() == date]

    def export_tasks_to_csv(self, tasks, filename):
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ['title', 'due_date', 'description', 'priority', 'status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for task in tasks:
                writer.writerow({
                    'title': task.title,
                    'due_date': task.due_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'description': task.description,
                    'priority': task.priority,
                    'status': 'Completed' if task.completed else 'Pending'
                })
        print(f"Tasks exported to {filename} successfully.")


def download_tasks_by_date(manager, date, filename):
    tasks = manager.filter_tasks_by_date(date)
    manager.export_tasks_to_csv(tasks, filename)


import tkinter as tk
from tkinter import ttk, filedialog, simpledialog


class TaskApp:
    def __init__(self, root, task_manager):
        self.root = root
        self.task_manager = task_manager
        self.root.title("Task Manager")

        self.create_widgets()
        self.update_task_list()

    def create_widgets(self):
        self.frame = tk.Frame(self.root)
        self.frame.pack()

        self.task_listbox = tk.Listbox(self.frame, width=100, height=20)
        self.task_listbox.pack(side=tk.LEFT)

        self.scrollbar = tk.Scrollbar(self.frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.task_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.task_listbox.yview)

        self.add_task_button = tk.Button(self.root, text="Add Task", command=self.add_task)
        self.add_task_button.pack()

        self.complete_task_button = tk.Button(self.root, text="Complete Task", command=self.complete_task)
        self.complete_task_button.pack()

        self.show_finished_tasks_button = tk.Button(self.root, text="Show Finished Tasks",
                                                    command=self.show_finished_tasks)
        self.show_finished_tasks_button.pack()

        self.show_pending_tasks_button = tk.Button(self.root, text="Show Pending Tasks",
                                                   command=self.show_pending_tasks)
        self.show_pending_tasks_button.pack()

        self.show_all_tasks_button = tk.Button(self.root, text="Show All Tasks", command=self.show_all_tasks)
        self.show_all_tasks_button.pack()

        self.download_tasks_button = tk.Button(self.root, text="Download Tasks by Date", command=self.download_tasks)
        self.download_tasks_button.pack()

    def add_task(self):
        title = simpledialog.askstring("Task Title", "Enter task title:")
        due_date = simpledialog.askstring("Due Date", "Enter due date (YYYY-MM-DD):")
        description = simpledialog.askstring("Description", "Enter task description:")
        priority = simpledialog.askstring("Priority", "Enter task priority (Low, Medium, High):", initialvalue="Medium")

        if title and due_date and description and priority:
            try:
                due_date = datetime.strptime(due_date, "%Y-%m-%d")
                self.task_manager.add_task(title, due_date, description, priority)
                self.update_task_list()
            except ValueError:
                print("Invalid date format. Please enter date in YYYY-MM-DD format.")

    def complete_task(self):
        selected_task = self.task_listbox.get(tk.ACTIVE)
        if selected_task:
            title = selected_task.split(",")[0].split("=")[1].strip()
            self.task_manager.complete_task(title)
            self.update_task_list()

    def show_finished_tasks(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.task_manager.list_tasks(completed=True):
            self.task_listbox.insert(tk.END, task)

    def show_pending_tasks(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.task_manager.list_tasks(completed=False):
            self.task_listbox.insert(tk.END, task)

    def show_all_tasks(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.task_manager.list_tasks():
            self.task_listbox.insert(tk.END, task)

    def download_tasks(self):
        date_str = simpledialog.askstring("Task Date", "Enter date (YYYY-MM-DD):")
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                if filename:
                    download_tasks_by_date(self.task_manager, date, filename)
            except ValueError:
                print("Invalid date format. Please enter date in YYYY-MM-DD format.")

    def update_task_list(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.task_manager.list_tasks():
            self.task_listbox.insert(tk.END, task)


if __name__ == "__main__":
    root = tk.Tk()
    manager = TaskManager()

    # Add some sample tasks for testing
    manager.add_task("Task 1", datetime(2023, 10, 15), "Description for Task 1", priority='High')
    manager.add_task("Task 2", datetime(2023, 10, 20), "Description for Task 2", priority='Low')

    app = TaskApp(root, manager)
    root.mainloop()
