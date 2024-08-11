import copy
from typing import Dict, List

from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from ceylon import Agent, on_message, CoreAdmin
from ceylon.llm import Task, SubTask, TaskAssignment, TaskResult


class SpecializedAgent(Agent):
    def __init__(self, name: str, specialty: str, skills: List[str], experience_level: str,
                 tools: List[str], llm=None):
        self.specialty = specialty
        self.skills = skills
        self.experience_level = experience_level
        self.tools = tools
        self.task_history = []
        self.llm = copy.copy(llm)
        self.history: Dict[str, List[TaskResult]] = {}
        super().__init__(name=name, workspace_id="openai_task_management", admin_port=8000)

    async def get_llm_response(self, task_description: str, parent_task_id: str) -> str:
        # Construct the agent profile context
        agent_profile = f"""
        Agent Profile:
        - Name: {self.details().name}
        - Specialty: {self.specialty}
        - Skills: {', '.join(self.skills)}
        - Experience Level: {self.experience_level}
        - Available Tools: {', '.join(self.tools)}
        """

        # Construct the task information context
        task_info = f"""
        Task Information:
        - Description: {task_description}
        
        Recent Task History:
        {self._format_task_history(parent_task_id)}
        """

        # Combine all context information
        context = f"{agent_profile}\n\n{task_info}"

        # Create the prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(
                content="You are an AI assistant helping a specialized agent. "
                        "Use the following context to provide the best approach for the task."),
            HumanMessage(
                content=f"{context}\n\nGiven this information, what's the best"
                        f"approach to complete this task efficiently and effectively?")
        ])

        try:
            runnable = prompt_template | self.llm | StrOutputParser()
            response = runnable.invoke({
                context: context
            })
            return response
        except Exception as e:
            logger.error(f"Error in LLM request: {e}")
            return "Error in processing the task with LLM."

    def _format_task_history(self, task_id) -> str:
        if task_id not in self.history:
            return ""

        history = "\n".join([f"- {task.result}" for task in self.history[task_id]])
        return history

    @on_message(type=TaskAssignment)
    async def on_task_assignment(self, data: TaskAssignment):
        if data.assigned_agent == self.details().name:
            logger.info(f"{self.details().name} received subtask: {data.task.description}")
            result = await self.get_llm_response(
                data.task.description,
                data.task.parent_task_id
            )
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

    def __init__(self, tasks: List[Task], agents: List[SpecializedAgent], tool_llm=None):
        self.tool_llm = tool_llm
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

        prompt_template = ChatPromptTemplate.from_template(
            """Given the following subtask and list of agents with their specialties, determine which agent is 
            best suited for the subtask.        

            Subtask: {subtask_description}
            Required Specialty: {required_specialty}
            
            Agents and their specialties:
            {agent_specialties}
            
            Respond with only the name of the best-suited agent."""
        )
        runnable = prompt_template | self.tool_llm | StrOutputParser()

        response = runnable.invoke({
            "subtask_description": subtask.description,
            "required_specialty": subtask.required_specialty,
            "agent_specialties": agent_specialties
        })
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

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    # Create specialized agents
    agents = [
        SpecializedAgent(
            name="backend",
            specialty="Knowledge about backend tools",
            skills=["Python", "Java", "Node.js"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["Django", "Spring Boot", "Express.js"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="frontend",
            specialty="Knowledge about frontend tools",
            skills=["HTML", "CSS", "JavaScript", "React"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["React", "Angular", "Vue.js"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="database",
            specialty="Knowledge about database management tools",
            skills=["SQL", "NoSQL", "Database Design"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["MySQL", "MongoDB", "PostgreSQL"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="deployment",
            specialty="Knowledge about deployment tools and CI tools",
            skills=["CI/CD", "Docker", "Kubernetes"],  # Example skills
            experience_level="Advanced",  # Example experience level
            tools=["Jenkins", "Docker", "Kubernetes"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="qa",
            specialty="Knowledge about testing tools",
            skills=["Automated Testing", "Manual Testing", "Test Case Design"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["Selenium", "JUnit", "TestNG"],  # Example tools
            llm=llm
        ),

        SpecializedAgent(
            name="delivery",
            specialty="Knowledge about delivery tools",
            skills=["Release Management", "Continuous Delivery"],  # Example skills
            experience_level="Intermediate",  # Example experience level
            tools=["Jira", "Confluence", "GitLab CI"],  # Example tools
            llm=llm
        )

    ]
    task_manager = TaskManager(tasks, agents, tool_llm=llm)
    task_manager.run_admin(inputs=b"", workers=agents)
