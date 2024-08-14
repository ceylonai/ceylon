from langchain_community.chat_models import ChatOllama

from ceylon.llm import LLMTaskManager
from ceylon.llm.agent import LLMTaskAgent
from ceylon.llm.data_types import Task

if __name__ == "__main__":

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    # Create tasks with subtasks
    tasks = [
        Task(id=1, description="Create an article about AI advancements"),
    ]

    # Create specialized agents
    specialized_agents = [
        LLMTaskAgent(
            name="ContentWriter",
            context="Content writing and research",
            skills=["Blog writing", "Article writing", "Copywriting", "SEO writing"],
            experience_level="Expert",
            tools=["Google Docs", "Grammarly", "Hemingway Editor", "WordPress"],
            llm=llm
        ),
        LLMTaskAgent(
            name="ImageGenerator",
            context="AI image generation and editing",
            skills=["DALL-E prompting", "Midjourney", "Photoshop", "Canva"],
            experience_level="Advanced",
            tools=["DALL-E", "Midjourney", "Adobe Photoshop", "Canva"],
            llm=llm
        ),
        LLMTaskAgent(
            name="Editor",
            context="Proofreading, editing, and formatting",
            skills=["Copy editing", "Content editing", "Style guide implementation", "Formatting"],
            experience_level="Expert",
            tools=["Microsoft Word", "Google Docs", "Grammarly", "Chicago Manual of Style"],
            llm=llm
        ),
        LLMTaskAgent(
            name="SEOMaster",
            context="Search engine optimization and content optimization",
            skills=["Keyword research", "On-page SEO", "Technical SEO", "Link building"],
            experience_level="Expert",
            tools=["SEMrush", "Ahrefs", "Google Analytics", "Google Search Console"],
            llm=llm
        ),
        LLMTaskAgent(
            name="ContentResearcher",
            context="Content research and analysis",
            skills=["Academic research", "Market research", "Data collection", "Trend analysis"],
            experience_level="Advanced",
            tools=["Google Scholar", "JSTOR", "LexisNexis", "Statista"],
            llm=llm
        ),
        LLMTaskAgent(
            name="UIDesigner",
            context="UI/UX design and frontend development",
            skills=["Wireframing", "Prototyping", "User testing", "Responsive design"],
            experience_level="Expert",
            tools=["Figma", "Sketch", "Adobe XD", "InVision"],
            llm=llm
        ),
        LLMTaskAgent(
            name="BackendDev",
            context="Backend development and database management",
            skills=["Python", "Node.js", "SQL", "RESTful API design"],
            experience_level="Expert",
            tools=["Django", "Express.js", "PostgreSQL", "Docker"],
            llm=llm
        ),
        LLMTaskAgent(
            name="FrontendDev",
            context="Frontend development and UI/UX design",
            skills=["JavaScript", "React", "HTML5", "CSS3"],
            experience_level="Expert",
            tools=["VS Code", "webpack", "npm", "Chrome DevTools"],
            llm=llm
        ),
        LLMTaskAgent(
            name="DevOps",
            context="DevOps and infrastructure management",
            skills=["CI/CD", "Cloud infrastructure", "Containerization", "Monitoring"],
            experience_level="Expert",
            tools=["Jenkins", "AWS", "Docker", "Kubernetes"],
            llm=llm
        ),
        LLMTaskAgent(
            name="DataAnalyst",
            context="Data analysis and statistics",
            skills=["Data visualization", "Statistical analysis", "SQL", "Excel"],
            experience_level="Advanced",
            tools=["Tableau", "R", "Python", "Microsoft Excel"],
            llm=llm
        ),
        LLMTaskAgent(
            name="DataScientist",
            context="Data science and machine learning",
            skills=["Machine learning", "Deep learning", "NLP", "Big data"],
            experience_level="Expert",
            tools=["Python", "TensorFlow", "Scikit-learn", "Jupyter Notebook"],
            llm=llm
        ),
        LLMTaskAgent(
            name="QATester",
            context="Software testing and quality assurance",
            skills=["Manual testing", "Automated testing", "Performance testing", "Security testing"],
            experience_level="Advanced",
            tools=["Selenium", "JUnit", "JIRA", "Postman"],
            llm=llm
        )
    ]

    # Create and run task manager
    task_manager = LLMTaskManager(tasks, specialized_agents)
    task_manager.run_admin(inputs=b"", workers=specialized_agents)
