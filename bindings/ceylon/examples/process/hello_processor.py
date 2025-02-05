#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from typing import Any

from ceylon.processor.agent import ProcessWorker
from ceylon.processor.data import ProcessRequest
from ceylon.processor.playground import ProcessPlayGround


class UpperCaseProcessor(ProcessWorker):

    async def _processor(self, request: ProcessRequest, time: int) -> tuple[Any, dict]:
        """Process the input text by converting it to uppercase"""
        try:
            # Convert input to string and make uppercase
            if isinstance(request.data, str):
                result = request.data.upper()
            else:
                result = str(request.data).upper()

            # Return result and empty metadata
            return result, {}

        except Exception as e:
            raise Exception(f"Error processing text: {str(e)}")


async def main():
    # Create playground and worker
    playground = ProcessPlayGround(name="text_playground", port=8888)
    worker = UpperCaseProcessor(name="uppercase_worker", role="uppercase_processor")

    # Start playground with worker
    async with playground.play(workers=[worker]) as pg:
        # Create a process request
        request = ProcessRequest(
            task_type="uppercase_processor",
            data="Hello, World!"
        )

        # Send request and wait for response
        response = await pg.process_request(request)

        # Print results
        print(f"Original text: {request.data}")
        print(f"Processed text: {response.result}")
        print(f"Process status: {response.status}")

        # Signal playground to finish
        await pg.finish()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
