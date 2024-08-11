from langchain_community.chat_models import ChatOllama
from langchain_experimental.llms.ollama_functions import OllamaFunctions

from ceylon.llm import Task, SubTask, SpecializedAgent, TaskManager

# Example usage
if __name__ == "__main__":
    # Create a task with initial subtasks
    article_task = Task(name="Write Article", description="Write an article about AI advancements")

    tasks = [
        article_task
    ]

    llm = ChatOllama(model="llama3.1:latest", temperature=0)
    tool_llm = OllamaFunctions(model="llama3.1:latest", format="json", temperature=0.7)

    # Create specialized agents
    agents = [
        SpecializedAgent(
            name="research",
            role="Research Analyst",
            context="Extensive knowledge of research methodologies,"
                    " data collection techniques, and analytical tools. "
                    "Proficient in both qualitative and quantitative research methods. "
                    "Familiar with academic, market, and industry-specific research practices.",
            skills=[
                "Market Research",
                "Data Analysis",
                "Literature Review",
                "Survey Design",
                "Interviewing Techniques",
                "Statistical Analysis",
                "Trend Forecasting",
                "Competitive Intelligence",
                "Research Report Writing",
                "Data Visualization"
            ],
            tools=[
                "Google Scholar",
                "JSTOR",
                "LexisNexis",
                "SPSS",
                "Tableau",
                "Qualtrics",
                "Web of Science",
                "EndNote",
                "NVivo",
                "R Programming"
            ],
            llm=llm
        ),

        SpecializedAgent(
            name="writing",
            role="Content Strategist & Writer",
            context="Deep understanding of various writing styles, content formats, "
                    "and audience engagement strategies. Knowledgeable about "
                    "SEO-friendly writing, storytelling techniques, and brand voice "
                    "development. Familiar with content management systems and digital publishing platforms.",
            skills=[
                "Creative Writing",
                "Technical Writing",
                "Copywriting",
                "Content Strategy",
                "Storytelling",
                "SEO Writing",
                "Editing and Proofreading",
                "Brand Voice Development",
                "Audience Analysis",
                "Multimedia Content Creation"
            ],
            tools=[
                "Grammarly",
                "Hemingway Editor",
                "Scrivener",
                "CoSchedule Headline Analyzer",
                "Canva",
                "Airtable",
                "Trello",
                "Google Docs",
                "Copyscape",
                "Readable"
            ],
            llm=llm
        ),

        SpecializedAgent(
            name="seo_optimization",
            role="SEO Strategist",
            context="Comprehensive understanding of search engine algorithms,"
                    " ranking factors, and SEO best practices. Proficient in technical SEO,"
                    " content optimization, and link building strategies. Familiar with local SEO,"
                    " mobile optimization, and voice search optimization.",
            skills=[
                "Keyword Research",
                "On-Page SEO",
                "Off-Page SEO",
                "Technical SEO",
                "Content Optimization",
                "Link Building",
                "Local SEO",
                "Mobile SEO",
                "Voice Search Optimization",
                "SEO Analytics and Reporting"
            ],
            tools=[
                "Ahrefs",
                "SEMrush",
                "Yoast SEO",
                "Google Search Console",
                "Google Analytics",
                "Moz Pro",
                "Screaming Frog",
                "BrightLocal",
                "Answer the Public",
                "SpyFu"
            ],
            llm=llm
        ),

        SpecializedAgent(
            name="web_publishing",
            role="Digital Content Manager",
            context="Extensive knowledge of web publishing platforms, "
                    "content management systems, and digital asset management. "
                    "Proficient in HTML, CSS, and basic JavaScript. Familiar with web accessibility standards, "
                    "responsive design principles, and UX/UI best practices.",
            skills=[
                "CMS Management",
                "HTML/CSS",
                "Content Scheduling",
                "Digital Asset Management",
                "Web Accessibility",
                "Responsive Design",
                "Version Control",
                "A/B Testing",
                "Web Analytics",
                "User Experience Optimization"
            ],
            tools=[
                "WordPress",
                "Squarespace",
                "Medium",
                "Git",
                "Adobe Experience Manager",
                "Drupal",
                "Cloudinary",
                "Google Tag Manager",
                "Optimizely",
                "Hotjar"
            ],
            llm=llm
        )
    ]

    task_manager = TaskManager(tasks, agents, tool_llm=tool_llm, llm=llm)
    tasks = task_manager.do(inputs=b"")

    for t in tasks:
        print(t.final_answer)
