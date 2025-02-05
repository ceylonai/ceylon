import asyncio

from ceylon.llm.agent import LLMConfig, LLMAgent
from ceylon.llm.models.ollama import OllamaModel
from ceylon.llm.models.support.tools import ToolDefinition
from ceylon.task.data import Task, TaskResult
from ceylon.task.playground import TaskProcessingPlayground


async def calculate(expression: str) -> float:
    print(f"Calculating: {expression}")
    """Simple calculator function that evaluates mathematical expressions."""
    try:
        # Evaluate the expression safely
        allowed_chars = set("0123456789+-*/(). ")
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Invalid characters in expression")
        return eval(expression)
    except Exception as e:
        return f"Error: {str(e)}"


async def main():
    # Define calculator tool
    tools = [
        ToolDefinition(
            name="calculator",
            description="Performs basic mathematical calculations",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2')"
                    }
                },
                "required": ["expression"]
            },
            function=calculate
        )
    ]

    # Create playground
    playground = TaskProcessingPlayground()

    # Create LLM agent with calculator tool
    llm_agent = LLMAgent(
        name="math_assistant",
        llm_model=OllamaModel(
            model_name="deepseek-r1:8b",
            base_url="http://localhost:11434"
        ),
        config=LLMConfig(
            system_prompt=(
                "You are a math assistant. Use the calculator tool to perform calculations. "
                "When asked to perform calculations, always use the calculator tool for accuracy."
            ),
            temperature=0.7,
            max_tokens=1000,
            tools=tools
        ),
        role="math_assistant"
    )

    # Start the system
    async with playground.play(workers=[llm_agent]) as active_playground:
        # Test some calculations
        test_questions = [
            "What is 123 * 456?",
            "Calculate 15.5 + 27.3",
            "What is (100 - 20) / 2?"
        ]

        for question in test_questions:
            response:TaskResult = await active_playground.add_and_execute_task(
                Task(
                    name="Calculate",
                    processor="math_assistant",
                    input_data={"request": question}
                )
            )
            print(f"\nQuestion: {question}")
            print(f"Response: {response.output}")


if __name__ == "__main__":
    asyncio.run(main())
