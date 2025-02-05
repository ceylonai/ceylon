# Step-by-Step Tutorial: Ceylon ProcessPlayGround with ProcessWorker

This tutorial will guide you through creating a simple text processing application using Ceylon's ProcessPlayGround and
ProcessWorker. We'll build a system that converts text to uppercase.

## Prerequisites

1. Python 3.7 or higher installed
2. Ceylon package installed
3. Basic understanding of Python async/await

## Step 1: Project Setup

First, create a new directory for your project and create a new Python file:

```bash
mkdir ceylon_tutorial
cd ceylon_tutorial
touch uppercase_processor.py
```

## Step 2: Import Required Dependencies

Open `uppercase_processor.py` and add the necessary imports:

```python
import asyncio
from typing import Any
from ceylon.processor.agent import ProcessWorker
from ceylon.processor.playground import ProcessPlayGround
from ceylon.processor.data import ProcessRequest, ProcessResponse, ProcessState
```

## Step 3: Create the ProcessWorker

Create a custom ProcessWorker class that will handle the text conversion:

```python
class UpperCaseProcessor(ProcessWorker):
    """A simple processor that converts input text to uppercase"""

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
```

Key points about the ProcessWorker:

- Inherits from `ProcessWorker`
- Takes a name parameter in `__init__`
- Implements `_processor` method that receives a request and returns a tuple of (result, metadata)

## Step 4: Create the Main Function

Add the main function that sets up and runs the playground:

```python
async def main():
    # Create playground and worker
    playground = ProcessPlayGround(name="text_playground", port=8888)
    worker = UpperCaseProcessor()

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
```

## Step 5: Add Entry Point

Add the entry point at the bottom of the file:

```python
if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
```

## Understanding the Components

### ProcessPlayGround

- Acts as a central hub for processing requests
- Manages workers and their connections
- Handles message routing between components

### ProcessWorker

- Performs the actual processing work
- Defines processing logic in `_processor` method
- Can handle specific types of requests based on role

### ProcessRequest

- Contains the data to be processed
- Includes task type that matches worker role
- Can include additional metadata

### ProcessResponse

- Contains the processed result
- Includes status (SUCCESS/ERROR)
- Can include error messages and metadata

## Running the Example

1. Save all the code in `uppercase_processor.py`
2. Open a terminal in your project directory
3. Run the script:

```bash
python uppercase_processor.py
```

Expected output:

```
Original text: Hello, World!
Processed text: HELLO, WORLD!
Process status: ProcessState.SUCCESS
```

## Common Issues and Solutions

1. **Port Already in Use**
    - Error: "Address already in use"
    - Solution: Change the port number in playground initialization

2. **Worker Not Connected**
    - Error: "No worker available for task type"
    - Solution: Ensure worker role matches task_type in request

3. **Async Context Issues**
    - Error: "Event loop is closed"
    - Solution: Ensure all async code is within the main function

## Next Steps

1. Add error handling:

```python
try:
    response = await pg.process_request(request)
except Exception as e:
    print(f"Error processing request: {e}")
```

2. Process multiple requests:

```python
requests = [
    ProcessRequest(task_type="uppercase_processor", data="first request"),
    ProcessRequest(task_type="uppercase_processor", data="second request")
]
for request in requests:
    response = await pg.process_request(request)
    print(response.result)
```

3. Add metadata to track processing time:

```python
import time


async def _processor(self, request: ProcessRequest, time: int) -> tuple[Any, dict]:
    start_time = time.time()
    result = request.data.upper()
    processing_time = time.time() - start_time
    return result, {"processing_time": processing_time}
```

## Tips for Production Use

1. Always implement proper error handling
2. Use logging instead of print statements
3. Consider implementing request timeouts
4. Add monitoring and metrics collection
5. Implement proper cleanup in case of failures

## Conclusion

This tutorial covered the basics of creating a Ceylon ProcessPlayGround with a custom ProcessWorker. The example
demonstrates:

- Setting up a processing system
- Creating custom workers
- Handling requests and responses
- Basic error handling

As you build more complex systems, you can extend this pattern to handle different types of data, implement more
sophisticated processing logic, and add additional features like load balancing and error recovery.