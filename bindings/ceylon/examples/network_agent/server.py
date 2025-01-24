#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio

from ceylon import Admin

app = Admin(name="admin", port=8888, role="admin")


@app.on_run()
async def run_worker(inputs: bytes):
    print(f"Worker started - {app.details().name} ({app.details().id})")
    while True:
        print(f"Worker running - {app.details().name} ({app.details().id})")
        await app.broadcast_message("Hello World from Server")
        # await asyncio.sleep(0.0001)


if __name__ == '__main__':
    asyncio.run(app.start_agent(b"", []))
