from langchain_community.chat_models import ChatOllama

from ceylon import Agent, AgentJobStepRequest, AgentJobResponse, JobRequest, JobSteps, Step, RunnerAgent

llm_lib = ChatOllama(model="llama3:instruct")


class TAAgent(Agent):

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        return AgentJobResponse(
            worker=self.details().name,
            job_data={
                "MA": 100.0,
                "EMA": 200.0,
            }
        )


class NewAnalysisAgent(Agent):

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        return AgentJobResponse(
            worker=self.details().name,
            job_data={
                "sentiment": "Positive",
            }
        )


class DecisionMakerAgent(Agent):

    async def execute_request(self, request: AgentJobStepRequest) -> AgentJobResponse:
        return AgentJobResponse(
            worker=self.details().name,
            job_data={
                "trade": True,
            }
        )


ta_worker = TAAgent(name="ta", role="Technical Analyst")
news_sentiment_worker = NewAnalysisAgent(name="news_sentiment", role="Technical Analyst")
decision_maker_worker = DecisionMakerAgent(name="decision_maker", role="Make Decision")

chief = RunnerAgent(workers=[ta_worker, news_sentiment_worker, decision_maker_worker], tool_llm=llm_lib,
                    server_mode=False)
for i in range(10):
    job = JobRequest(
        title=f"{i} write_article",
        explanation="Write an article about machine learning, Tone: Informal, Style: Creative, Length: Large",
        steps=JobSteps(steps=[
            Step(
                worker="ta",
                explanation="",
                dependencies=[]
            ),
            Step(
                worker="news_sentiment",
                explanation="",
                dependencies=[]
            ),
            Step(
                worker="decision_maker",
                explanation="",
                dependencies=["ta", "news_sentiment"]
            )
        ])
    )
    res = chief.execute(job)
    print(res)
