#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio

from ceylon import Worker

worker = Worker(name="worker", port=8888, role="worker")


@worker.on(str)
async def on_message(agent_id: str, data: str, time: int) -> None:
    print(f"Received message from {agent_id}: {data} at {time}")


if __name__ == '__main__':
    asyncio.run(worker.start_agent(b""))
