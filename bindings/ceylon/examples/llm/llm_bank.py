#  Copyright 2024-Present, Syigen Ltd. and Syigen Private Limited. All rights reserved.
#  Licensed under the Apache License, Version 2.0 (See LICENSE.md or http://www.apache.org/licenses/LICENSE-2.0).
#
import asyncio
from typing import Optional

from ceylon.llm.agent import LLMConfig, LLMAgent
from ceylon.llm.models.ollama import OllamaModel
from ceylon.task.data import Task, TaskResult
from ceylon.task.playground import TaskProcessingPlayground


class DatabaseConn:
    """This is a fake database for example purposes.
    In reality, you'd be connecting to an external database
    (e.g. PostgreSQL) to get information about customers.
    """

    @classmethod
    async def customer_name(cls, *, id: int) -> Optional[str]:
        if id == 123:
            return 'John'
        return None

    @classmethod
    async def customer_balance(cls, *, id: int, include_pending: bool) -> float:
        if id == 123:
            return 123.45
        else:
            raise ValueError('Customer not found')


async def main():
    # Create agent with configuration
    agent = LLMAgent(
        name="bank_support",
        llm_model=OllamaModel(
            model_name="llama3.2",
        ),
        config=LLMConfig(
            system_prompt=(
                "You are a support agent in our bank. Give the customer support "
                "and judge the risk level of their query on a scale of 0-10. "
                "Always use the provided tools to look up customer information. "
                "Format your response as:\n"
                "Advice: <your advice>\n"
                "Risk Level: <0-10>\n"
                "Block Card: <yes/no>"
            )
        ),
        role="bank_support"
    )

    # Define customer name lookup tool
    @agent.tool(
        name="get_customer_name",
        description="Looks up the customer's name using their ID"
    )
    async def get_customer_name(customer_id: int) -> str:
        name = await DatabaseConn.customer_name(id=customer_id)
        if name:
            return name
        return "Customer not found"

    # Define balance lookup tool
    @agent.tool(
        name="get_balance",
        description="Returns the customer's current account balance"
    )
    async def get_balance(customer_id: int, include_pending: bool = True) -> str:
        try:
            balance = await DatabaseConn.customer_balance(
                id=customer_id,
                include_pending=include_pending
            )
            return f"${balance:.2f}"
        except ValueError as e:
            return str(e)

    # Create playground
    playground = TaskProcessingPlayground()

    # Start the system
    async with playground.play(workers=[agent]) as active_playground:
        # Test some customer support scenarios
        test_queries = [
            {
                "customer_id": 123,
                "query": "What is my balance?"
            },
            {
                "customer_id": 123,
                "query": "I just lost my card!"
            }
        ]

        for test in test_queries:
            response: TaskResult = await active_playground.add_and_execute_task(
                Task(
                    name="Support",
                    processor="bank_support",
                    input_data={
                        "customer_id": test["customer_id"],
                        "request": test["query"]
                    }
                )
            )
            print(f"\nQuery: {test['query']}")
            print(f"Response: {response.output}")

        await active_playground.finish()


if __name__ == "__main__":
    asyncio.run(main())
