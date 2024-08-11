from langchain_community.chat_models import ChatOllama

from ceylon.llm import TaskManager
from ceylon.llm.agent import SpecializedAgent
from ceylon.llm.data_types import Task

if __name__ == "__main__":

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    # Create tasks with subtasks
    tasks = [
        Task(id=1, description="Create an article about AI advancements"),
    ]

    # Create specialized agents
    specialized_agents = [
        SpecializedAgent(
            name="ContentWriter",
            context="Content writing and research",
            skills=["Blog writing", "Article writing", "Copywriting", "SEO writing"],
            experience_level="Expert",
            tools=["Google Docs", "Grammarly", "Hemingway Editor", "WordPress"],
            llm=llm
        ),
        SpecializedAgent(
            name="ImageGenerator",
            context="AI image generation and editing",
            skills=["DALL-E prompting", "Midjourney", "Photoshop", "Canva"],
            experience_level="Advanced",
            tools=["DALL-E", "Midjourney", "Adobe Photoshop", "Canva"],
            llm=llm
        ),
        SpecializedAgent(
            name="Editor",
            context="Proofreading, editing, and formatting",
            skills=["Copy editing", "Content editing", "Style guide implementation", "Formatting"],
            experience_level="Expert",
            tools=["Microsoft Word", "Google Docs", "Grammarly", "Chicago Manual of Style"],
            llm=llm
        ),
        SpecializedAgent(
            name="SEOMaster",
            context="Search engine optimization and content optimization",
            skills=["Keyword research", "On-page SEO", "Technical SEO", "Link building"],
            experience_level="Expert",
            tools=["SEMrush", "Ahrefs", "Google Analytics", "Google Search Console"],
            llm=llm
        ),
        SpecializedAgent(
            name="ContentResearcher",
            context="Content research and analysis",
            skills=["Academic research", "Market research", "Data collection", "Trend analysis"],
            experience_level="Advanced",
            tools=["Google Scholar", "JSTOR", "LexisNexis", "Statista"],
            llm=llm
        ),
        SpecializedAgent(
            name="UIDesigner",
            context="UI/UX design and frontend development",
            skills=["Wireframing", "Prototyping", "User testing", "Responsive design"],
            experience_level="Expert",
            tools=["Figma", "Sketch", "Adobe XD", "InVision"],
            llm=llm
        ),
        SpecializedAgent(
            name="BackendDev",
            context="Backend development and database management",
            skills=["Python", "Node.js", "SQL", "RESTful API design"],
            experience_level="Expert",
            tools=["Django", "Express.js", "PostgreSQL", "Docker"],
            llm=llm
        ),
        SpecializedAgent(
            name="FrontendDev",
            context="Frontend development and UI/UX design",
            skills=["JavaScript", "React", "HTML5", "CSS3"],
            experience_level="Expert",
            tools=["VS Code", "webpack", "npm", "Chrome DevTools"],
            llm=llm
        ),
        SpecializedAgent(
            name="DevOps",
            context="DevOps and infrastructure management",
            skills=["CI/CD", "Cloud infrastructure", "Containerization", "Monitoring"],
            experience_level="Expert",
            tools=["Jenkins", "AWS", "Docker", "Kubernetes"],
            llm=llm
        ),
        SpecializedAgent(
            name="DataAnalyst",
            context="Data analysis and statistics",
            skills=["Data visualization", "Statistical analysis", "SQL", "Excel"],
            experience_level="Advanced",
            tools=["Tableau", "R", "Python", "Microsoft Excel"],
            llm=llm
        ),
        SpecializedAgent(
            name="DataScientist",
            context="Data science and machine learning",
            skills=["Machine learning", "Deep learning", "NLP", "Big data"],
            experience_level="Expert",
            tools=["Python", "TensorFlow", "Scikit-learn", "Jupyter Notebook"],
            llm=llm
        ),
        SpecializedAgent(
            name="QATester",
            context="Software testing and quality assurance",
            skills=["Manual testing", "Automated testing", "Performance testing", "Security testing"],
            experience_level="Advanced",
            tools=["Selenium", "JUnit", "JIRA", "Postman"],
            llm=llm
        )
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, specialized_agents)
    task_manager.run_admin(inputs=b"", workers=specialized_agents)
