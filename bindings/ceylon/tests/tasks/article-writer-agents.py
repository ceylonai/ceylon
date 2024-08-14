from langchain_community.chat_models import ChatOllama

from ceylon.task import Task, SubTask
from ceylon.llm import  LLMTaskOperator,LLMTaskCoordinator

# Example usage
if __name__ == "__main__":
    # Create a task with initial subtasks
    article_task = Task.create_task("Write Article", "Write an article about AI advancements",
                                    subtasks=[
                                        SubTask(name="research", description="Conduct research for the article",
                                                required_specialty="Knowledge about research methodologies and tools"),
                                        SubTask(name="writing", description="Write the main content of the article",
                                                depends_on={"research"},
                                                required_specialty="Knowledge about content writing"),
                                        SubTask(name="seo_optimization", description="Optimize the article for SEO",
                                                depends_on={"writing"},
                                                required_specialty="Knowledge about SEO strategies and tools"),
                                        SubTask(name="web_publishing",
                                                description="Final article for web publishing, need to ready for publication",
                                                depends_on={"seo_optimization"},
                                                required_specialty="Knowledge about web publishing tools"),
                                    ])

    tasks = [
        article_task
    ]

    llm = ChatOllama(model="llama3.1:latest", temperature=0)

    # Create specialized agents
    agents = [
        LLMTaskOperator(
            name="research",
            role="Researcher",
            context="Knowledge about research methodologies and tools",
            skills=["Market Research", "Data Analysis", "Literature Review"],  # Example skills
            llm=llm
        ),

        LLMTaskOperator(
            name="writing",
            role="Content Writer",
            context="Knowledge about content writing",
            skills=["Creative Writing", "Technical Writing", "Copywriting"],  # Example skills
            llm=llm
        ),

        LLMTaskOperator(
            name="seo_optimization",
            role="SEO Expert",
            context="Knowledge about SEO strategies and tools",
            skills=["Keyword Research", "On-Page SEO", "Content Optimization"],  # Example skills
            llm=llm
        ),

        LLMTaskOperator(
            name="web_publishing",
            role="Writer",
            context="Knowledge about web publishing tools",
            skills=["CMS Management", "HTML/CSS", "Content Scheduling"],  # Example skills
            llm=llm
        )
    ]

    task_manager = LLMTaskCoordinator(tasks, agents, llm=llm)
    tasks = task_manager.do(inputs=b"")

    for t in tasks:
        print(t.final_answer)
