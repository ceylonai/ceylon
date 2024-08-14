from langchain_community.chat_models import ChatOllama

from ceylon.llm import Task, SubTask, LLMTaskAgent, LLMTaskManager

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
        LLMTaskAgent(
            name="research",
            context="Knowledge about research methodologies and tools",
            skills=["Market Research", "Data Analysis", "Literature Review"],  # Example skills
            tools=["Google Scholar", "JSTOR", "LexisNexis"],  # Example tools
            llm=llm
        ),

        LLMTaskAgent(
            name="writing",
            context="Knowledge about content writing",
            skills=["Creative Writing", "Technical Writing", "Copywriting"],  # Example skills
            tools=["Grammarly", "Hemingway Editor", "Scrivener"],  # Example tools
            llm=llm
        ),

        LLMTaskAgent(
            name="seo_optimization",
            context="Knowledge about SEO strategies and tools",
            skills=["Keyword Research", "On-Page SEO", "Content Optimization"],  # Example skills
            tools=["Ahrefs", "SEMrush", "Yoast SEO"],  # Example tools
            llm=llm
        ),

        LLMTaskAgent(
            name="web_publishing",
            context="Knowledge about web publishing tools",
            skills=["CMS Management", "HTML/CSS", "Content Scheduling"],  # Example skills
            tools=["WordPress", "Squarespace", "Medium"],  # Example tools
            llm=llm
        )
    ]

    task_manager = LLMTaskManager(tasks, agents, llm=llm)
    tasks = task_manager.do(inputs=b"")

    for t in tasks:
        print(t.final_answer)
