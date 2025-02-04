import asyncio
from typing import Dict, Any

from loguru import logger

from ceylon.task import TaskPlayGround
from ceylon.task.agent import TaskAgent
from ceylon.task.data import TaskRequest, TaskStatus


class SimpleLLMAgent(TaskAgent):
    """Simple LLM agent that simulates text generation and processing"""

    def _setup_supported_tasks(self) -> None:
        self.supported_tasks = {
            "generate": self._generate_text,
            "summarize": self._summarize_text,
            "answer": self._answer_question
        }

    async def process_task(self, request: TaskRequest) -> Any:
        handler = self.supported_tasks[request.task_type]
        return await handler(request.data)

    async def _generate_text(self, prompt: str) -> Dict[str, Any]:
        """Simulate text generation"""
        await asyncio.sleep(2)  # Simulate API call
        return {
            "text": f"Generated response for: {prompt}",
            "tokens": len(prompt) * 2,
            "model": "simple-llm"
        }

    async def _summarize_text(self, text: str) -> Dict[str, Any]:
        """Simulate text summarization"""
        await asyncio.sleep(1.5)  # Simulate processing
        return {
            "summary": f"Summary of {len(text)} chars: {text[:50]}...",
            "original_length": len(text),
            "summary_ratio": 0.3
        }

    async def _answer_question(self, question: str) -> Dict[str, Any]:
        """Simulate question answering"""
        await asyncio.sleep(1)  # Simulate thinking
        return {
            "answer": f"The answer to '{question}' is: This is a simulated response",
            "confidence": 0.85,
            "sources": ["simulated knowledge base"]
        }


async def run_llm_example():
    # Create playground and LLM agent
    playground = TaskPlayGround()
    llm_agent = SimpleLLMAgent("llm_assistant", "text_processor")

    try:
        async with playground.play(workers=[llm_agent]) as active_playground:
            # Test cases
            test_cases = [
                ("generate", "Write a short story about Python programming"),
                ("summarize", "This is a long text that needs to be summarized. " * 5),
                ("answer", "What is the meaning of life?"),
                ("unknown", "This should fail"),  # Unknown task type
            ]

            for task_type, data in test_cases:
                logger.info(f"\nSubmitting {task_type} task:")
                logger.info(f"Input: {data[:100]}...")

                # Submit task with metadata
                response = await active_playground.submit_task(
                    task_type=task_type,
                    instructions=data,
                    role="text_processor",
                    metadata={
                        "priority": "high",
                        "source": "example_script"
                    }
                )

                # Handle response
                if response:
                    if response.status == TaskStatus.COMPLETED:
                        logger.info(f"Task completed successfully!")
                        logger.info(f"Result: {response.result}")
                        if response.runtime_stats:
                            logger.info(f"Stats: {response.runtime_stats}")
                    else:
                        logger.warning(f"Task failed: {response.error_message}")

                # Small delay between tasks
                await asyncio.sleep(1)

            await active_playground.finish()

    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
    finally:
        logger.info("Example completed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(run_llm_example())