import asyncio

from ceylon import base


async def main():
    llm_writer = base.LLMAgent(name="writer", is_leader=True)


if __name__ == '__main__':
    asyncio.run(main())
