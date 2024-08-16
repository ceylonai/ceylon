import tkinter as tk
from tkinter import messagebox, END, filedialog
import csv
from datetime import datetime


class Task:
    def __init__(self, description, date):
        self.description = description
        self.completed = False
        self.date = date  # New date attribute


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, description, date):
        task = Task(description, date)
        self.tasks.append(task)

    def complete_task(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks[index].completed = True
            return self.tasks[index].description
        return None

    def delete_task(self, index):
        if 0 <= index < len(self.tasks):
            return self.tasks.pop(index).description
        return None

    def get_task_list(self):
        return [(task.description, task.completed, task.date) for task in self.tasks]

    def get_finished_tasks(self):
        return [(task.description, task.completed, task.date) for task in self.tasks if task.completed]

    def get_tasks_filtered_by_date(self, filter_date):
        return [(task.description, task.completed, task.date) for task in self.tasks if task.date == filter_date]


class TaskManagerApp:
    def __init__(self, master):
        self.master = master
        self.task_manager = TaskManager()
        master.title("Task Management Application")

        # Task Entry Section
        self.task_label = tk.Label(master, text="Enter Task:")
        self.task_label.pack()

        self.task_entry = tk.Entry(master, width=50)
        self.task_entry.pack()

        self.date_label = tk.Label(master, text="Enter Date (YYYY-MM-DD):")
        self.date_label.pack()

        self.date_entry = tk.Entry(master, width=50)
        self.date_entry.pack()

        self.add_task_button = tk.Button(master, text="Add Task", command=self.add_task)
        self.add_task_button.pack()

        # Task List Section
        self.task_listbox = tk.Listbox(master, width=50, height=10)
        self.task_listbox.pack()

        self.complete_task_button = tk.Button(master, text="Complete Task", command=self.complete_task)
        self.complete_task_button.pack()

        self.delete_task_button = tk.Button(master, text="Delete Task", command=self.delete_task)
        self.delete_task_button.pack()

        # Download Section
        self.download_button = tk.Button(master, text="Download Tasks", command=self.download_tasks)
        self.download_button.pack()

        # Finished Tasks Section
        self.view_finished_tasks_button = tk.Button(master, text="View Finished Tasks",
                                                    command=self.view_finished_tasks)
        self.view_finished_tasks_button.pack()

        # Status Section
        self.status_label = tk.Label(master, text="", fg="green")
        self.status_label.pack()

    def add_task(self):
        task = self.task_entry.get()
        date_str = self.date_entry.get()
        if task and self.validate_date(date_str):
            self.task_manager.add_task(task, date_str)
            self.task_entry.delete(0, END)
            self.date_entry.delete(0, END)
            self.update_task_listbox()
            self.update_status("Task added!")
        else:
            self.update_status("Please enter a valid task and date.")

    def complete_task(self):
        try:
            selected_task_index = self.task_listbox.curselection()[0]
            completed_task = self.task_manager.complete_task(selected_task_index)
            if completed_task:
                self.update_task_listbox()
                self.update_status(f"Task '{completed_task}' completed!")
            else:
                self.update_status("Error completing task.")
        except IndexError:
            self.update_status("Please select a task to complete.")

    def delete_task(self):
        try:
            selected_task_index = self.task_listbox.curselection()[0]
            deleted_task = self.task_manager.delete_task(selected_task_index)
            if deleted_task:
                self.update_task_listbox()
                self.update_status(f"Task '{deleted_task}' deleted!")
            else:
                self.update_status("Error deleting task.")
        except IndexError:
            self.update_status("Please select a task to delete.")

    def download_tasks(self):
        filter_date = self.date_entry.get()
        if self.validate_date(filter_date):
            tasks_to_download = self.task_manager.get_tasks_filtered_by_date(filter_date)
            if tasks_to_download:
                file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                if file_path:
                    with open(file_path, mode='w', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow(["Task Description", "Completed", "Date"])
                        for task_desc, completed, date in tasks_to_download:
                            writer.writerow([task_desc, completed, date])
                    self.update_status("Tasks downloaded successfully!")
                else:
                    self.update_status("Download cancelled.")
            else:
                self.update_status("No tasks found for this date.")
        else:
            self.update_status("Please enter a valid date (YYYY-MM-DD).")

    def view_finished_tasks(self):
        finished_tasks = self.task_manager.get_finished_tasks()
        self.task_listbox.delete(0, END)
        if finished_tasks:
            for task_description, completed, date in finished_tasks:
                self.task_listbox.insert(END, f"✔️ {task_description} (Date: {date})")
        else:
            self.task_listbox.insert(END, "No finished tasks.")

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False

    def update_task_listbox(self):
        self.task_listbox.delete(0, END)
        for task_description, completed, date in self.task_manager.get_task_list():
            status = "✔️" if completed else "❌"
            self.task_listbox.insert(END, f"{status} {task_description} (Date: {date})")

    def update_status(self, message):
        self.status_label.config(text=message)


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()
