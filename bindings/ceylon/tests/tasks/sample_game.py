import tkinter as tk
from tkinter import messagebox, filedialog
from datetime import datetime
from dataclasses import dataclass, field
import csv


@dataclass
class Task:
    description: str
    due_date: datetime.date
    priority: str
    completed: bool = field(default=False)


class TaskManager:
    def __init__(self):
        self.tasks = []

    def add_task(self, description, due_date, priority):
        if priority not in ['High', 'Medium', 'Low']:
            raise ValueError("Priority must be 'High', 'Medium', or 'Low'")
        task = Task(description, due_date, priority)
        self.tasks.append(task)

    def mark_task_completed(self, task_index):
        if 0 <= task_index < len(self.tasks):
            self.tasks[task_index].completed = True
        else:
            raise IndexError("Task index out of range")

    def get_pending_tasks(self):
        return [task for task in self.tasks if not task.completed]

    def get_finished_tasks(self):
        return [task for task in self.tasks if task.completed]

    def edit_task(self, task_index, new_description, new_due_date, new_priority):
        if 0 <= task_index < len(self.tasks):
            task = self.tasks[task_index]
            task.description = new_description
            task.due_date = new_due_date
            task.priority = new_priority
        else:
            raise IndexError("Task index out of range")

    def delete_task(self, task_index):
        if 0 <= task_index < len(self.tasks):
            del self.tasks[task_index]
        else:
            raise IndexError("Task index out of range")

    def get_tasks_sorted_by_date(self):
        return sorted(self.tasks, key=lambda task: task.due_date)

    def export_tasks_to_file(self, filename):
        sorted_tasks = self.get_tasks_sorted_by_date()
        try:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Description", "Due Date", "Priority", "Completed"])
                for task in sorted_tasks:
                    writer.writerow([task.description, task.due_date, task.priority, task.completed])
            return True
        except Exception as e:
            print(f"An error occurred while writing to file: {e}")
            return False


class TaskApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")

        self.task_manager = TaskManager()

        # Description
        tk.Label(root, text="Description").grid(row=0, column=0)
        self.description_entry = tk.Entry(root)
        self.description_entry.grid(row=0, column=1)

        # Due Date
        tk.Label(root, text="Due Date (YYYY-MM-DD)").grid(row=1, column=0)
        self.due_date_entry = tk.Entry(root)
        self.due_date_entry.grid(row=1, column=1)

        # Priority
        tk.Label(root, text="Priority").grid(row=2, column=0)
        self.priority_var = tk.StringVar(value="Medium")
        tk.OptionMenu(root, self.priority_var, "High", "Medium", "Low").grid(row=2, column=1)

        # Add Task Button
        tk.Button(root, text="Add Task", command=self.add_task).grid(row=3, column=1)

        # Download Task List Button
        tk.Button(root, text="Download Task List", command=self.download_task_list).grid(row=3, column=2)

        # Task List
        self.task_list_frame = tk.Frame(root)
        self.task_list_frame.grid(row=4, column=0, columnspan=3)
        self.update_task_list()

    def add_task(self):
        description = self.description_entry.get()
        due_date_str = self.due_date_entry.get()
        priority = self.priority_var.get()

        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            self.task_manager.add_task(description, due_date, priority)
            messagebox.showinfo("Success", "Task added successfully!")
            self.description_entry.delete(0, tk.END)
            self.due_date_entry.delete(0, tk.END)
            self.priority_var.set("Medium")
            self.update_task_list()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def update_task_list(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()

        tk.Label(self.task_list_frame, text="Pending Tasks").grid(row=0, column=0)
        tk.Label(self.task_list_frame, text="Finished Tasks").grid(row=0, column=1)

        pending_tasks = self.task_manager.get_pending_tasks()
        finished_tasks = self.task_manager.get_finished_tasks()

        for idx, task in enumerate(pending_tasks):
            tk.Label(self.task_list_frame, text=f"{task.description} (Due: {task.due_date}, Priority: {task.priority})").grid(row=idx + 1, column=0)
            tk.Button(self.task_list_frame, text="Mark as Done", command=lambda idx=idx: self.mark_task_done(idx)).grid(row=idx + 1, column=1)
            tk.Button(self.task_list_frame, text="Edit", command=lambda idx=idx: self.edit_task(idx)).grid(row=idx + 1, column=2)
            tk.Button(self.task_list_frame, text="Delete", command=lambda idx=idx: self.delete_task(idx)).grid(row=idx + 1, column=3)

        for idx, task in enumerate(finished_tasks):
            tk.Label(self.task_list_frame, text=f"{task.description} (Due: {task.due_date}, Priority: {task.priority})").grid(row=len(pending_tasks) + idx + 1, column=1)

    def mark_task_done(self, task_index):
        try:
            self.task_manager.mark_task_completed(task_index)
            self.update_task_list()
        except IndexError as e:
            messagebox.showerror("Error", str(e))

    def edit_task(self, task_index):
        try:
            task = self.task_manager.tasks[task_index]
            self.description_entry.delete(0, tk.END)
            self.description_entry.insert(0, task.description)
            self.due_date_entry.delete(0, tk.END)
            self.due_date_entry.insert(0, task.due_date.strftime('%Y-%m-%d'))
            self.priority_var.set(task.priority)

            def save_changes():
                new_description = self.description_entry.get()
                new_due_date_str = self.due_date_entry.get()
                new_priority = self.priority_var.get()
                try:
                    new_due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
                    self.task_manager.edit_task(task_index, new_description, new_due_date, new_priority)
                    self.update_task_list()
                    messagebox.showinfo("Success", "Task updated successfully!")
                    self.description_entry.delete(0, tk.END)
                    self.due_date_entry.delete(0, tk.END)
                    self.priority_var.set("Medium")
                    save_button.destroy()
                except ValueError as e:
                    messagebox.showerror("Error", str(e))

            save_button = tk.Button(self.root, text="Save Changes", command=save_changes)
            save_button.grid(row=3, column=2)

        except IndexError as e:
            messagebox.showerror("Error", str(e))

    def delete_task(self, task_index):
        try:
            self.task_manager.delete_task(task_index)
            self.update_task_list()
            messagebox.showinfo("Success", "Task deleted successfully!")
        except IndexError as e:
            messagebox.showerror("Error", str(e))

    def download_task_list(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            success = self.task_manager.export_tasks_to_file(filename)
            if success:
                messagebox.showinfo("Success", "Task list downloaded successfully!")
            else:
                messagebox.showerror("Error", "Failed to download task list.")


if __name__ == "__main__":
    root = tk.Tk()
    app = TaskApp(root)
    root.mainloop()

