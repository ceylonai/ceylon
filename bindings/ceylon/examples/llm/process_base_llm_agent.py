import asyncio

from ceylon.llm.agent import LLMConfig, LLMAgent
from ceylon.llm.models.ollama import OllamaModel
from ceylon.processor.agent import ProcessRequest, ProcessResponse
from ceylon.processor.playground import ProcessPlayGround


async def main():
    # Create playground and worker
    playground = ProcessPlayGround()
    # Create LLM agent
    llm_agent = LLMAgent(
        name="writer_1",
        llm_model=OllamaModel(
            model_name="llama3.2",
        ),
        config=LLMConfig(
            system_prompt=(
                "You are an expert content writer specializing in technology topics. "
                "Provide clear, informative, and engaging responses."
            )
        ),
        role="writer"
    )

    # Start the system
    async with playground.play(workers=[llm_agent]) as active_playground:
        active_playground: ProcessPlayGround = active_playground
        # Send some test requests
        response: ProcessResponse = await active_playground.process_request(ProcessRequest(
            task_type="writer",
            data="Write a blog post about AI in 2023."
        ))
        print(f"Response received: {response.result}")
        await active_playground.finish()


if __name__ == "__main__":
    asyncio.run(main())
