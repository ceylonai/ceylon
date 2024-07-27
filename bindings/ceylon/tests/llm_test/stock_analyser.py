from time import sleep

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
                "job": request.job_id,
                "trade": True,
            }
        )


ta_worker = TAAgent(name="ta", role="Technical Analyst")
ta_worker2 = TAAgent(name="ta2", role="Technical Analyst2")
ta_worker3 = TAAgent(name="ta2", role="Technical Analyst3")
news_sentiment_worker = NewAnalysisAgent(name="news_sentiment", role="Technical Analyst")
decision_maker_worker = DecisionMakerAgent(name="decision_maker", role="Make Decision")

chief = RunnerAgent(workers=[ta_worker, ta_worker2, ta_worker3, news_sentiment_worker, decision_maker_worker],
                    tool_llm=llm_lib,
                    parallel_jobs=1,
                    server_mode=False)

job = JobRequest(
    title=f"{10} write_article",
    explanation="Write an article about machine learning, Tone: Informal, Style: Creative, Length: Large",
    steps=JobSteps(steps=[
        Step(
            worker="ta",
            explanation="",
            dependencies=[]
        ),
        Step(
            worker="ta2",
            explanation="",
            dependencies=[]
        ),
        Step(
            worker="news_sentiment",
            explanation="",
            dependencies=["ta2"]
        ),
        Step(
            worker="decision_maker",
            explanation="",
            dependencies=["ta", "news_sentiment"]
        )
    ])
)
res = chief.execute(job)
print("Finished job: ", job.id, job.current_status, res.id)
