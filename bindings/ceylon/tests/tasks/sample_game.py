import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk
from datetime import datetime
import csv

class Task:
    def __init__(self, title, description, due_date, priority):
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.completed = False

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"{self.title} - Due: {self.due_date} - Priority: {self.priority} - Status: {status}"

class TaskManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Manager")

        self.tasks = []  # List to store Task objects

        # Menu Bar
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        # Task List Frame
        self.frame_task_list = tk.Frame(self.root)
        self.frame_task_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.task_listbox = tk.Listbox(self.frame_task_list, selectmode=tk.SINGLE)
        self.task_listbox.pack(fill=tk.BOTH, expand=True)

        # Buttons
        self.button_frame = tk.Frame(self.frame_task_list)
        self.button_frame.pack()

        tk.Button(self.button_frame, text="Add Task", command=self.add_task).pack(side=tk.LEFT)
        tk.Button(self.button_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT)
        tk.Button(self.button_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT)
        tk.Button(self.button_frame, text="Complete Task", command=self.complete_task).pack(side=tk.LEFT)
        tk.Button(self.button_frame, text="Download Tasks", command=self.download_tasks).pack(side=tk.LEFT)  # New button

        # Task Details Frame
        self.frame_task_details = tk.Frame(self.root)
        self.frame_task_details.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(self.frame_task_details, text="Title:").pack()
        self.entry_title = tk.Entry(self.frame_task_details)
        self.entry_title.pack()

        tk.Label(self.frame_task_details, text="Description:").pack()
        self.text_description = tk.Text(self.frame_task_details, height=5)
        self.text_description.pack()

        tk.Label(self.frame_task_details, text="Due Date (YYYY-MM-DD):").pack()
        self.entry_due_date = tk.Entry(self.frame_task_details)
        self.entry_due_date.pack()

        tk.Label(self.frame_task_details, text="Priority:").pack()
        self.priority_var = tk.StringVar(value="Medium")
        priority_options = ["Low", "Medium", "High"]
        self.priority_menu = ttk.Combobox(self.frame_task_details, textvariable=self.priority_var, values=priority_options)
        self.priority_menu.pack()

        tk.Button(self.frame_task_details, text="Save Task", command=self.save_task).pack()

    def add_task(self):
        self.clear_task_details()
        self.entry_title.focus()

    def edit_task(self):
        selected_task_index = self.task_listbox.curselection()
        if selected_task_index:
            task = self.tasks[selected_task_index[0]]
            self.entry_title.delete(0, tk.END)
            self.entry_title.insert(0, task.title)
            self.text_description.delete("1.0", tk.END)
            self.text_description.insert("1.0", task.description)
            self.entry_due_date.delete(0, tk.END)
            self.entry_due_date.insert(0, task.due_date)
            self.priority_var.set(task.priority)

    def delete_task(self):
        selected_task_index = self.task_listbox.curselection()
        if selected_task_index:
            del self.tasks[selected_task_index[0]]
            self.update_task_listbox()

    def complete_task(self):
        selected_task_index = self.task_listbox.curselection()
        if selected_task_index:
            task = self.tasks[selected_task_index[0]]
            task.completed = True
            self.update_task_listbox()

    def save_task(self):
        title = self.entry_title.get()
        description = self.text_description.get("1.0", tk.END).strip()
        due_date = self.entry_due_date.get()
        priority = self.priority_var.get()

        if title and due_date:
            try:
                # Validate the date format
                datetime.strptime(due_date, '%Y-%m-%d')
                task = Task(title, description, due_date, priority)
                self.tasks.append(task)
                self.update_task_listbox()
                self.clear_task_details()
                messagebox.showinfo("Info", "Task saved successfully!")
            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD.")
        else:
            messagebox.showwarning("Warning", "Title and Due Date are required.")

    def clear_task_details(self):
        self.entry_title.delete(0, tk.END)
        self.text_description.delete("1.0", tk.END)
        self.entry_due_date.delete(0, tk.END)
        self.priority_var.set("Medium")

    def update_task_listbox(self):
        # Sort tasks by priority before updating the listbox
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        self.tasks.sort(key=lambda x: priority_order[x.priority])  # Sort by priority

        self.task_listbox.delete(0, tk.END)
        for task in self.tasks:
            self.task_listbox.insert(tk.END, str(task))

    def download_tasks(self):
        # Open a file dialog to choose the save location
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                   filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, mode='w', newline='') as file:
                    writer = csv.writer(file)
                    # Write the header
                    writer.writerow(["Title", "Description", "Due Date", "Priority", "Status"])
                    for task in self.tasks:
                        writer.writerow([task.title, task.description, task.due_date, task.priority, "Completed" if task.completed else "Pending"])
                messagebox.showinfo("Success", "Tasks downloaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to download tasks: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TaskManagerApp(root)
    root.mainloop()