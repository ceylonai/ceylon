import asyncio

from ceylon.llm.agent import LLMAgent
from ceylon.llm.playground import PlayGround

playground = PlayGround()
agent1 = LLMAgent(
    name="agent1",
    role="worker",
    system_prompt="You are a helpful assistant."
)
agent2 = LLMAgent(
    name="agent2",
    role="worker",
    system_prompt="You are another helpful assistant."
)


@agent1.on(dict)
async def on_message(agent_id: str, data: dict, time: int) -> None:
    print(f"{agent1.details().name} Received message from {agent_id}: {data} at {time}")


@agent2.on(dict)
async def on_message2(agent_id: str, data: dict, time: int) -> None:
    print(f"{agent2.details().name}Received message from {agent_id}: {data} at {time}")


async def main():
    # Create playground and agents
    workers = [agent1, agent2]
    async with playground.play(workers=workers) as active_playground:
        pl: PlayGround = active_playground
        while True:
            await pl.broadcast_message({"type": "worker_status", "name": agent1.details().name, "messages_received": 1})
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
