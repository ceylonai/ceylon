import asyncio
from dataclasses import dataclass

from loguru import logger

from ceylon import Worker, AgentDetail
from ceylon.base.playground import BasePlayGround
from ceylon.llm.agent import LLMAgent, LLMConfig, LLMResponse
from ceylon.llm.models.ollama import OllamaModel
from ceylon.task import TaskManager
from ceylon.task.data import TaskMessage


@dataclass
class SimpleMessage:
    content: str


playground = BasePlayGround(name="minimal_demo")
agent = LLMAgent(
    name="writer_1",
    llm_model=OllamaModel(
        model_name="llama3.2",
        base_url="http://localhost:11434"
    ),
    config=LLMConfig(
        system_prompt=(
            f"You are an expert content writer specializing in financial writing. "
            "Create engaging and informative content in your distinctive style."
        ),
        temperature=0.7,
        max_tokens=1000,
        retry_attempts=2
    ),
    worker_role="content_writer"
)


@agent.on(SimpleMessage)
async def handle_message(message: SimpleMessage, sender: AgentDetail, time: int):
    logger.info(f"From {sender.name} received: {message.content}")


async def main():
    # Create playground and worker

    async with playground.play(workers=[agent]) as active_playground:
        # Send a message
        message = TaskMessage(content="Hello from worker1!")
        await active_playground.broadcast_message(message)



if __name__ == "__main__":
    asyncio.run(main())
