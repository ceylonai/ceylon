import asyncio
from typing import List, Dict

from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from loguru import logger
from pydantic.v1 import BaseModel, Field

from ceylon import Agent, CoreAdmin, on_message
from ceylon.llm import TaskManager
from ceylon.llm.agent import SpecializedAgent
from ceylon.llm.data_types import Task

if __name__ == "__main__":
    # Create tasks with subtasks
    tasks = [
        Task(id=1, description="Create an article about AI advancements"),
        Task(id=2, description="Create a landing page for a new Food product and deploy it on the web"),
        Task(id=3, description="Create a data collection form for a new product and deploy it on the web"),
    ]

    # Create specialized agents
    agents = [
        SpecializedAgent("ContentWriter", "Content writing and research"),
        SpecializedAgent("ImageGenerator", "AI image generation and editing"),
        SpecializedAgent("Editor", "Proofreading, editing, and formatting"),
        SpecializedAgent("SEOMaster", "Search engine optimization and content optimization"),
        SpecializedAgent("ContentResearcher", "Content research and analysis"),
        SpecializedAgent("UIDesigner", "UI/UX design and frontend development"),
        SpecializedAgent("BackendDev", "Backend development and database management"),
        SpecializedAgent("FrontendDev", "Frontend development and UI/UX design"),
        SpecializedAgent("DevOps", "DevOps and infrastructure management"),
        SpecializedAgent("DataAnalyst", "Data analysis and statistics"),
        SpecializedAgent("DataScientist", "Data science and machine learning"),
        SpecializedAgent("QATester", "Software testing and quality assurance")
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, agents)
    task_manager.run_admin(inputs=b"", workers=agents)
