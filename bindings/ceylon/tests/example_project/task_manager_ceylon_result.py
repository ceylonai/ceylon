import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk
import csv
from datetime import datetime


class Task:
    def __init__(self, title, description, due_date, priority):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority  # Priority can be 'Low', 'Medium', or 'High'
        self.completed = False

    def complete(self):
        self.completed = True

    def __str__(self):
        status = "✓" if self.completed else "✗"
        return f"{status} {self.title} (Due: {self.due_date}, Priority: {self.priority})"


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, title, description, due_date, priority):
        task = Task(title, description, due_date, priority)
        self.tasks.append(task)

    def complete_task(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks[index].complete()

    def filter_tasks_by_date(self, date_str):
        return [task for task in self.tasks if task.due_date == date_str]

    def download_tasks_as_csv(self, filtered_tasks, date_str):
        filename = f'tasks_{date_str}.csv'
        with open(filename, mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=filtered_tasks[0].__dict__.keys())
            writer.writeheader()
            writer.writerows([task.__dict__ for task in filtered_tasks])
        return filename


class TaskMasterApp:
    def __init__(self, master):
        self.master = master
        self.master.title("TaskMaster")
        self.task_manager = TaskManager()

        self.task_listbox = tk.Listbox(master, selectmode=tk.SINGLE)
        self.task_listbox.pack(expand=True, fill=tk.BOTH)

        self.add_button = tk.Button(master, text="Add Task", command=self.add_task)
        self.add_button.pack(side=tk.LEFT)

        self.complete_button = tk.Button(master, text="Complete Task", command=self.complete_task)
        self.complete_button.pack(side=tk.LEFT)

        self.download_button = tk.Button(master, text="Download Completed Tasks", command=self.download_completed_tasks)
        self.download_button.pack(side=tk.LEFT)

        self.check_finished_button = tk.Button(master, text="Check Finished Tasks", command=self.check_finished_tasks)
        self.check_finished_button.pack(side=tk.LEFT)

    def add_task(self):
        title = simpledialog.askstring("Task Title", "Enter the task title:")
        description = simpledialog.askstring("Task Description", "Enter the task description:")
        due_date = simpledialog.askstring("Due Date", "Enter the due date (YYYY-MM-DD):")
        priority = simpledialog.askstring("Priority", "Enter the priority (Low, Medium, High):")
        self.task_manager.add_task(title, description, due_date, priority)
        self.update_task_list()

    def complete_task(self):
        try:
            selected_index = self.task_listbox.curselection()[0]
            self.task_manager.complete_task(selected_index)
            self.update_task_list()
        except IndexError:
            messagebox.showwarning("Warning", "No task selected.")

    def download_completed_tasks(self):
        date_input = simpledialog.askstring("Download Tasks",
                                            "Enter the date to download completed tasks (YYYY-MM-DD):")
        filtered_tasks = self.task_manager.filter_tasks_by_date(date_input)
        if filtered_tasks:
            filename = self.task_manager.download_tasks_as_csv(filtered_tasks, date_input)
            messagebox.showinfo("Download Complete", f"Tasks downloaded as {filename}.")
        else:
            messagebox.showinfo("No Tasks", "No tasks found for the selected date.")

    def check_finished_tasks(self):
        completed_tasks = [task for task in self.task_manager.tasks if task.completed]
        if completed_tasks:
            completed_tasks_str = "\n".join(str(task) for task in completed_tasks)
            messagebox.showinfo("Completed Tasks", f"The following tasks are completed:\n\n{completed_tasks_str}")
        else:
            messagebox.showinfo("Completed Tasks", "No tasks are completed.")

    def update_task_list(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.task_manager.tasks:
            self.task_listbox.insert(tk.END, str(task))


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskMasterApp(root)
    root.mainloop()
