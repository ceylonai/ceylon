from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

import networkx as nx
from langchain.chains.llm import LLMChain
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from ceylon import Agent, on_message, CoreAdmin


class SubTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias='_id')
    parent_task_id: Optional[str] = Field(default=None)
    name: str
    description: str
    required_specialty: str
    depends_on: Set[str] = Field(default_factory=set)
    completed: bool = False

    result: Optional[str] = None

    def complete(self, result: Optional[str] = None):
        self.result = result
        self.completed = True

    def __str__(self):
        status = "Completed" if self.completed else "Pending"
        return f"SubTask: {self.name} (ID: {self.id}) - {status} - Dependencies: {self.depends_on}"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), alias='_id')
    name: str
    description: str
    subtasks: Dict[str, SubTask] = Field(default_factory=dict)

    execution_order: List[str] = Field(default_factory=list)

    def add_subtask(self, subtask: SubTask):
        if subtask.name in self.subtasks:
            raise ValueError(f"Subtask with id {subtask.name} already exists")

        self.subtasks[subtask.name] = subtask
        self._validate_dependencies()
        self.execution_order = self.get_execution_order()

    def _validate_dependencies(self):
        graph = self._create_dependency_graph()
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("The dependencies create a cycle")

    def _create_dependency_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for subtask in self.subtasks.values():
            graph.add_node(subtask.name)
        return graph

    def validate_sub_tasks(self) -> bool:
        subtask_names = set(self.subtasks.keys())

        # Check if all dependencies are present
        for subtask in self.subtasks.values():
            if not subtask.depends_on.issubset(subtask_names):
                missing_deps = subtask.depends_on - subtask_names
                print(f"Subtask '{subtask.name}' has missing dependencies: {missing_deps}")
                return False

        # Check for circular dependencies
        try:
            self._validate_dependencies()
        except ValueError as e:
            print(f"Circular dependency detected: {str(e)}")
            return False

        return True

    def get_execution_order(self) -> List[str]:
        graph = self._create_dependency_graph()
        return list(nx.topological_sort(graph))

    def get_next_subtask(self) -> Optional[Tuple[str, SubTask]]:
        for subtask_name in self.execution_order:
            subtask = self.subtasks[subtask_name]
            if all(self.subtasks[dep].completed for dep in subtask.depends_on):
                return (subtask_name, subtask)
        return None

    def update_subtask_status(self, subtask_name: str, result: str):
        if subtask_name not in self.subtasks:
            raise ValueError(f"Subtask {subtask_name} not found")

        subtask = self.subtasks[subtask_name]
        if result is not None:
            subtask.complete()

        if subtask_name in self.execution_order:
            self.execution_order.remove(subtask_name)

    def is_completed(self) -> bool:
        return all(subtask.completed for subtask in self.subtasks.values())

    def __str__(self):
        return f"Task: {self.name}\nSubtasks:\n" + "\n".join(str(st) for st in self.subtasks.values())

    @staticmethod
    def create_task(name: str, description: str, subtasks: List[SubTask] = None) -> 'Task':
        task = Task(name=name, description=description)
        if subtasks:
            for subtask in subtasks:
                subtask.parent_task_id = task.id
                task.add_subtask(subtask)
        return task


def execute_task(task: Task) -> None:
    while True:
        # Get the next subtask
        next_subtask: Optional[tuple[str, SubTask]] = task.get_next_subtask()

        # If there are no more subtasks, break the loop
        if next_subtask is None:
            break

        subtask_name, subtask = next_subtask
        print(f"Executing: {subtask}")

        # Here you would actually execute the subtask
        # For this example, we'll simulate execution with a simple print statement
        print(f"Simulating execution of {subtask_name}")

        # Simulate a result (in a real scenario, this would be the outcome of the subtask execution)
        result = "success"

        # Update the subtask status
        task.update_subtask_status(subtask_name, result)

        # Check if the entire task is completed
        if task.is_completed():
            print("All subtasks completed successfully!")
            break

    # Final check to see if all subtasks were completed
    if task.is_completed():
        print("Task execution completed successfully!")
    else:
        print("Task execution incomplete. Some subtasks may have failed.")


class TaskAssignment(BaseModel):
    task: SubTask
    assigned_agent: str


class TaskResult(BaseModel):
    task_id: str
    parent_task_id: str
    agent: str
    result: str


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str):
        self.specialty = specialty
        self.history = {}
        super().__init__(name=name, workspace_id="openai_task_management", admin_port=8000)

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.task.description}")

            task_related_history = self.history.get(data.task.parent_task_id, [])
            if task_related_history:
                print("Task history:", task_related_history)

            # Simulate task execution
            # await asyncio.sleep(2)
            result = f"{self.details().name} completed the subtask: {data.task.description}"
            result_task = TaskResult(task_id=data.task.id, subtask_id=data.task.name, agent=self.details().name,
                                     parent_task_id=data.task.parent_task_id,
                                     result=result)

            # Update task history
            await self.add_result_to_history(result_task)
            await self.broadcast_data(result_task)

    @on_message(type=TaskResult)
    async def on_task_result(self, data: TaskResult):
        await self.add_result_to_history(data)

    async def add_result_to_history(self, data: TaskResult):
        if data.parent_task_id in self.history:
            self.history[data.parent_task_id].append(data)
        else:
            self.history[data.parent_task_id] = [data]


class TaskManager(CoreAdmin):
    tasks: List[Task] = []
    agents: List[SpecializedAgent] = []
    results: Dict[str, List[TaskResult]] = {}

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent]):
        self.tasks = tasks
        self.agents = agents
        super().__init__(name="openai_task_management", port=8000)

    async def run(self, inputs: bytes):
        for idx, task in enumerate(self.tasks):
            if task.validate_sub_tasks():
                logger.info(f"Task {task.name} is valid")
            else:
                logger.info(f"Task {task.name} is invalid")
                del self.tasks[idx]

        await self.run_tasks()

    async def run_tasks(self):
        if len(self.tasks) == 0:
            logger.info("No tasks found")
            return
        for task in self.tasks:
            self.results[task.id] = []
            sub_task = task.get_next_subtask()
            if sub_task is None:
                continue
            subtask_name, subtask_ = sub_task
            assigned_agent = await self.get_best_agent_for_subtask(subtask_)
            await self.broadcast_data(TaskAssignment(task=subtask_, assigned_agent=assigned_agent))

    @on_message(type=TaskResult)
    async def on_task_result(self, result: TaskResult):
        for task in self.tasks:
            sub_task = task.get_next_subtask()
            if sub_task is None or result.task_id != sub_task[1].id:
                continue
            if result.task_id == sub_task[1].id:
                task.update_subtask_status(sub_task[1].name, result.result)
                break

        if self.all_tasks_completed():
            await self.end_task_management()

        await self.run_tasks()

    def all_tasks_completed(self) -> bool:
        for task in self.tasks:
            subtask_completed_status = [st.completed for st in task.subtasks.values()]
            if not all(subtask_completed_status):
                return False
        return True

    async def end_task_management(self):
        logger.info("All tasks completed. Results:")
        for task in self.tasks:
            logger.info(f"Task {task.id} results:")
            for result in self.results[task.id]:
                logger.info(f"  Subtask {result.subtask_id}: {result.result}")
        await self.stop()

    async def get_best_agent_for_subtask(self, subtask: SubTask) -> str:
        agent_specialties = "\n".join([f"{agent.details().name}: {agent.specialty}" for agent in self.agents])
        llm = ChatOllama(model="llama3.1:latest", temperature=0)

        prompt_template = ChatPromptTemplate.from_template(
            """Given the following subtask and list of agents with their specialties, determine which agent is 
            best suited for the subtask.        

            Subtask: {subtask_description}
            Required Specialty: {required_specialty}
            
            Agents and their specialties:
            {agent_specialties}
            
            Respond with only the name of the best-suited agent."""
        )

        chain = LLMChain(llm=llm, prompt=prompt_template)
        response = chain.run(subtask_description=subtask.description, required_specialty=subtask.required_specialty,
                             agent_specialties=agent_specialties)
        return response.strip()


# Example usage
if __name__ == "__main__":
    # Create a task with initial subtasks
    web_app = Task.create_task("Build Web App", "Create a simple web application",
                               subtasks=[
                                   SubTask(name="setup", description="Set up the development environment",
                                           required_specialty="Knowledge about deployment and development tools"),
                                   SubTask(name="database", description="Set up the database",
                                           required_specialty="Knowledge about database management tools"),
                                   SubTask(name="testing", description="Perform unit and integration tests",
                                           depends_on={"backend", "frontend"},
                                           required_specialty="Knowledge about testing tools"),
                                   SubTask(name="frontend", description="Develop the frontend UI",
                                           depends_on={"setup", "backend"},
                                           required_specialty="Knowledge about frontend tools"),
                                   SubTask(name="backend", description="Develop the backend API",
                                           depends_on={"setup", "database"},
                                           required_specialty="Knowledge about backend tools"),
                                   SubTask(name="deployment", description="Deploy the application",
                                           depends_on={"testing", "qa"},
                                           required_specialty="Knowledge about deployment tools and CI tools"),
                                   SubTask(name="delivery", description="Deploy the application",
                                           depends_on={"deployment"},
                                           required_specialty="Knowledge about delivery tools"),
                                   SubTask(name="qa", description="Perform quality assurance",
                                           depends_on={"testing"},
                                           required_specialty="Knowledge about testing tools")

                               ])

    tasks = [
        web_app
    ]

    # Create specialized agents
    agents = [
        SpecializedAgent("backend", "Knowledge about backend tools"),
        SpecializedAgent("frontend", "Knowledge about frontend tools"),
        SpecializedAgent("database", "Knowledge about database management tools"),
        SpecializedAgent("deployment", "Knowledge about deployment tools and CI tools"),
        SpecializedAgent("qa", "Knowledge about testing tools"),
        SpecializedAgent("delivery", "Knowledge about delivery tools")
    ]
    task_manager = TaskManager(tasks, agents)
    task_manager.run_admin(inputs=b"", workers=agents)
