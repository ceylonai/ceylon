import asyncio
from ceylon.llm.models.ollama import OllamaModel
from ceylon.task.data import Task, TaskResult
from ceylon.task.playground import TaskProcessingPlayground
from ceylon.llm.agent import LLMConfig, LLMAgent


async def main():
    # Create agent with configuration
    agent = LLMAgent(
        name="math_assistant",
        llm_model=OllamaModel(
            model_name="deepseek-r1:8b",
        ),
        config=LLMConfig(
            system_prompt=(
                "You are a math assistant. Use the calculator tool to perform calculations. "
                "When asked to perform calculations, always use the calculator tool for accuracy."
            )
        ),
        role="math_assistant"
    )

    # Define calculator tool using decorator
    @agent.tool(
        name="calculator",
        description="Performs basic mathematical calculations"
    )
    async def calculate(expression: str) -> float:
        print(f"Calculating: {expression}")
        try:
            # Evaluate the expression safely
            allowed_chars = set("0123456789+-*/(). ")
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            return eval(expression)
        except Exception as e:
            return f"Error: {str(e)}"

    # Create playground
    playground = TaskProcessingPlayground()

    # Start the system
    async with playground.play(workers=[agent]) as active_playground:
        # Test some calculations
        test_questions = [
            "What is 123 * 456?",
            "Calculate 15.5 + 27.3",
            "What is (100 - 20) / 2?"
        ]

        for question in test_questions:
            response: TaskResult = await active_playground.add_and_execute_task(
                Task(
                    name="Calculate",
                    processor="math_assistant",
                    input_data={"request": question}
                )
            )
            print(f"\nQuestion: {question}")
            print(f"Response: {response.output}")

        await active_playground.finish()


if __name__ == "__main__":
    asyncio.run(main())
