import tkinter as tk
from tkinter import messagebox


class TaskManager:
    def __init__(self, master):
        self.master = master
        self.master.title("Task Manager")
        self.tasks = []

        # Frame for the task list
        self.frame = tk.Frame(self.master)
        self.frame.pack(pady=10)

        # Listbox to display tasks
        self.task_listbox = tk.Listbox(self.frame, width=50, height=10, selectmode=tk.SINGLE)
        self.task_listbox.pack(side=tk.LEFT)

        # Scrollbar for the listbox
        self.scrollbar = tk.Scrollbar(self.frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.task_listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.task_listbox.yview)

        # Entry and buttons
        self.entry = tk.Entry(self.master, width=52)
        self.entry.pack(pady=10)

        self.add_task_button = tk.Button(self.master, text="Add Task", command=self.add_task)
        self.add_task_button.pack(pady=5)

        self.complete_task_button = tk.Button(self.master, text="Complete Task", command=self.complete_task)
        self.complete_task_button.pack(pady=5)

        self.list_tasks_button = tk.Button(self.master, text="List Tasks", command=self.list_tasks)
        self.list_tasks_button.pack(pady=5)

    def add_task(self):
        task = self.entry.get()
        if task:
            self.tasks.append(task)
            self.entry.delete(0, tk.END)
            self.update_task_listbox()
        else:
            messagebox.showwarning("Warning", "Please enter a task.")

    def complete_task(self):
        try:
            selected_index = self.task_listbox.curselection()[0]
            completed_task = self.tasks.pop(selected_index)
            messagebox.showinfo("Task Completed", f"You have completed: {completed_task}")
            self.update_task_listbox()
        except IndexError:
            messagebox.showwarning("Warning", "Please select a task to complete.")

    def list_tasks(self):
        if not self.tasks:
            messagebox.showinfo("Tasks", "No tasks available.")
        else:
            task_list = "\n".join(self.tasks)
            messagebox.showinfo("Tasks", f"Your tasks:\n{task_list}")

    def update_task_listbox(self):
        self.task_listbox.delete(0, tk.END)
        for task in self.tasks:
            self.task_listbox.insert(tk.END, task)


root = tk.Tk()
task_manager = TaskManager(root)
root.mainloop()




