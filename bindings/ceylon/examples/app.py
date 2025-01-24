#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
from pydantic.dataclasses import dataclass

from ceylon import AgentDetail
from ceylon import Worker, Admin

import asyncio


@dataclass
class BaseData:
    name: str


ag = Admin(name="admin", port=8888, role="admin")
ag_w = Worker(name="worker_agent1", role="worker1")
ag_w1 = Worker(name="worker_agent2", role="worker_2")


@ag.on(BaseData)
async def on_message(agent_id: str, data: BaseData, time: int) -> None:
    print(f"Received message from {agent_id}: {data} at {time}")


@ag_w.on_run()
async def run_worker(inputs: bytes):
    print(f"Worker started - {ag_w.details().name} ({ag_w.details().id})")
    while True:
        print(f"Worker running - {ag_w.details().name} ({ag_w.details().id})")
        await ag_w.broadcast_message(BaseData(name=ag_w.details().name))
        await asyncio.sleep(1)


@ag_w.on_connect("*")
async def on_connect_admin(topic: str, agent: AgentDetail):
    print(f"Worker2 connected: {ag_w.details().name} ({agent.name}) - Role: {agent.role} ({topic})")


@ag_w.on_connect("*:worker2")
async def on_connect_admin2(topic: str, agent: AgentDetail):
    print(f"Worker2 connected: {ag_w.details().name} ({agent.name}) - Role: {agent.role} ({topic})")


if __name__ == '__main__':
    asyncio.run(ag.start_agent(b"", [ag_w, ag_w1]))
