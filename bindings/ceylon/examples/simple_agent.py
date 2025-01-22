#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio

from ceylon import enable_log
from ceylon.base.uni_agent import BaseAgent
from ceylon.ceylon import PeerMode

enable_log("INFO")


class AdminAgent(BaseAgent):
    pass


class WorkerAgent(BaseAgent):
    pass


async def main():
    admin = AdminAgent(
        port=8855,
        mode=PeerMode.ADMIN,
        name="admin"
    )

    await admin.start_agent(b"")


if __name__ == '__main__':
    asyncio.run(main())
