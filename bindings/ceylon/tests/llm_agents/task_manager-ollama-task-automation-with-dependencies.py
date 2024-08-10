from ceylon.llm import TaskManager
from ceylon.llm.agent import SpecializedAgent
from ceylon.llm.data_types import Task

if __name__ == "__main__":
    # Create tasks with subtasks
    tasks = [
        Task(id=1, description="Create an article about AI advancements"),
        # Task(id=2, description="Create a landing page for a new Food product and deploy it on the web"),
        # Task(id=3, description="Create a data collection form for a new product and deploy it on the web"),
    ]

    # Create specialized agents
    specialized_agents = [
        SpecializedAgent(
            name="ContentWriter",
            specialty="Content writing and research",
            skills=["Blog writing", "Article writing", "Copywriting", "SEO writing"],
            experience_level="Expert",
            tools=["Google Docs", "Grammarly", "Hemingway Editor", "WordPress"]
        ),
        SpecializedAgent(
            name="ImageGenerator",
            specialty="AI image generation and editing",
            skills=["DALL-E prompting", "Midjourney", "Photoshop", "Canva"],
            experience_level="Advanced",
            tools=["DALL-E", "Midjourney", "Adobe Photoshop", "Canva"]
        ),
        SpecializedAgent(
            name="Editor",
            specialty="Proofreading, editing, and formatting",
            skills=["Copy editing", "Content editing", "Style guide implementation", "Formatting"],
            experience_level="Expert",
            tools=["Microsoft Word", "Google Docs", "Grammarly", "Chicago Manual of Style"]
        ),
        SpecializedAgent(
            name="SEOMaster",
            specialty="Search engine optimization and content optimization",
            skills=["Keyword research", "On-page SEO", "Technical SEO", "Link building"],
            experience_level="Expert",
            tools=["SEMrush", "Ahrefs", "Google Analytics", "Google Search Console"]
        ),
        SpecializedAgent(
            name="ContentResearcher",
            specialty="Content research and analysis",
            skills=["Academic research", "Market research", "Data collection", "Trend analysis"],
            experience_level="Advanced",
            tools=["Google Scholar", "JSTOR", "LexisNexis", "Statista"]
        ),
        SpecializedAgent(
            name="UIDesigner",
            specialty="UI/UX design and frontend development",
            skills=["Wireframing", "Prototyping", "User testing", "Responsive design"],
            experience_level="Expert",
            tools=["Figma", "Sketch", "Adobe XD", "InVision"]
        ),
        SpecializedAgent(
            name="BackendDev",
            specialty="Backend development and database management",
            skills=["Python", "Node.js", "SQL", "RESTful API design"],
            experience_level="Expert",
            tools=["Django", "Express.js", "PostgreSQL", "Docker"]
        ),
        SpecializedAgent(
            name="FrontendDev",
            specialty="Frontend development and UI/UX design",
            skills=["JavaScript", "React", "HTML5", "CSS3"],
            experience_level="Expert",
            tools=["VS Code", "webpack", "npm", "Chrome DevTools"]
        ),
        SpecializedAgent(
            name="DevOps",
            specialty="DevOps and infrastructure management",
            skills=["CI/CD", "Cloud infrastructure", "Containerization", "Monitoring"],
            experience_level="Expert",
            tools=["Jenkins", "AWS", "Docker", "Kubernetes"]
        ),
        SpecializedAgent(
            name="DataAnalyst",
            specialty="Data analysis and statistics",
            skills=["Data visualization", "Statistical analysis", "SQL", "Excel"],
            experience_level="Advanced",
            tools=["Tableau", "R", "Python", "Microsoft Excel"]
        ),
        SpecializedAgent(
            name="DataScientist",
            specialty="Data science and machine learning",
            skills=["Machine learning", "Deep learning", "NLP", "Big data"],
            experience_level="Expert",
            tools=["Python", "TensorFlow", "Scikit-learn", "Jupyter Notebook"]
        ),
        SpecializedAgent(
            name="QATester",
            specialty="Software testing and quality assurance",
            skills=["Manual testing", "Automated testing", "Performance testing", "Security testing"],
            experience_level="Advanced",
            tools=["Selenium", "JUnit", "JIRA", "Postman"]
        )
    ]

    # Create and run task manager
    task_manager = TaskManager(tasks, specialized_agents)
    task_manager.run_admin(inputs=b"", workers=specialized_agents)