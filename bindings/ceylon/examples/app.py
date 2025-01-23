#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from pydantic.dataclasses import dataclass

from ceylon.base.agents import Worker, Admin

ag = Admin(name="worker_agent", port=8874)


@dataclass
class BaseData:
    name: str


@ag.on(BaseData)
async def on_message(agent_id: str, data: BaseData, time: int) -> None:
    print(f"Received message from {agent_id}: {data} at {time}")


class WorkerAgent(Worker):

    async def run(self, inputs: bytes):
        print(f"Worker started - {self.details().name} ({self.details().id})")
        while True:
            print(f"Worker running - {self.details().name} ({self.details().id})")
            await self.broadcast_message(BaseData(name=self.details().name))
            await asyncio.sleep(1)


if __name__ == '__main__':
    import asyncio

    asyncio.run(ag.start_agent(b"", [WorkerAgent(
        name="worker_agent",
        role="worker", )]))
