from app import cy

writer_agent = cy.Agent(
    role="Writer",
    responsibility="Write an article.",
    instructions="Write an article.",
)

researcher_agent = cy.Agent(
    role="Researcher",
    responsibility="Research on the topic.",
    instructions="Research on the topic.",
)

article_writer = cy.TaskForce(
    name="Article Writer",
    description="Write an article.",
    agents=[writer_agent, researcher_agent],
    job=[
        cy.Job(
            instruction="Write an article."
        ),
        cy.Job(
            instruction="Research on the topic."
        ),
    ]
)

if __name__ == '__main__':
    article_writer.execute(
        inputs={
            "topic": "Covid-19",
        }
    )
