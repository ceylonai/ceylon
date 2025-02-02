import asyncio
from typing import AsyncIterator

from ceylon.llm.models import StreamedResponse, ModelSettings, ModelMessage
from ceylon.llm.models.ollama import OllamaModel
from ceylon.llm.models.support.messages import MessageRole, TextPart


async def print_stream(stream: AsyncIterator[StreamedResponse]) -> None:
    """Helper to print streaming responses"""
    async for chunk in stream:
        if hasattr(chunk.delta, 'text'):
            print(chunk.delta.text, end='', flush=True)
    print()  # New line at end


async def main():
    # Initialize the model
    model = OllamaModel(
        model_name="llama3.2",  # or another model you have pulled
        base_url="http://localhost:11434"
    )

    try:
        # First, let's check available models
        models = await OllamaModel.list_models()
        print("Available models:")
        for model_info in models:
            print(f"- {model_info['name']}")
        print()

        # Create a context with some settings
        context = model.create_context(
            settings=ModelSettings(
                temperature=0.7,
                max_tokens=2000
            )
        )

        # Example 1: Basic question answering
        print("Example 1: Basic question answering")
        print("-" * 50)

        messages = [
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text="What are the main benefits of Python programming language?")]
            )
        ]

        response, usage = await model.request(messages, context)

        print("Response:")
        for part in response.parts:
            if hasattr(part, 'text'):
                print(part.text)

        print("\nUsage statistics:")
        print(f"Request tokens: {usage.request_tokens}")
        print(f"Response tokens: {usage.response_tokens}")
        print(f"Total tokens: {usage.total_tokens}")
        print()

        # Example 2: Conversation with system prompt
        print("Example 2: Conversation with system prompt")
        print("-" * 50)

        messages = [
            ModelMessage(
                role=MessageRole.SYSTEM,
                parts=[TextPart(text="You are a helpful coding assistant that provides concise answers.")]
            ),
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text="Show me a simple Python function to calculate factorial.")]
            )
        ]

        response, usage = await model.request(messages, context)

        print("Response:")
        for part in response.parts:
            if hasattr(part, 'text'):
                print(part.text)
        print()

        # Example 3: Streaming response
        print("Example 3: Streaming response")
        print("-" * 50)

        messages = [
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text="Write a short story about a programmer who discovers AI.")]
            )
        ]

        print("Streaming response:")
        stream = model.request_stream(messages, context)
        await print_stream(stream)
        print()

        # Example 4: Multi-turn conversation
        print("Example 4: Multi-turn conversation")
        print("-" * 50)

        conversation = [
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text="What is a binary search tree?")]
            ),
            ModelMessage(
                role=MessageRole.ASSISTANT,
                parts=[TextPart(
                    text="A binary search tree is a data structure where each node has at most two children, with all left descendents being smaller and right descendents being larger than the node's value.")]
            ),
            ModelMessage(
                role=MessageRole.USER,
                parts=[TextPart(text="Can you show me how to implement one in Python?")]
            )
        ]

        response, usage = await model.request(conversation, context)

        print("Response:")
        for part in response.parts:
            if hasattr(part, 'text'):
                print(part.text)
        print()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        # Clean up
        await model.close()


if __name__ == "__main__":
    asyncio.run(main())
