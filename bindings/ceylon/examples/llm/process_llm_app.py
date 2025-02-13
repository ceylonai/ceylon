import asyncio

from ceylon.llm.agent import LLMConfig, LLMAgent
from ceylon.llm.models.ollama import OllamaModel
from ceylon.processor.agent import ProcessRequest, ProcessResponse
from ceylon.processor.playground import ProcessPlayGround


async def main():
    # Create playground and worker
    playground = ProcessPlayGround()
    llm_model = OllamaModel(
        model_name="llama3.2",
        base_url="http://localhost:11434"
    )

    # Configure LLM agent
    llm_config = LLMConfig(
        system_prompt=(
            "You are an expert content writer specializing in technology topics. "
            "Provide clear, informative, and engaging responses."
        ),
        temperature=0.7,
        max_tokens=1000,
        retry_attempts=1
    )

    # Create LLM agent
    llm_agent = LLMAgent(
        name="writer_1",
        llm_model=llm_model,
        config=llm_config,
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


if __name__ == "__main__":
    asyncio.run(main())

