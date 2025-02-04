import asyncio
from dataclasses import dataclass

from loguru import logger

from ceylon import Worker, AgentDetail
from ceylon.base.playground import BasePlayGround


@dataclass
class SimpleMessage:
    content: str


playground = BasePlayGround(name="minimal_demo")
agent = Worker("worker1")


@agent.on(SimpleMessage)
async def handle_message(message: SimpleMessage, sender: AgentDetail, time: int):
    logger.info(f"From {sender.name} received: {message.content}")


async def main():
    # Create playground and worker

    async with playground.play(workers=[agent]) as active_playground:
        # Send a message
        message = SimpleMessage(content="Hello from worker1!")
        await active_playground.broadcast_message(message)


if __name__ == "__main__":
    asyncio.run(main())
